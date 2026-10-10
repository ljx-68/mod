from main import *
import random
import json
class Dataloop:
    def __init__(self):
        self.df = self.load_texts()
        self.intent = Intent()
    def load_texts(self)->list[str]:
        address: str = "data/ratings.txt"
        with open(address, "r", encoding = "utf-8")as f:
            return [line.strip() for line in f if line.strip()]
    def annotate(self):
        data = self.intent.Data_Storage(self.df)
        print(data)
    def sample_jsonl(self, path: str, n: int = 10) -> list[dict]:
        with open(path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        sample = random.sample(lines, min(n, len(lines)))
        return [json.loads(line) for line in sample]


if __name__ == "__main__":
    op = Dataloop()
    t = op.sample_jsonl("data/clause/v1.0.jsonl")
    for s in t:
        print(s["clause"], s["emotions"])
