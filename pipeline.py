
from grammar_rules import ClauseSplitter
from Text_Data_Labeling import EmotionTypeLabeling
from Types import ClauseNode, EmotionScore


class Pipeline:
    def __init__(self, root="."):
        self.splitter = ClauseSplitter(root=root)
        self.labeler = EmotionTypeLabeling(root=root)

    def process(self, text: str) -> dict:
        if not text or not text.strip():
            return {
                "sentence": "",
                "tree": None,
                "clauses": [],
                "vad": [0.5, 0.5, 0.5],
            }

        # 1. 断句
        tree = self.splitter.split(text)

        # 2. 情绪匹配（叶子节点）
        self._match_emotions(tree)

        # 3. 收集子句情绪 + VAD
        clauses_data = self._collect_clauses(tree)
        vad = self._to_vad(clauses_data)

        return {
            "sentence": text,
            "tree": tree.to_dict(),
            "clauses": clauses_data,
            "vad": vad,
        }

    # ── 情绪匹配 ──
    def _match_emotions(self, node: ClauseNode) -> None:
        if node.is_leaf():
            scores = self.labeler.Text_matching(node.text)
            for emo, s in scores.items():
                node.add_emotion(s)
            return
        for child in node.children:
            self._match_emotions(child)

    # ── 收集叶子节点 ──
    def _collect_clauses(self, node: ClauseNode) -> list[dict]:
        result = []
        for leaf in self._walk_leaves(node):
            result.append({
                "text": leaf.text,
                "confidence": leaf.confidence,
                "relation": leaf.relation,
                "emotions": {e.emotion: e.to_dict() for e in leaf.emotions},
            })
        return result

    def _walk_leaves(self, node: ClauseNode):
        if node.is_leaf():
            yield node
            return
        for child in node.children:
            yield from self._walk_leaves(child)

    # ── VAD 计算 ──
    def _to_vad(self, clauses_data: list[dict]) -> list[float]:
        if not clauses_data:
            return [0.5, 0.5, 0.5]

        vads = []
        for c in clauses_data:
            emos = c["emotions"]
            if not emos:
                vads.append([0.5, 0.5, 0.5])
                continue
            vads.append(self._emotions_to_vad(emos))

        vads = [v for v in vads if v != [0.5, 0.5, 0.5]]
        if not vads:
            return [0.5, 0.5, 0.5]

        return [
            round(sum(v[i] for v in vads) / len(vads), 2)
            for i in range(3)
        ]

    def _emotions_to_vad(self, emos: dict[str, dict]) -> list[float]:
        """单个子句的情绪 → VAD。"""
        from constants import BASE_COORDS, NEGATE_MAP

        active = {}
        for emo, data in emos.items():
            final = data.get("final", 0)
            if final > 0:
                active[emo] = max(active.get(emo, 0), abs(final))
            elif final < 0:
                target, coef = NEGATE_MAP.get(emo, (None, 0))
                if target:
                    active[target] = max(active.get(target, 0), abs(final) * coef)

        if not active:
            return [0.5, 0.5, 0.5]

        total = sum(active.values())
        weights = {e: v / total for e, v in active.items()}

        V = A = D = 0.0
        for e, w in weights.items():
            coords = BASE_COORDS.get(e)
            if coords is None:
                continue
            V += coords[0] * w
            A += coords[1] * w
            D += coords[2] * w

        intensity = min(1.0, total)
        return [
            round(max(0, min(1, 0.5 + (V - 0.5) * intensity)), 2),
            round(max(0, min(1, 0.5 + (A - 0.5) * intensity)), 2),
            round(max(0, min(1, 0.5 + (D - 0.5) * intensity)), 2),
        ]