from grammar_rules import ClauseSplitter
from Text_Data_Labeling import EmotionTypeLabeling


def fill_emotions(node, labeler):
    """递归给每个叶子节点挂情绪。"""
    if node.is_leaf():
        scores = labeler.Text_matching(node.text)
        for emo, s in scores.items():
            node.add_emotion(s)
        return
    for child in node.children:
        fill_emotions(child, labeler)


def print_tree(node, indent=0):
    prefix = "  " * indent
    emos = [e.emotion for e in node.emotions]
    mark = f" → {emos}" if emos else ""
    print(f"{prefix}{node.text!r} (L{node.level}){mark}")
    for c in node.children:
        print_tree(c, indent + 1)


if __name__ == "__main__":
    splitter = ClauseSplitter()
    labeler = EmotionTypeLabeling()

    text = "今天很好！明天更好！"
    tree = splitter.split(text)

    fill_emotions(tree, labeler)
    print_tree(tree)