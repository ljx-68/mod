
from typing import Any
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class ClauseNode:
    text: str
    start: int
    end: int

    level: int = 1
    split_reason: str = ""


    punct: str | None = None
    punct_type: str | None = None
    adjust: float = 1.0

    subject: str = ""
    particle: str = ""
    is_sentence: bool = False

    relation: str | None = None

    parent: "ClauseNode | None" = field(default=None, repr=False, compare=False)
    children: list["ClauseNode"] = field(default_factory=list)

    confidence: float = 0.0

    emotion: "EmotionRecord | None" = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("parent", None)
        d.pop("emotion", None)
        return d

@dataclass(frozen = True)
class MatchContext:
    neg_count: int = 0
    is_negated: bool = False
    intensity: float = 1.0


@dataclass(frozen = True)
class ContextMatch:
    emotion: str = ""
    intensity: float = 0.0


@dataclass(frozen = True)
class ContextPattern:
    name: str
    emotion: str
    require_all_groups: tuple[tuple[str, ...], ...]
    weight: float

    def match(self, text: str) -> bool:
        return all(
            any(w in text for w in group)
            for group in self.require_all_groups
        )

@dataclass(frozen = True)
class ModifierLexicon:
    modifiers: dict[str, float]
    def find(self, text: str) -> tuple[str, float] | None:
        for word, coef in self.modifiers.items():
            if word in text:
                return word, coef
        return None

    def find_all(self, text: str) -> list[tuple[str, float]]:
        hits = []
        for word, coef in self.modifiers.items():
            start = 0
            while True:
                idx = text.find(word, start)
                if idx == -1:
                    break
                hits.append((word, coef))
                start = idx + len(word)
        return hits

@dataclass(frozen=True)
class NegationLexicon:
    words: frozenset[str]

    def count(self, text: str) -> int:
        words = sorted(self.words, key = len, reverse = True)
        count = 0
        i = 0
        while i < len(text):
            for w in words:
                if text.startswith(w, i):
                    count += 1
                    i += len(w)
                    break
            else:
                i += 1
        return count

@dataclass
class EmotionScore:              # ← 去掉 frozen=True
    emotion: str
    raw: float = 0.0
    intensity: float = 1.0
    neg_count: int = 0
    relation: str = ""
    positions: list[int] = field(default_factory = list)
    sources: list[str] = field(default_factory = list)
    subjects: list[str] = field(default_factory = list)

    @property
    def final(self) -> float:
        score = self.raw * self.intensity
        if self.neg_count % 2 == 1:
            score = -score
        return round(score, 2)

@dataclass(frozen=True)
class RelationPair:
    front: tuple[str, ...]
    back: tuple[str, ...]


@dataclass(frozen=True)
class RelationRule:
    name: str
    priority: int
    weight: tuple[float, float]
    standalone: tuple[str, ...] = ()
    pairs: tuple[RelationPair, ...] = ()

@dataclass(frozen = True)
class Token:
    word: str
    start: int
    end: int
    kind: str
    value: Any

@dataclass
class InferenceRecord:
    sentence : str
    vad : tuple[float, float, float]
    clauses : list["ClauseRecord"]
    version : str = "1.0"
    timestamp : str = ""
    def to_dict(self)-> dict:
        return {
            "sentence": self.sentence,
            "vad": list(self.vad),
            "clauses": [i.to_dict() for i in self.clauses],
            "version": self.version,
            "timestamp": self.timestamp,
        }
    @classmethod
    def from_dict(cls, data: dict)-> "InferenceRecord":
        return cls(
            sentence = data["sentence"],
            vad = tuple(data["vad"]),
            clauses = [ClauseRecord.from_dict(c) for c in data["clauses"]],
            version = data.get("version", "1.0"),
            timestamp = data.get("timestamp", "")
        )

@dataclass
class ClauseRecord:
    text: str
    vad: tuple[float, float, float]
    relation: str = ""
    emotions: dict[str, "EmotionRecord"] = field(default_factory = dict)

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "vad": list(self.vad),
            "relation": self.relation,
            "emotions": {e: s.to_dict() for e, s in self.emotions.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ClauseRecord":
        return cls(
            text = data["text"],
            vad = tuple(data["vad"]),
            relation = data.get("relation", ""),
            emotions = {
                e: EmotionRecord.from_dict(s)
                for e, s in data.get("emotions", {}).items()
            },
        )


@dataclass
class EmotionRecord:
    raw: float
    intensity: float
    neg_count: int
    relation: str
    final: float
    positions: list[int]
    sources: list[str]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "EmotionRecord":
        return cls(**data)

@dataclass(frozen = True)
class GrammarRule:
    type: str
    subtype: str
    desc: str = ""
    adjust: float = 1.0
    words: tuple[str, ...] = ()
@dataclass(frozen=True)
class GrammarLexicon:
    pronouns: frozenset[str] = frozenset()
    prepositions: frozenset[str] = frozenset()
    particles: dict[str, float] = field(default_factory = dict)
    punctuations: dict[str, float] = field(default_factory = dict)

@dataclass
class GrammarResult:
    subject: str = ""
    preposition: str = ""
    particle: str = ""
    punctuation: str = ""

    subject_pos: int = -1
    preposition_pos: int = -1
    particle_pos: int = -1
    punctuation_pos: int = -1

    is_sentence: bool = False
    confidence: float = 0.0
@dataclass(frozen = True)
class Edge_processing:
    MIN_LENGTH:int = 3
    SUBJECT_WINDOW:int = 6
    PREP_WINDOW:int = 6
    PUNCT_WINDOW:int = 3

@dataclass
class ClauseNode2:
    text: str
    start: int
    end: int

    level: int = 1
    split_reason: str = ""

    punct: str | None = None
    punct_type: str | None = None
    adjust: float = 1.0

    subject: str = ""
    particle: str = ""
    is_sentence: bool = False

    relation: str | None = None

    parent: "ClauseNode | None" = field(default=None, repr=False, compare=False)
    children: list["ClauseNode"] = field(default_factory=list)

    confidence: float = 0.0

    emotions: list["EmotionScore"] = field(default_factory=list)

    def add_emotion(self, score: "EmotionScore") -> None:
        self.emotions.append(score)

    def dominant(self) -> "EmotionScore | None":
        if not self.emotions:
            return None
        return max(self.emotions, key=lambda e: abs(e.raw * e.intensity))

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("parent", None)
        return d