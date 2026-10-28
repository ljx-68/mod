from mod.intent_core.main import Intent
from mod.intent_core.Document_Management import load_corpus_csv

from pathlib import Path
from mod.intent_core.ClauseStore_File import ClauseStore


class Node:
    def __init__(self, base_dir: str = "data/results", save_data: bool = True):
        self.intent = Intent()
        base: list[str] = [f"{Path(base_dir)}/v0.3_emotion.jsonl", f"{Path(base_dir)}/v0.3_unlabeled.jsonl"]
        self.save_data = save_data

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

    def Data_Loading(self, start_row: int = 100, end_row: int = None):
        corpus = load_corpus_csv("ratings.csv", start_row = start_row, end_row = end_row)
        print(f"读到 {len(corpus)} 条")
        for i, item in enumerate(corpus, 1):
            self.uo_2(i, item, len(corpus))
        if self.save_data:
            self._flush()
            self._print_stats()
    def uo_2(self, i: int, item: dict, corpus: int)->None:
        try:
            tree = self.intent.process(item["text"])
            if self.save_data:
                row = tree.to_dict()
                row["scores"] = item["scores"]
                row["timestamp"] = item["timestamp"]
                is_high_quality = any(
                    c.emotions and c.confidence >= 0.75
                    for c in tree.iter_leaves()
                )
                self.uo(is_high_quality, row)
        except Exception as e:
            print(f"处理失败: {e}")
        if i % 10 == 0:
            print(f"  已处理 {i}/{corpus}")
    def uo(self, is_high_quality: bool, row: dict)->None:
        if is_high_quality:
            self.emotion_store.append(row)
        else:
            self.unlabeled_store.append(row)
    def _flush(self):
        self.emotion_store.flush()
        self.unlabeled_store.flush()

    def _print_stats(self):
        print("\n=== 有情绪库 ===")
        print(self.emotion_store.stats())
        print("\n=== 无情绪库 ===")
        print(self.unlabeled_store.stats())

if __name__ == "__main__":
    Node(save_data = True).Data_Loading(start_row = 0, end_row = None)