from Types import ClauseNode
def format_analyze(text: str, tree: ClauseNode) -> dict:
    return {
        "text": text,
        "vad": tree.vad,
        "has_emotion": tree.has_emotion(),
        "tree": tree.to_dict(),
        "clauses": [
            {
                "text": leaf.text,
                "vad": leaf.vad,
                "emotions": [e.emotion for e in leaf.emotions],
                "has_emotion": bool(leaf.emotions),
            }
            for leaf in tree.iter_leaves()
        ],
    }
