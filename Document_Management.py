import json
from pathlib import Path
from Types import (NegationLexicon, ContextMatch, ContextPattern, RelationRule, RelationPair,
                   ModifierLexicon, RelationRule, InferenceRecord, EmotionRecord, ClauseRecord)
from datetime import datetime

class DataLoadError(RuntimeError):
    pass
def load_emotion_data(address: str, root: Path | str = ".") -> list[dict]:
    path = Path(root) / "feelings" / address / f"{address}_data.json"

    if not path.exists():
        return []

    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise DataLoadError(f"Invalid JSON: {path}: {e}") from e
    except OSError as e:
        raise DataLoadError(f"Cannot read: {path}: {e}") from e


def _load_json(path: Path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError as e:
        raise DataLoadError(f"File not found: {path}") from e
    except json.JSONDecodeError as e:
        raise DataLoadError(f"Invalid JSON: {path}: {e}") from e
    except OSError as e:
        raise DataLoadError(f"Cannot read: {path}: {e}") from e


def load_negation_lexicon(root: Path | str = ".") -> NegationLexicon:
    base = Path(root) / "Subtle_emotional_shifts"
    reversal = _load_json(base / "Semantic_reversal_data.json")

    words: set[str] = set()
    for item in reversal:
        words.update(item.get("Subtle verb adjustment", []))
    return NegationLexicon(words = frozenset(words))


def load_modifier_lexicon(root: Path | str = ".") -> ModifierLexicon:
    base = Path(root) / "Subtle_emotional_shifts"
    shifts = _load_json(base / "Subtle_emotional_shifts_data.json")
    value: float
    modifiers: dict[str, float] = {}
    for item in shifts:
        if not isinstance(item, dict):
            continue
        value = item.get("value", 1.0)
        for word in item.get("words", []):
            modifiers[word] = value
    return ModifierLexicon(modifiers = modifiers)


def Secondary_judgment_data_loading(
    address: str,
    root: Path | str = ".",)-> tuple[ContextPattern, ...]:
    path = Path(root) / "feelings" / address / f"{address}_Two_data.json"

    if not path.exists():
        return ()

    try:
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as e:
        raise DataLoadError(f"Invalid JSON: {path}: {e}") from e
    except OSError as e:
        raise DataLoadError(f"Cannot read: {path}: {e}") from e

    if not isinstance(raw, list):
        return ()

    patterns = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        if not all(k in item for k in ("name", "emotion", "require_all_groups", "weight")):
            continue
        try:
            patterns.append(ContextPattern(
                name = item["name"],
                emotion = item["emotion"],
                require_all_groups = tuple(tuple(g) for g in item["require_all_groups"]),
                weight = float(item["weight"]),
            ))
        except (TypeError, ValueError):
            continue

    return tuple(patterns)

def load_relation_rules(root: Path | str = ".") -> tuple[RelationRule, ...]:
    path = Path(root) / "Subtle_emotional_shifts" / "Transition_Words_Library.json"

    if not path.exists():
        return ()

    try:
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as e:
        raise DataLoadError(f"Invalid JSON: {path}: {e}") from e
    except OSError as e:
        raise DataLoadError(f"Cannot read: {path}: {e}") from e

    if not isinstance(raw, list):
        return ()

    rules = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        if "name" not in item or "priority" not in item:
            continue

        pairs = tuple(
            RelationPair(
                front = tuple(p.get("front", [])),
                back = tuple(p.get("back", [])),
            )
            for p in item.get("pairs", [])
            if isinstance(p, dict)
        )

        rules.append(RelationRule(
            name = item["name"],
            priority = int(item["priority"]),
            weight = tuple(item.get("weight", (1.0, 1.0))),
            standalone = tuple(item.get("standalone", [])),
            pairs = pairs,
        ))

    return tuple(sorted(rules, key = lambda r: r.priority))

class JSONLStorage:
    def __init__(self, path: str, key: str = "sentence", mod: str = "a"):
        self.path = Path(path)
        self.path.parent.mkdir(parents = True, exist_ok = True)
        self.key = key
        self.mode = mod
        self._seen: set[str] = set()
        self.initialized = False

    def _load_seen(self):
        if self._seen:
            return
        if self.mode == "w" and not self.initialized:
            self.path.write_text("", encoding = "ytf-8")
            self.initialized = True
            return
        if self.path.exists():
            with self.path.open("r", encoding = "utf-8")as f:
                for i in f:
                    line = i.strip()
                    if line:
                        self._seen.add(json.loads(line)[self.key])
    def exists(self, value: str) -> bool:
        self._load_seen()
        return value in self._seen

    def save(self, data: dict) -> bool:
        value = data[self.key]
        if self.exists(value):
            return False
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
        self._seen.add(value)
        return True

def result_to_record(result: tuple) -> InferenceRecord:
    clauses_data, (sentence_text, overall_vad) = result

    clauses = []
    for clause_text, scores, vad in clauses_data:
        emotions = {}
        for emo, s in scores.items():
            emotions[emo] = EmotionRecord(
                raw = s.raw,
                intensity = s.intensity,
                neg_count = s.neg_count,
                relation = s.relation,
                final = s.final,
                positions = list(s.positions),
                sources = list(s.sources),
            )

        relation = ""
        for s in scores.values():
            if s.relation:
                relation = s.relation
                break

        clauses.append(ClauseRecord(
            text = clause_text,
            vad = tuple(vad),
            relation = relation,
            emotions = emotions,
        ))

    return InferenceRecord(
        sentence = sentence_text,
        vad = tuple(overall_vad),
        clauses = clauses,
        version = "v1.0",
        timestamp = datetime.now().isoformat(),
    )


def export_clauses(record: InferenceRecord) -> list[dict]:
    result = []
    for pos, clause in enumerate(record.clauses):
        if not clause.emotions:
            continue
        result.append({
            "sentence": record.sentence,
            "clause": clause.text,
            "clause_vad": list(clause.vad),
            "relation": clause.relation,
            "position": pos,
            "emotions": {
                e: {
                    "raw": s.raw,
                    "intensity": s.intensity,
                    "neg_count": s.neg_count,
                    "final": s.final,
                    "sources": s.sources,
                }
                for e, s in clause.emotions.items()
            },
            "version": record.version,
            "timestamp": record.timestamp,
        })
    return result

def save_both(result, nested_path: str, clause_path: str):
    record = result_to_record(result)

    nested = JSONLStorage(nested_path, key="sentence")
    clause_storage = JSONLStorage(clause_path, key="clause")

    # 1. 整句去重
    if not nested.save(record.to_dict()):
        return False

    for c in export_clauses(record):
        clause_storage.save(c)

    return True
