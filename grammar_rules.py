from Document_Management import build_grammar_lexicon
from Types import *
import re
class EmotionTypeLabeling:
    def __init__(self, root = "."):
        self.grammar = build_grammar_lexicon(root = root)
        self.WEIGHTS = {
            "subject": 0.35,
            "punctuation": 0.30,
            "preposition": 0.20,
            "particle": 0.15,
        }
    def Sentence_splitting(self, test : str = "")->list[ClauseNode]:
        clauses = [
            c.strip()
            for c in re.findall(r'[^，。？！；:;,.?!"\'‘”/{}、|\\\[\]]+[，。？！；:;,.?!"\'‘”/{}、|\\\[\]]*', test)
            if c.strip() and len(c.strip()) > 2
        ]
        return clauses
    def Output(self, text: str = ""):
        print(self.grammar.punctuations)
    def analyze(self, text: str) -> GrammarResult:
        result = GrammarResult()

        if not text or len(text) < Edge_processing.MIN_LENGTH:
            return result

        n = len(text)


        result.subject, result.subject_pos = self._find(
            text, self.grammar.pronouns, 0, min(Edge_processing.SUBJECT_WINDOW, n)
        )

        result.preposition, result.preposition_pos = self._find(
            text, self.grammar.prepositions, 0, min(Edge_processing.PREP_WINDOW, n)
        )

        result.particle, result.particle_pos = self._find(
            text, self.grammar.particles.keys(), 0, n
        )

        result.punctuation, result.punctuation_pos = self._find(
            text, self.grammar.punctuations.keys(),
            max(0, n - Edge_processing.PUNCT_WINDOW), n
        )

        result.confidence = self._compute_confidence(result)
        result.is_sentence = bool(
            result.subject and (
                    result.object or result.punctuation or result.particle
            )
        )
        return result
    def _find(self, text: str, words, start: int, end: int):
        for i in range(start, min(end, len(text))):
            for length in (4, 3, 2, 1):
                if i + length > len(text):
                    continue
                word = text[i:i + length]
                if word in words:
                    return word, i
        return "", -1

    def _compute_confidence(self, r: GrammarResult) -> float:
        score = 0.0
        if r.subject:
            score += self.WEIGHTS["subject"]
        if r.punctuation:
            score += self.WEIGHTS["punctuation"]
        if r.preposition:
            score += self.WEIGHTS["preposition"]
        if r.particle:
            score += self.WEIGHTS["particle"]
        return round(min(1.0, score), 2)
    def analyze_tree(self, node, labeler, grammar_analyzer) -> None:
        if node.is_leaf():
            node.grammar = grammar_analyzer.analyze(node.text)
            node.emotion = labeler.Text_matching(node.text, node.grammar)
            node.confidence = node.grammar.confidence
            return
        for child in node.children:
            self.analyze_tree(child, labeler, grammar_analyzer)

        child_conf = [c.confidence for c in node.children if c.confidence > 0]
        if child_conf:
            node.confidence = round(sum(child_conf) / len(child_conf), 2)
        else:
            node.confidence = 0.0

        if node.level <= 2:
            node.confidence = min(1.0, node.confidence + 0.1)
if __name__ == "__main__":
    labeler = EmotionTypeLabeling()
    labeler.Output()
    # labeler.Output("喜欢在麦德龙购物已经5，6年了。自从麦德龙开了没多久，几个败家妈妈就发现了它，平均一礼拜来一次，还是开车从湘潭来。（汗一个先~老说便宜，其实来回的油钱和过桥过路费都不知道多少了。。。）")