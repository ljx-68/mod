
from Roughlyfilter_data import (
    BASE_CONF, OPEN_QUOTES, PROTECT_PAIRS, URL_STOP,
    PARTICLE_CONF_BASE, PARTICLE_CONF_STEP, PARTICLE_CONF_MAX,
)
from Types import ClauseNode, Edge_processing
from Document_Management import load_relation_rules, build_grammar_lexicon


class ClauseSplitter:
    def __init__(self, root="."):
        self.root = root
        self.grammar = build_grammar_lexicon(root=root)
        self.edge = Edge_processing()
        self._rel_fronts, self._rel_backs, self._rel_standalones = \
            self._cache_relational_words()
        self._rel_all = self._rel_fronts | self._rel_backs
        self.space_chars = frozenset(
            w for w, st in self.grammar.punct_subtype.items() if st == "space"
        )
    def _cache_relational_words(self):
        fronts, backs, standalones = set(), set(), set()
        for rule in load_relation_rules(self.root):
            for pair in rule.pairs:
                fronts.update(pair.front)
                backs.update(pair.back)
            standalones.update(rule.standalone)
        return fronts, backs, standalones

    def split_l1(self, test: str, min_len: int = 3) -> list[ClauseNode]:
        if not test or not test.strip():
            return []

        protected = self._protect(test)
        nodes: list[ClauseNode] = []
        buf, start = [], 0
        skip_until = -1

        for i, ch in enumerate(test):
            buf.append(ch)
            if i in protected:
                continue

            ptype = self.grammar.punct_type.get(ch)
            if ptype is None or ptype == "protect":
                continue
            if ch in self.space_chars:
                if not self._should_split_space(test, i):
                    continue

            candidate = "".join(buf).strip()
            if len(candidate) < min_len:
                continue

            adjust = self.grammar.punctuations.get(ch, 1.0)
            conf = round(min(1.0, BASE_CONF[ptype] * adjust), 3)

            nodes.append(ClauseNode(
                text=candidate,
                start=start, end=i + 1,
                level=1, split_reason="punct",
                punct=ch, punct_type=ptype,
                punct_subtype=self.grammar.punct_subtype.get(ch),
                adjust=adjust, confidence=conf,
            ))
            buf, start = [], i + 1
            if ch in self.space_chars:
                if not self._should_split_space(test, i):
                    continue

        if buf and "".join(buf).strip():
            nodes.append(ClauseNode(
                text = "".join(buf).strip(),
                start=start, end=len(test),
                level=1, split_reason="tail",
                confidence=BASE_CONF["tail"],
            ))
        return nodes

    def _should_split_space(self, text: str, i: int) -> bool:
        j = i
        while j < len(text) and text[j] in self.space_chars:
            j += 1
        if j - i >= 2:
            return True
        if 0 < i < len(text) - 1:
            prev_c = text[i - 1]
            next_c = text[i + 1]
            return ('\u4e00' <= prev_c <= '\u9fff'
                    and '\u4e00' <= next_c <= '\u9fff')
        return False
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
                        i = j + 1
                        matched = True
                        break
            if matched:
                continue

            if text[i:i + 7] == "http://":
                j = i + 7
                while j < len(text) and text[j] not in URL_STOP:
                    j += 1
                protected.update(range(i, j))
                i = j
                continue

            if text[i:i + 8] == "https://":
                j = i + 8
                while j < len(text) and text[j] not in URL_STOP:
                    j += 1
                protected.update(range(i, j))
                i = j
                continue

            if text[i] == "." and 0 < i < len(text) - 1:
                if text[i - 1].isdigit() and text[i + 1].isdigit():
                    protected.add(i)

            i += 1
        return protected

    def split_l2(self, clauses: list[ClauseNode], min_len: int = 4) -> list[ClauseNode]:
        result = []
        for c in clauses:
            if c.punct_type == "strong":
                result.append(c)
                continue
            if len(c.text) < min_len:
                result.append(c)
                continue

            boundaries = self._find_l2_boundaries(c.text)
            if not boundaries:
                result.append(c)
                continue

            result.extend(self._slice_l2(c, boundaries))
        return result

    def _find_l2_boundaries(self, text: str) -> list[tuple[int, str, float]]:
        if any(w in text for w in self._rel_all):
            return []

        boundaries = []
        n = len(text)

        for i in range(1, n):
            if not self._starts_with_subject(text, i):
                continue

            prev = text[:i]
            if not self._has_predicate(prev):
                continue
            if prev[-1] in self.grammar.forbidden:
                continue
            if any(prev.endswith(v) for v in self.grammar.transitive):
                continue

            boundaries.append((i, "subject_start", 0.75))

        for i, w in self._iter_particles(text):
            end = i + len(w)
            if end >= n:
                continue
            if text[end] in self.grammar.continuations:
                continue

            prev = text[:end]
            if not self._has_predicate(prev):
                continue

            curr = text[end:]
            if not (self._starts_with_subject(curr, 0)
                    or self._starts_with_adverb(curr)):
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
        return any(seg.startswith(w) for w in self.grammar.adverbs)

    def _has_predicate(self, seg: str) -> bool:
        return any(v in seg for v in self.grammar.predicates)

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


    def split_l3(self, clauses: list[ClauseNode]) -> list[ClauseNode]:
        for node in clauses:
            self._apply_particle(node)
        return clauses

    def _apply_particle(self, node: ClauseNode) -> None:
        text = node.text
        if not text:
            return
        stripped = text.rstrip(",，.。？?！!;:；、…—～")
        if not stripped:
            return

        for w in sorted(self.grammar.particles, key=len, reverse=True):
            if stripped.endswith(w):
                node.particle = w
                node.particle_subtype = self.grammar.particle_subtype.get(w, "")
                adjust = self.grammar.particles[w]

                particle_conf = round(
                    min(PARTICLE_CONF_MAX,
                        PARTICLE_CONF_BASE + PARTICLE_CONF_STEP * adjust),
                    3,
                )
                node.confidence = round(max(node.confidence, particle_conf), 3)
                break

        if node.particle_subtype == "question":
            node.is_question = True
        if node.particle_subtype == "exclamation":
            node.is_exclamation = True

        if node.punct_subtype == "question":
            node.is_question = True
        if node.punct_subtype == "exclamation":
            node.is_exclamation = True

    def split_l4(self, clauses: list[ClauseNode]) -> list[ClauseNode]:
        # ── 修 5：传 root ──
        rules = load_relation_rules(self.root)
        if not rules or not clauses:
            return clauses

        step1 = []
        for c in clauses:
            inside = self._find_inside_pair(c.text, rules)
            if inside:
                rule, b_pos = inside
                step1.append(self._make_inside_compound(c, rule, b_pos))
            else:
                c.relation = next(
                    (rule.name for rule in rules
                     if any(w in c.text for w in rule.standalone)),
                    c.relation,
                )
                step1.append(c)

        marks = [self._scan_relations(c.text, rules) for c in step1]

        result = []
        i = 0
        while i < len(step1):
            c = step1[i]
            if c.children:
                result.append(c)
                i += 1
                continue

            m = marks[i]
            if m["front"]:
                rule, _ = m["front"][0]
                found = -1
                for j in range(i + 1, min(i + 4, len(step1))):
                    if any(r2.name == rule.name for r2, _ in marks[j]["back"]):
                        found = j
                        break

                if found != -1:
                    for k in range(i + 1, found):
                        result.append(step1[k])
                    result.append(self._make_cross_compound(
                        step1[i], step1[found], rule))
                    i = found + 1
                    continue

            result.append(c)
            i += 1

        return result

    def _make_cross_compound(
        self,
        front_c: ClauseNode,
        back_c: ClauseNode,
        rule,
    ) -> ClauseNode:
        parent = ClauseNode(
            text=front_c.text + back_c.text,
            start=front_c.start,
            end=back_c.end,
            level=4,
            split_reason="relation",
            relation=rule.name,
            confidence=0.85,
            children=[front_c, back_c],
        )
        front_c.parent = parent
        back_c.parent = parent
        front_c.relation = f"{rule.name}_front"
        back_c.relation = f"{rule.name}_back"
        return parent

    def _scan_relations(self, text: str, rules) -> dict:
        m = {"front": [], "back": [], "standalone": []}
        for rule in rules:
            for pair in rule.pairs:
                hit = False
                for w in pair.front:
                    if w in text:
                        m["front"].append((rule, w))
                        hit = True
                        break
                if hit:
                    break
            for pair in rule.pairs:
                hit = False
                for w in pair.back:
                    if w in text:
                        m["back"].append((rule, w))
                        hit = True
                        break
                if hit:
                    break
            for w in rule.standalone:
                if w in text:
                    m["standalone"].append((rule, w))
                    break
        return m

    def _find_inside_pair(self, text, rules):
        for rule in rules:
            for pair in rule.pairs:
                f_pos = -1
                for w in pair.front:
                    idx = text.find(w)
                    if idx != -1 and (f_pos == -1 or idx < f_pos):
                        f_pos = idx
                if f_pos == -1:
                    continue

                b_pos = -1
                for w in pair.back:
                    idx = text.find(w, f_pos + 1)
                    if idx != -1 and (b_pos == -1 or idx < b_pos):
                        b_pos = idx
                if b_pos == -1:
                    continue

                return rule, b_pos
        return None

    def _make_inside_compound(self, c, rule, b_pos):
        front = ClauseNode(
            text=c.text[:b_pos].strip(),
            start=c.start, end=c.start + b_pos,
            level=4, split_reason="rel_front",
            relation=f"{rule.name}_front",
            confidence=0.85,
        )
        back = ClauseNode(
            text=c.text[b_pos:].strip(),
            start=c.start + b_pos, end=c.end,
            level=4, split_reason="rel_back",
            relation=f"{rule.name}_back",
            confidence=0.85,
        )
        parent = ClauseNode(
            text=c.text,
            start=c.start, end=c.end,
            level=4, split_reason="relation",
            relation=rule.name,
            confidence=0.85,
            children=[front, back],
        )
        front.parent = parent
        back.parent = parent
        return parent

    def merge_short(
            self,
            clauses: list[ClauseNode],
            min_len: int = 3,
    ) -> list[ClauseNode]:
        if not clauses:
            return []

        result = [clauses[0]]
        for c in clauses[1:]:
            if len(c.text) < min_len and result:
                prev = result[-1]
                prev.text += c.text
                prev.end = c.end
                if c.children:
                    prev.children.extend(c.children)
            else:
                result.append(c)
        return result

    def build_tree(self, clauses: list[ClauseNode]) -> ClauseNode:
        if not clauses:
            return ClauseNode(text="", start=0, end=0, level=0)

        roots = [c for c in clauses if c.parent is None]

        if len(roots) == 1:
            root = roots[0]
        else:
            root = ClauseNode(
                text = "".join(c.text for c in roots),
                start = roots[0].start,
                end = roots[-1].end,
                level = 0,
                split_reason = "root",
                confidence = 1.0,
                children = roots,
            )
            for c in roots:
                c.parent = root

        self._fill_clause_list(root)
        return root
    def split(self, text: str) -> ClauseNode:
        l1 = self.split_l1(text)
        l2 = self.split_l2(l1)
        l3 = self.split_l3(l2)
        l4 = self.split_l4(l3)
        merged = self.merge_short(l4)
        tree = self.build_tree(merged)

        return tree

    def _fill_clause_list(self, node: ClauseNode) -> list[ClauseNode]:
        if node.is_leaf():
            node.ClauseList = [node]
            return [node]

        result = []
        for child in node.children:
            result.extend(self._fill_clause_list(child))

        node.ClauseList = result
        return result
if __name__ == "__main__":
    splitter = ClauseSplitter()
    tree = splitter.split("今天很好！明天更好！")
    print(tree)
    for c in tree.ClauseList:
        print(c)