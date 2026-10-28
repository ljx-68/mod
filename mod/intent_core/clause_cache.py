
import json
from pathlib import Path


class ClauseCache:
    def __init__(self, path="data/cache/clauses.jsonl", max_size=100_000):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_size = max_size
        self._cache: dict[str, dict] = {}
        self._loaded = False
        self._stats = {"hit": 0, "miss": 0, "skipped": 0}

    def _load(self):
        if self._loaded:
            return
        if self.path.exists():
            with self.path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    key = obj.get("text", "")
                    if key:
                        self._cache[key] = obj
        self._loaded = True

    def get(self, text: str) -> dict | None:
        self._load()
        result = self._cache.get(text)
        if result:
            self._stats["hit"] += 1
        else:
            self._stats["miss"] += 1
        return result

    def put(self, text: str, emotions: list, vad: list) -> None:
        self._load()
        if text in self._cache:
            return
        if len(self._cache) >= self.max_size:
            self._stats["skipped"] += 1
            return

        entry = {"text": text, "emotions": emotions, "vad": vad}
        self._cache[text] = entry
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def count(self) -> int:
        self._load()
        return len(self._cache)

    def stats(self) -> dict:
        total = self._stats["hit"] + self._stats["miss"]
        rate = self._stats["hit"] / total * 100 if total else 0
        return {
            "hit": self._stats["hit"],
            "miss": self._stats["miss"],
            "skipped": self._stats["skipped"],
            "hit_rate": f"{rate:.1f}%",
            "cache_size": self.count(),
        }