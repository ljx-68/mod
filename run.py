from main import Intent
from ClauseStore_File import ClauseStore
from Document_Management import load_corpus_csv

from pathlib import Path
from ClauseStore_File import ClauseStore


class Node:
    def __init__(self, base_dir: str = "data/results"):
        self.intent = Intent()
        base: list[str] = [f"{Path(base_dir)}/v0.3_emotion.jsonl", f"{Path(base_dir)}/v0.3_unlabeled.jsonl"]


        self.emotion_store = ClauseStore(
            base[0],
            key = "text",
            max_size = 100_000,
        )
        self.unlabeled_store = ClauseStore(
            base[1],
            key = "text",
            max_size = 200_000,
        )

    def Data_Loading(self, max_rows=100):
        corpus = load_corpus_csv("ratings.csv", max_rows=max_rows)
        print(f"读到 {len(corpus)} 条")

        for i, item in enumerate(corpus, 1):
            try:
                tree = self.intent.process(item["text"])
                row = tree.to_dict()
                row["scores"] = item["scores"]
                row["timestamp"] = item["timestamp"]

                if tree.emotions or any(c.emotions for c in tree.children):
                    self.emotion_store.append(row)
                else:
                    self.unlabeled_store.append(row)

            except Exception as e:
                print(f"#{i} 失败: {e}")

            if i % 10 == 0:
                print(f"  已处理 {i}/{len(corpus)}")

        self._flush()
        self._print_stats()

    def _flush(self):
        self.emotion_store.flush()
        self.unlabeled_store.flush()

    def _print_stats(self):
        print("\n=== 有情绪库 ===")
        print(self.emotion_store.stats())
        print("\n=== 无情绪库 ===")
        print(self.unlabeled_store.stats())

if __name__ == "__main__":
    Node().Data_Loading(max_rows = 1000)