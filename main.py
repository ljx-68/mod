from sklearn.feature_extraction.text import TfidfVectorizer
from Text_Data_Labeling import EmotionTypeLabeling
from Types import ClauseNode, EmotionScore
from grammar_rules import ClauseSplitter
from clause_cache import ClauseCache
from Roughlyfilter_data import BASE_COORDS, NEGATE_MAP
class Intent:
    def __init__(self, root = "."):
        self.splitter = ClauseSplitter(root = root)
        self.labeler = EmotionTypeLabeling(root = root)
        self.clause_cache = ClauseCache()

    def process(self, text: str) -> ClauseNode:
        if not text or not text.strip():
            return ClauseNode(text = "", start = 0, end = 0, level = 0, vad = [0.5, 0.5, 0.5])

        try:
            tree = self.splitter.split(text)
        except Exception as e:
            print(f"断句失败: {text[:30]!r}: {e}")
            return ClauseNode(text = text, start = 0, end = len(text), level = 0, vad = [0.5, 0.5, 0.5])

        self._fill_with_cache(tree)
        return tree

    def process_emotion(self, text: str) -> ClauseNode | None:
        tree = self.process(text)
        return tree.filter_tree(only_emotion = True)

    def _fill_with_cache(self, node: ClauseNode) -> None:
        if node.is_leaf():
            cached = self.clause_cache.get(node.text)
            if cached:
                for e in cached["emotions"]:
                    node.add_emotion(EmotionScore.from_dict(e))
                node.vad = cached["vad"]
                return

            scores = self.labeler.Text_matching(node.text)
            for emo, s in scores.items():
                node.add_emotion(s)
            node.vad = self._to_vad(node.emotions)
            self.clause_cache.put(
                node.text,
                [e.to_dict() for e in node.emotions],
                node.vad,
            )
            return

        for child in node.children:
            self._fill_with_cache(child)

        child_vad = [c.vad for c in node.children if c.vad]
        if child_vad:
            node.vad = [
                round(sum(v[i] for v in child_vad) / len(child_vad), 2)
                for i in range(3)
            ]
        else:
            node.vad = [0.5, 0.5, 0.5]
    def _to_vad(self, emotions: list[EmotionScore])-> list[float]:
        if not emotions:
            return [0.5, 0.5, 0.5]
        active: dict[str, float] = {}
        for s in emotions:
            if s.final > 0:
                active[s.emotion] = max(active.get(s.emotion, 0), abs(s.final))
            elif s.final < 0:
                target, coef = NEGATE_MAP.get(s.emotion, (None, 0))
                if target:
                    active[target] = max(active.get(target, 0), abs(s.final) * coef)
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
    def process_batch(self, texts: list[str]) -> list[ClauseNode]:
        return [self.process(t) for t in texts]
    def cache_stats(self) -> dict:
        return self.clause_cache.stats()

