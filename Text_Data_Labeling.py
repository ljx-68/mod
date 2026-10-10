import re
from pathlib import Path

from Types import ContextPattern, EmotionScore, Token
from Document_Management import (
    load_emotion_data,
    Secondary_judgment_data_loading,
    load_negation_lexicon,
    load_modifier_lexicon,
    load_relation_rules,
)


class EmotionTypeLabeling:
    PRONOUNS = ("我", "你", "他", "她", "它", "我们", "你们", "他们", "咱们")

    def __init__(self, root: Path | str = "."):
        self.root = Path(root)
        self.emotions = sorted(
            p.name for p in (self.root / "feelings").iterdir() if p.is_dir()
        )

        self.context_patterns, self.word_index = self._build_word_index()
        self.negation = load_negation_lexicon(root=self.root)
        self.modifier = load_modifier_lexicon(root=self.root)
        self.relation_rules = load_relation_rules(root=self.root)

        self.lexicon = self._build_lexicon()
        self.words_sorted = sorted(self.lexicon, key=len, reverse=True)

    def _build_word_index(self) -> tuple[list[ContextPattern], dict[str, list[str]]]:
        patterns: list[ContextPattern] = []
        word_index: dict[str, list[str]] = {}

        for emo in self.emotions:
            for entry in load_emotion_data(emo, root=self.root):
                for word in entry["data"]:
                    word_index.setdefault(word, []).append(entry["Type"])

            patterns.extend(
                Secondary_judgment_data_loading(emo, root=self.root)
            )

        return patterns, word_index

    def _build_lexicon(self) -> dict[str, list[tuple[str, object]]]:
        lex: dict[str, list[tuple[str, object]]] = {}

        def add(word: str, kind: str, value):
            lex.setdefault(word, []).append((kind, value))

        for word, emotions in self.word_index.items():
            add(word, "emotion", emotions)

        for word in self.negation.words:
            add(word, "negation", None)

        for word, coef in self.modifier.modifiers.items():
            add(word, "modifier", coef)

        for rule in self.relation_rules:
            for word in rule.standalone:
                add(word, "relation", rule.name)
            for pair in rule.pairs:
                for word in pair.front:
                    add(word, "relation", rule.name)
                for word in pair.back:
                    add(word, "relation", rule.name)

        return lex

    def Text_matching(self, text: str) -> dict[str, EmotionScore]:
        tokens = self._tokenize(text)
        relation = self._extract_relation(tokens)

        scores: dict[str, EmotionScore] = {}
        for token in tokens:
            if token.kind == "emotion":
                self._fill_score(scores, tokens, token, relation)

        return scores
    def _tokenize(self, text: str) -> list[Token]:
        matched: set[int] = set()
        tokens: list[Token] = []

        i = 0
        while i < len(text):
            word = self._match_at(text, i, matched)
            if word:
                for kind, value in self.lexicon[word]:
                    tokens.append(Token(word, i, i + len(word), kind, value))
                matched |= set(range(i, i + len(word)))
                i += len(word)
            else:
                i += 1

        return tokens

    def _match_at(self, text: str, position: int, matched: set[int]) -> str | None:
        for word in self.words_sorted:
            if text.startswith(word, position):
                span = set(range(position, position + len(word)))
                if not (span & matched):
                    return word
        return None

    def _extract_relation(self, tokens: list[Token]) -> str:
        rel_tokens = [t for t in tokens if t.kind == "relation"]
        if not rel_tokens:
            return ""

        hit_names = {t.value for t in rel_tokens}

        for rule in self.relation_rules:
            if rule.name not in hit_names:
                continue

            for t in rel_tokens:
                if t.value == rule.name and t.word in rule.standalone:
                    return rule.name

            for pair in rule.pairs:
                front_hit = any(
                    t.value == rule.name and t.word in pair.front
                    for t in rel_tokens
                )
                back_hit = any(
                    t.value == rule.name and t.word in pair.back
                    for t in rel_tokens
                )
                if front_hit and back_hit:
                    return rule.name

        return ""
    def _count_negation(self, tokens: list[Token], position: int) -> int:
        return sum(
            1 for t in tokens
            if t.kind == "negation" and t.start < position
        )

    def _compute_intensity(self, tokens: list[Token], position: int) -> float:
        intensity = 1.0
        for t in tokens:
            if t.kind == "modifier" and t.start < position:
                intensity *= t.value
        return round(intensity, 2)

    def _fill_score(
        self,
        scores: dict[str, EmotionScore],
        tokens: list[Token],
        token: Token,
        relation: str,
    ) -> None:
        neg_count = self._count_negation(tokens, token.start)
        intensity = self._compute_intensity(tokens, token.start)

        for emo in token.value:
            if emo not in scores:
                scores[emo] = EmotionScore(emotion=emo)
            s = scores[emo]
            s.raw += 1.0
            s.neg_count += neg_count
            s.intensity *= intensity
            s.positions.append(token.start)
            s.sources.append(f"词表:{token.word}")
            if relation:
                s.relation = relation