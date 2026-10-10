from sklearn.feature_extraction.text import TfidfVectorizer
from concurrent.futures.thread import ThreadPoolExecutor
from Text_Data_Labeling import *
from Document_Management import JSONLStorage, result_to_record, export_clauses, save_both
class EmotionTypeLabeling_S:
    def __init__(self):
        self.base_coords = {
            "Joy": (0.85, 0.72, 0.68),
            "Sad": (0.12, 0.35, 0.18),
            "Fear": (0.12, 0.85, 0.20),
            "Anger": (0.12, 0.78, 0.68),
            "Surprise": (0.50, 0.85, 0.25),
            "Anticipation": (0.68, 0.62, 0.55),
            "Love": (0.90, 0.55, 0.60),
            "Disgust": (0.18, 0.52, 0.58),
            "Calm": (0.50, 0.12, 0.58),
            "Trust": (0.78, 0.35, 0.58),
            "Contempt": (0.15, 0.45, 0.72),
            "Anxiety": (0.20, 0.72, 0.25),
            "Shame": (0.15, 0.58, 0.15),
        }
        self.NEGATE_MAP = {
            "Joy":          ("Sad", 1.0),
            "Sad":          ("Joy", 1.0),
            "Fear":         ("Calm", 0.5),
            "Calm":         ("Fear", 0.3),

            "Anger":        ("Trust", 0.5),
            "Trust":        ("Anger", 0.5),

            "Love":         ("Disgust", 0.5),
            "Disgust":      ("Love", 0.5),

            "Anticipation": ("Calm", 0.4),
            "Surprise":     ("Calm", 0.3),

            "Contempt":     ("Trust", 0.3),

            "Anxiety":      ("Calm", 0.5),
        
            "Shame":        ("Joy", 0.2),
        }

class Intent:
    def __init__(self):
        self.labeler = EmotionTypeLabeling()
        self.data_list = EmotionTypeLabeling_S()
    def Sentence_splitting(self, test : str)->tuple[list, tuple]:
        self.test = test
        clauses = [
            c.strip()
            for c in re.split(r'''[\[，。？！；:;,.?!"'‘”/{}、|\\\]]''', test)
            if c.strip()
        ]
        if not clauses:
            return ([], (test, [0.5, 0.5, 0.5]))
        def process(clause):
            scores = self.labeler.Text_matching(clause)
            vad = self.to_vad(scores)
            return clause, scores, vad
        with ThreadPoolExecutor(max_workers = len(clauses)) as executor:
            results = list(executor.map(process, clauses))
        return (results, self.Overall_output(test, results))
    def to_vad(self, scores: dict[str, EmotionScore]) -> list[float]:
        if not scores:
            return [0.5, 0.5, 0.5]
        active = self.item(scores)
        if not active:
            return [0.5, 0.5, 0.5]
        total_raw = sum(active.values())
        weights = {e: v / total_raw for e, v in active.items()}
        V = A = D = 0.0
        for e, w in weights.items():
            coords = self.data_list.base_coords.get(e)
            if coords is None:
                continue
            V += coords[0] * w
            A += coords[1] * w
            D += coords[2] * w
        total_final = sum(abs(i.final) for i in scores.values() if i.final != 0)
        intensity = min(1.0, total_final)
        V = 0.5 + (V - 0.5) * intensity
        A = 0.5 + (A - 0.5) * intensity
        D = 0.5 + (D - 0.5) * intensity
        return [round(max(0, min(1, x)), 2) for x in [V, A, D]]
    def item(self, scores: dict[str, EmotionScore]) -> dict[str, float]:
        if not scores: return {}
        active: dict = {}
        for e, s in scores.items():
            if s.final > 0:
                active[e] = s.raw
            elif s.final < 0:
                t, c = self.data_list.NEGATE_MAP.get(e, (None, 0))
                if t:
                    active[t] = active.get(t, 0) + s.raw * c
        return active

    def Overall_output(self, test: str, data: list)-> tuple[str, list[float]]:
        if not data: return (self.test, [0.5, 0.5, 0.5])
        data = [l for _, _, l in data if l != [0.5, 0.5, 0.5]]
        if not data: return (test, [0.5, 0.5, 0.5])
        V_A_D = [
            round(sum(e[i] for e in data) / len(data), 2) for i in range(3)
        ]
        return (test, V_A_D)
    def Data_Storage(self, texts: list[str]):
        if not texts:
            print("数据错误")
            return
        for text in texts:
            result = self.Sentence_splitting(text)
            saved = save_both(
                result,
                nested_path = "data/inference/v1.0.jsonl",
                clause_path = "data/clause/v1.0.jsonl",
            )
            if saved:
                print(f"已存: {text[:30]}...")
            else:
                print(f"跳过（已存在）: {text[:30]}...")


if __name__ == "__main__":
    op = Intent()
    op.Data_Storage(["我仿佛是一只快乐的小鸟，在幸福的天空中，自由地翱翔！",])