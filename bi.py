from grammar_rules import EmotionTypeLabeling


def main():
    labeler = EmotionTypeLabeling()

    cases = [
        # ── L3 语气词 ──
        "你去吗",
        "我很开心呢",
        "走吧",
        "今天真好呀",
        "我吃了",
        "买得多的话就更好了",
        "可是东西好啊，",

        # ── 长文本 ──
        "很适合有车一族来采购，因为没有袋子给的，只有纸箱子！感觉有点像仓库，可是东西好啊，买得多的话就更好了",
    ]

    for text in cases:
        print(f"\n{'='*60}")
        print(f"IN : {text!r}")

        l1 = labeler.split_l1(text)
        l2 = labeler.split_l2(l1)
        l3 = labeler.split_l3(l2)

        print(f"  L1: {len(l1)} 条 → L2: {len(l2)} 条 → L3: {len(l3)} 条")
        for n in l3:
            marks = []
            if n.is_question:    marks.append("Q")
            if n.is_exclamation: marks.append("!")
            mark = f"[{''.join(marks)}]" if marks else "[ ]"

            print(f"  {mark:4s} L{n.level} {n.text!r}")
            print(f"          particle={n.particle!r} "
                  f"sub={n.particle_subtype or '-':12s} "
                  f"conf={n.confidence}")


if __name__ == "__main__":
    main()