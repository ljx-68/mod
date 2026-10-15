from Document_Management import build_grammar_lexicon
from Types import *
from Roughlyfilter_data import *
class EmotionTypeLabeling:
    def __init__(self, root="."):
        self.grammar = build_grammar_lexicon(root=root)
        self.edge = Edge_processing()
    def split_l1(self, test: str) -> list[ClauseNode]:
        if not test or not test.strip():
            return []

        protected = self._protect(test)
        nodes: list[ClauseNode] = []
        buf, start = [], 0

        for i, ch in enumerate(test):
            buf.append(ch)
            if i in protected:
                continue

            ptype = self.grammar.punct_type.get(ch)
            if ptype is None or ptype == "protect":
                continue

            if ch in ("：", ":") and i + 1 < len(test):
                if test[i + 1] in OPEN_QUOTES:
                    continue

            adjust = self.grammar.punctuations.get(ch, 1.0)
            conf = round(min(1.0, BASE_CONF[ptype] * adjust), 3)

            nodes.append(ClauseNode(
                text = "".join(buf).strip(),
                start = start, end = i + 1,
                level = 1, split_reason="punct",
                punct = ch, punct_type=ptype,
                punct_subtype = self.grammar.punct_subtype.get(ch),
                adjust = adjust, confidence=conf,
            ))
            buf, start = [], i + 1

        if buf and "".join(buf).strip():
            nodes.append(ClauseNode(
                text = "".join(buf).strip(),
                start = start, end=len(test),
                level = 1, split_reason="tail",
                confidence = BASE_CONF["tail"],
            ))
        return nodes

    def _protect(self, text: str) -> set[int]:
        protected: set[int] = set()
        i = 0
        while i < len(text):
            matched = False
            for l, r in PROTECT_PAIRS:
                if text[i] == l:
                    j = text.find(r, i + 1)
                    if j != -1:
                        protected.update(range(i, j + 1))
                        i = j + 1  # ← 必须是 +1
                        matched = True
                        break
                if matched:
                    continue
            if matched:
                continue

            if text[i:i + 7] == "http://":
                j = i + 7
                while j < len(text) and text[j] not in " \n\t，。！？；":
                    j += 1
                protected.update(range(i, j))
                i = j
                continue
            if text[i:i + 8] == "https://":
                j = i + 8
                while j < len(text) and text[j] not in " \n\t，。！？；":
                    j += 1
                protected.update(range(i, j))
                i = j
                continue

            if text[i] == "." and 0 < i < len(text) - 1:
                if text[i - 1].isdigit() and text[i + 1].isdigit():
                    protected.add(i)

            if text[i] == ":" and 0 < i < len(text) - 1:
                if text[i - 1].isdigit() and text[i + 1].isdigit():
                    protected.add(i)

            i += 1

        return protected

    def split_l2(self, clauses: list[ClauseNode], threshold: int  = 4) -> list[ClauseNode]:
        result = []
        for c in clauses:
            if c.punct_type == "strong":
                result.append(c)
                continue
            if len(c.text) < threshold:
                result.append(c)
                continue

            boundaries = self._find_l2_boundaries(c.text)
            if not boundaries:
                result.append(c)
                continue

            result.extend(self._slice_l2(c, boundaries))
        return result

    def _find_l2_boundaries(self, text: str) -> list[tuple[int, str, float]]:
        boundaries = []
        n = len(text)

        for i in range(1, n):
            if not self._starts_with_subject(text, i):
                continue

            prev = text[:i]
            if not self._has_predicate(prev):
                continue
            if prev and prev[-1] in FORBIDDEN_TAIL:
                continue
            if any(prev.endswith(v) for v in TRANSITIVE_VERBS):
                continue

            boundaries.append((i, "subject_start", 0.75))

        for i, w in self._iter_particles(text):
            end = i + len(w)
            if end >= n:
                continue

            if text[end] in CONTINUATIONS:
                continue

            prev = text[:end]
            if not self._has_predicate(prev):
                continue

            curr = text[end:]
            if not (
                    self._starts_with_subject(curr, 0)
                    or self._starts_with_adverb(curr)
            ):
                continue

            adjust = self.grammar.particles.get(w, 1.0)
            conf = round(min(0.85, 0.6 + 0.15 * adjust), 3)
            boundaries.append((end, "end_particle", conf))

        boundaries.sort(key=lambda x: (x[0], 0 if x[1] == "end_particle" else 1))
        filtered, last = [], -10
        seen_pos = set()
        for pos, reason, conf in boundaries:
            if pos in seen_pos:
                continue
            if pos - last >= 2:
                filtered.append((pos, reason, conf))
                seen_pos.add(pos)
                last = pos
        return filtered

    def _starts_with_subject(self, text: str, i: int) -> bool:
        return any(text.startswith(s, i) for s in self.grammar.pronouns)

    def _starts_with_adverb(self, seg: str) -> bool:
        return any(seg.startswith(w) for w in ADVERB_STARTS)

    def _has_predicate(self, seg: str) -> bool:
        return any(v in seg for v in PREDICATE_VERBS)

    def _iter_particles(self, text: str):
        for i in range(len(text)):
            for w in self.grammar.particles:
                if text.startswith(w, i):
                    yield i, w
                    break

    def _slice_l2(
            self,
            base: ClauseNode,
            boundaries: list[tuple[int, str, float]],
    ) -> list[ClauseNode]:
        if not boundaries:
            return [base]

        t = base.text
        nodes, prev = [], 0
        for idx, reason, conf in boundaries:
            seg = t[prev:idx].strip()
            if seg:
                nodes.append(ClauseNode(
                    text=seg,
                    start=base.start + prev,
                    end=base.start + idx,
                    level=2,
                    split_reason=reason,
                    confidence=conf,
                ))
            prev = idx

        seg = t[prev:].strip()
        if seg:
            tail_reason, tail_conf = base.split_reason, base.confidence
            for w in self.grammar.particles:
                if seg.endswith(w):
                    adjust = self.grammar.particles[w]
                    tail_reason = "end_particle"
                    tail_conf = round(min(0.85, 0.6 + 0.15 * adjust), 3)
                    break

            nodes.append(ClauseNode(
                text=seg,
                start=base.start + prev,
                end=base.end,
                level=2,
                split_reason=tail_reason,
                confidence=tail_conf,
                punct=base.punct,
                punct_type=base.punct_type,
                punct_subtype=base.punct_subtype,
                adjust=base.adjust,
            ))
        return nodes
if __name__ == "__main__":
    labeler = EmotionTypeLabeling()

    cases = [
        # ── L1 标点 ──
        "今天很好！",
        "今天很好，明天更好。",
        "他说：“今天很好。”然后走了。",
        "价格是 3.14 元。",
        "网址是 http://a.com。真棒！",
        "今天很好",
        # ── L2 主谓宾 + 结束语 ──
        "我很累你呢",
        "我喜欢你你喜欢我吗",
        "我很开心你呢",
        "我今天很累",
        "我爱你",
        "我不觉得他开心",
        "你去吗我去",
    ]

    for text in cases:
        print(f"\n{'='*50}")
        print(f"IN : {text!r}")
        l1 = labeler.split_l1(text)
        print(f"  L1 输出 ({len(l1)} 条):")
        for n in l1:
            print(f"    L1 [{n.split_reason:6s}] {n.text!r} "
                  f"punct={n.punct!r} conf={n.confidence}")

        l2 = labeler.split_l2(l1)
        if l2 != l1:
            print(f"  L2 输出 ({len(l2)} 条):")
            for n in l2:
                print(f"    L{n.level} [{n.split_reason:13s}] {n.text!r} "
                      f"conf={n.confidence}")
        else:
            print(f"  L2 未切分")

