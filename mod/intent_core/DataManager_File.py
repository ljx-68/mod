from pathlib import Path
from .ClauseStore_File import ClauseStore


class DataManager:
    def __init__(self, root: str = "data"):
        self.root = Path(root)
        self._stores: dict[str, ClauseStore] = {}

    def _get_store(self, category: str, branch: str = "default") -> ClauseStore:
        key = f"{category}/{branch}"
        if key not in self._stores:
            path = self.root / category / branch / "data.jsonl"
            self._stores[key] = ClauseStore(str(path))
        return self._stores[key]

    def add_unlabeled(self, row: dict, branch: str = "default") -> str:
        store = self._get_store("unlabeled", branch)
        return store.append(row)

    def add_labeled(self, row: dict, split: str = "train", branch: str = "default") -> str:
        category = f"labeled/{split}"
        store = self._get_store(category, branch)
        return store.append(row)

    def flush_all(self):
        for store in self._stores.values():
            store.flush()

    def stats(self) -> dict:
        result = {}
        for key, store in self._stores.items():
            result[key] = store.count()
        return result