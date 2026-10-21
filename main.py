from Text_Data_Labeling import EmotionTypeLabeling

from Types import ClauseNode, EmotionScore

from grammar_rules import ClauseSplitter

from clause_cache import ClauseCache

import copy
import logging

from General_tpye import format_analyze

from Roughlyfilter_data import BASE_COORDS, NEGATE_MAP
class Intent:
    def __init__(self, root = ".", use_cache: bool = True):
        self.splitter = ClauseSplitter(root = root)
        self.labeler = EmotionTypeLabeling(root = root)
        self.clause_cache = ClauseCache() if use_cache else None
        self.logger = logging.getLogger(__name__)
    def _fill_with_cache(self, node: ClauseNode) -> None:
        if node.is_leaf():
            if self.clause_cache:
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
            if self.clause_cache:
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
    def cache_stats(self) -> dict:
        return self.clause_cache.stats() if self.clause_cache else {}

    # ── 用户层（返回 dict）──
    def analyze(self, text: str) -> dict:
        tree = self.process(text)
        return format_analyze(text, tree)

    def analyze_emotion(self, text: str) -> dict | None:
        tree = self.process(text)
        filtered = self._filter_tree(tree)
        if filtered is None:
            return None
        return {
            "text": text,
            "vad": filtered.vad,
            "tree": filtered.to_dict(),
        }
    # ── 便捷方法 ──
    def vad_only(self, text: str) -> list[float]:
        return self.process(text).vad
    def emotions_only(self, text: str) -> dict[str, float]:
        tree = self.process(text)
        result: dict[str, float] = {}
        for leaf in tree.iter_leaves():
            for e in leaf.emotions:
                result[e.emotion] = max(result.get(e.emotion, 0), abs(e.final))
        return result
    def clauses_only(self, text: str) -> list[dict]:
        tree = self.process(text)
        return [
            {
                "text": i.text,
                "vad": i.vad,
                "emotion": [e.emotion for e in i.emotions],
            }for i in tree.iter_leaves()
        ]
    # ── 进阶层（返回 ClauseNode）──
    def process(self, text: str) -> ClauseNode:
        if not text or not text.strip():
            return ClauseNode(text="", start=0, end=0, level=0, vad=[0.5, 0.5, 0.5])

        try:
            tree = self.splitter.split(text)
        except Exception as e:
            self.logger.warning(f"断句失败: {text[:30]!r}: {e}")
            return ClauseNode(text=text, start=0, end=len(text), level=0, vad=[0.5, 0.5, 0.5])

        self._fill_with_cache(tree)
        return tree
    def process_batch(self, texts: list[str]) -> list[ClauseNode]:
        return [self.process(t) for t in texts]

    def _filter_tree(self, node: ClauseNode) -> ClauseNode | None:
        children = []
        for c in node.children:
            f = self._filter_tree(c)
            if f is not None:
                children.append(f)

        if not children and not node.emotions:
            return None

        new = copy.copy(node)
        new.children = children
        new.parent = None
        for c in children:
            c.parent = new
        return new
