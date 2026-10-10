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
            liens = f.readlines()
        return [line.strip() for line in liens[:10] if line.strip()]
    def annotate(self):
        data = self.intent.Data_Storage(self.df)
        print(data)
    def sample_jsonl(self, path: str, n: int = 10) -> list[str]:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return [line.strip() for line in lines[:n] if line.strip()]


if __name__ == "__main__":
    op = Dataloop()
    t = op.sample_jsonl("data/clause/v1.0.jsonl")
    print(t)
