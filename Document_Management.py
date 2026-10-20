import json
import csv
from Roughlyfilter_data import *
from pathlib import Path
from Types import (
    GrammarLexicon, InferenceRecord, ClauseRecord,EmotionScore,
    NegationLexicon, ModifierLexicon,
    ContextPattern, RelationPair, RelationRule,
)
from datetime import datetime
class DataLoadError(RuntimeError):
    pass
def load_emotion_data(address = "feelings", root=".") -> dict[str, list[dict]]:
    path = Path(root) / address
    if not path.exists():
        return {}

    result: dict[str, list[dict]] = {}

    for f in sorted(path.rglob("*.json")):
        if not f.is_file():
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"{f}: JSON loading error : {e}")
            continue
        if not isinstance(data, list):
            continue
        first = data[0] if data and isinstance(data[0], dict) else {}
        kind_field = None
        for k in ("type", "Type", "emotion", "category"):
            if k in first:
                kind_field = k
                break

        if kind_field:
            for entry in data:
                if not isinstance(entry, dict):
                    continue
                kind = entry.get(kind_field)
                if kind:
                    result.setdefault(kind, []).append(entry)
        else:
            result[f.stem] = data

    return result


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
        if self.mode == "w":
            self.path.write_text("", encoding="utf-8")
            self.initialized = True
            return
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if self.key in obj:
                    self._seen.add(obj[self.key])
    def exists(self, value: str) -> bool:
        self._load_seen()
        return value in self._seen

    def save(self, data: dict) -> bool:
        if self.key not in data:
            return False
        value = data[self.key]
        self._load_seen()
        if value in self._seen:
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
            emotions[emo] = EmotionScore(          # ← 改这里
                emotion = emo,                       # ← 补 emotion 字段
                raw = s.raw,
                intensity = s.intensity,
                neg_count = s.neg_count,
                relation = s.relation,
                positions = list(s.positions),
                sources = list(s.sources),
                subjects = list(getattr(s, "subjects", [])),
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

    nested = JSONLStorage(nested_path, key = "sentence")
    clause_storage = JSONLStorage(clause_path, key = "clause")
    if not nested.save(record.to_dict()):
        return False

    for c in export_clauses(record):
        clause_storage.save(c)

    return True

def load_grammar_library(address = "Grammar_structure_library", root="."):
    base = Path(root) / address
    if not base.is_dir():
        return {}
    result: dict[str, list[dict]] = {}
    for i in sorted(base.iterdir()):
        if not i.is_file() or i.suffix != ".json":
            continue
        try:
            data = json.loads(i.read_text(encoding = "utf-8"))
        except json.JSONDecodeError as e:
            print(f"{i.name}: JSON loading error : {e}")
            continue
        if not isinstance(data, list):
            continue
        result[i.stem] = data
    return result

def build_grammar_lexicon(root=".") -> GrammarLexicon:
    raw = load_grammar_library("Grammar_structure_library", root = root)

    def word_set(items):
        s = set()
        for item in items:
            s.update(item.get("words", []))
        return frozenset(s)

    def adjust_map(items):
        d = {}
        for item in items:
            adj = float(item.get("adjust", 1.0))
            for w in item.get("words", []):
                d[w] = adj
        return d

    def subtype_map(items):
        d = {}
        for item in items:
            st = item.get("subtype", "")
            for w in item.get("words", []):
                d[w] = st
        return d

    def by_type(records, type_name):
        return [r for r in records if r.get("type") == type_name]

    def by_type_subtype(records, type_name, subtype_name):
        return [r for r in records
                if r.get("type") == type_name
                and r.get("subtype") == subtype_name]
    punct_records   = raw.get("EndingPunctuation_Library", [])
    closing_records = raw.get("Closing_RemarksVocabulary", [])

    p_subtype = subtype_map(punct_records)
    p_type    = {w: SUBTYPE_TO_TYPE.get(st, "weak") for w, st in p_subtype.items()}

    spo_records = raw.get("Subject_Predicate_Object", [])

    predicates = word_set(by_type(spo_records, "predicate"))
    transitive = word_set(by_type_subtype(spo_records, "predicate", "transitive"))

    objects = word_set(by_type(spo_records, "object"))
    adverbs = word_set(by_type(spo_records, "adverb"))

    continuations = word_set(by_type(spo_records, "continuation"))
    forbidden = word_set(by_type(spo_records, "forbidden"))

    return GrammarLexicon(
        pronouns         = word_set(raw.get("Mainword_data", [])),
        prepositions     = word_set(raw.get("Preposition_database", [])),
        particles        = adjust_map(closing_records),
        punctuations     = adjust_map(punct_records),
        punct_type       = p_type,
        punct_subtype    = p_subtype,
        particle_subtype = subtype_map(closing_records),
        predicates       = predicates,
        objects          = objects,
        transitive       = transitive,
        adverbs          = adverbs,
        continuations    = continuations,
        forbidden        = forbidden,
    )
def load_corpus_csv(
    path: str | Path = "ratings.csv",
    root: str | Path = ".",
    text_col: int = 7,
    timestamp_col: int = 6,
    score_cols: tuple[int, ...] = (3, 4, 5),
    skip_empty: bool = True,
    has_header: bool = True,
    max_rows: int | None = None,
) -> list[dict]:
    file = Path(root) / path
    if not file.exists():
        return []

    rows = []
    with file.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        if has_header:
            next(reader, None)

        for row in reader:
            if max_rows is not None and len(rows) >= max_rows:
                break

            if len(row) <= text_col:
                continue

            text = row[text_col].strip()
            if skip_empty and not text:
                continue

            scores = []
            for c in score_cols:
                if c < len(row) and row[c].strip():
                    try:
                        scores.append(float(row[c]))
                    except ValueError:
                        scores.append(None)
                else:
                    scores.append(None)

            rows.append({
                "text": text,
                "scores": scores,
                "timestamp": row[timestamp_col] if timestamp_col < len(row) else "",
                "user_id": row[0] if len(row) > 0 else "",
                "rest_id": row[1] if len(row) > 1 else "",
            })
    return rows
if __name__ == "__main__":
    build_grammar_lexicon(".")
