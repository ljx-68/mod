
import json
from pathlib import Path
from datetime import datetime


class ClauseStore:
    def __init__(self, path, key = "text", max_size = 100_000,
                 backup_dir = None, backup_max_size = 50_000):

        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.key = key
        self.max_size = max_size
        self.backup_dir = Path(backup_dir) if backup_dir else self.path.parent / "replaced"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self._cache: dict[str, dict] = {}
        self._loaded = False
        self._dirty = False
        self._stats = {"inserted": 0, "updated": 0, "skipped": 0, "rejected": 0}

        self.backup_max_size = backup_max_size
        self._backup_count = 0
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
                    if self.key in obj:
                        self._cache[obj[self.key]] = obj
        self._loaded = True

    def _backup(self, old: dict) -> None:
        if self._backup_count >= self.backup_max_size:
            return
        fp = self.backup_dir / f"replaced_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with fp.open("a", encoding="utf-8") as f:
            f.write(json.dumps(old, ensure_ascii=False) + "\n")
        self._backup_count += 1

    def has(self, value: str) -> bool:
        self._load()
        return value in self._cache

    def get(self, value: str) -> dict | None:
        self._load()
        return self._cache.get(value)

    def append(self, data: dict) -> str:
        self._load()
        if self.key not in data:
            return "skipped"
        value = data[self.key]

        if value in self._cache:
            if self._cache[value] == data:
                self._stats["skipped"] += 1
                return "skipped"
            self._backup(self._cache[value])
            self._cache[value] = data
            self._dirty = True
            self._stats["updated"] += 1
            return "updated"

        if len(self._cache) >= self.max_size:
            self._stats["rejected"] += 1
            return "rejected"

        self._cache[value] = data
        self._dirty = True
        self._stats["inserted"] += 1
        return "inserted"

    def flush(self):
        if not self._dirty:
            return
        tmp = self.path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            for obj in self._cache.values():
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        tmp.replace(self.path)
        self._dirty = False

    def count(self) -> int:
        self._load()
        return len(self._cache)

    def iter_all(self):
        self._load()
        yield from self._cache.values()

    def stats(self) -> dict:
        return {
            **self._stats,
            "total": len(self._cache),
            "max_size": self.max_size,
        }