# grammar_rules.py
from Roughlyfilter_data import (
    BASE_CONF, OPEN_QUOTES, PROTECT_PAIRS, URL_STOP,
    PARTICLE_CONF_BASE, PARTICLE_CONF_STEP, PARTICLE_CONF_MAX,
)
from Types import ClauseNode, Edge_processing
from Document_Management import load_relation_rules, build_grammar_lexicon


class EmotionTypeLabeling:
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

TEXTS = [
    "经常去的，不过我自己的卡很久不用，被冻了，只能用爸爸的。吉利莲的巧克力以前选择多些，最近一次去只有一种选择了。食品零食的选择还不够。买不全。酸奶的日期都比较新鲜，逢年过节，时令食品的选择比较丰富。冷冻产品丰富，看看都不错。建议自己带好购物袋。",
    "喜欢在这里购物的感觉~~不在市中心,又是凭会员卡购物,因此不会有像家乐福\沃尔马那种人多很挤的场面,在这购物很安心,环境,商品的质量,价格都很有保证~~我觉得长沙最便宜的手机就是这的了````而且绝对保证是行货~~",
    "很适合有车一族来采购，因为没有袋子给的，只有纸箱子！感觉有点像仓库，可是东西好啊，买得多的话就更好了",
    "里面有一些进口食品还是不错的，但个人感觉商品种类比较少，而且管理不是很灵活，退货比较麻烦。价格方面是比较适中的。\n现在没有会员也可以进了，竞争越来越激烈了嘛。",
    "虽然是有一些不方便,但购物环境比较舒服,人少,房高,感觉很通透,不像别的商场人多,楼层低,人多的时候很闷,这里不会有这些问题,不过在这要买的多才爽,看着一车子东西,真的很爽.",
    "非常喜欢这个德国超市，他家各类东东都品牌齐全，不像沃尔玛、家乐福之类只有便宜货。经常能找到一些讨人喜欢的东东，比如梅子醋、XO酱、超有料的炖汤佐料，当然还有偶最爱的各式冷冻海鲜和Icecream，大爱。PS。停车也超方便，偶去四方坪常蹭他家免费停车位，非常谢谢啦，呵呵。",
    "感觉像仓储式购物，这才是超市：1 超级大；2 停车超级方便；3品种超级多；4 东西超级正牌超级便宜；5 运营超级规范",
    "从这家超市刚在湖南开的时候就开始消费，眼看着这里周边由荒凉变得热闹。人生真是好短。\n奇怪的是这里既然说是全世界有很多连锁店的超市，我在美国纽约州读书的同学居然说一直没有见过美国有这个超市，而且METRO是地铁的意思，晕。\n商品齐全，有不少杭州特产，楼外楼的东坡肉之类都有卖。对了，还有哈根达斯，在冰柜里，一样很贵很贵。\n买单的时候要刷会员卡的。\n他们家不对家庭和个人开放，会员是要凭营业执照去登记的。因此确实这样会把很多人拒之门外。\n有不少海鲜，价钱好贵。推荐水果、进口食品、现做面包等，质素都很不错，品种也齐全",
    "喜欢在麦德龙购物已经5，6年了。自从麦德龙开了没多久，几个败家妈妈就发现了它，平均一礼拜来一次，还是开车从湘潭来。（汗一个先~老说便宜，其实来回的油钱和过桥过路费都不知道多少了。。。）",
    "麦德隆多是大包装的东西。适合三代同堂的家庭采购。\n这里有卡才能进入，结帐时，同样要出示会员卡。\n其实离我家还蛮远的。但有时也会开车到这里来采购。\n不过，有次在这里买了酱牛肉，密封包装的。回到家里，打开包装，吓死了，牛肉都绿了。再仔细看了看保质日期，没错呀，是在保质期内的。只好又开车去麦德隆退货。损失了路费。就连麦德隆的售后服务人员，看了包装袋里的酱牛肉，都不禁皱起了眉头",
    "全部都是货架 有点像个仓库  东西都要成打的买··我哥哥喜欢去那里买东西··觉得还不错吧 有很多其他超市买不到的物品··总的来说很不错·",
]


def check_one(labeler, text, idx):
    print(f"\n{'='*70}")
    print(f"#{idx}  len={len(text)}  首40字={text[:40]!r}")

    l1 = labeler.split_l1(text)
    l2 = labeler.split_l2(l1)
    l3 = labeler.split_l3(l2)
    l4 = labeler.split_l4(l3)

    print(f"  L1={len(l1)}  L2={len(l2)}  L3={len(l3)}  L4={len(l4)}")

    for n in l4:
        if n.children:
            print(f"  L4 [{n.relation}] {n.text[:50]!r}")
            for c in n.children:
                print(f"      ├─ [{c.relation}] {c.text[:40]!r}")
        else:
            tag = n.relation or "-"
            long = " ⚠长" if len(n.text) > 50 else ""
            print(f"  L{n.level} [{tag:10s}] {n.text[:50]!r}{long}")


def main():
    labeler = EmotionTypeLabeling()
    for i, text in enumerate(TEXTS, 1):
        check_one(labeler, text, i)

    print(f"\n{'='*70}")
    print("体检结论（见下方人工判断）")


if __name__ == "__main__":
    main()