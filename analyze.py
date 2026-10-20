import json
from pathlib import Path
from collections import Counter


def iter_leaves(node):
    if not node.get("children"):
        yield node
        return
    for c in node["children"]:
        yield from iter_leaves(c)


def iter_all(node):
    yield node
    for c in node.get("children", []):
        yield from iter_all(c)


def main():
    path = Path("78/data/results/v0.3.jsonl")
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l]

    print(f"总条数: {len(rows)}")

    # 子句数
    clause_counts = [len(list(iter_leaves(r["tree"]))) for r in rows]
    print(f"\n子句数:")
    print(f"  平均: {sum(clause_counts) / len(clause_counts):.1f}")
    print(f"  最多: {max(clause_counts)}")
    print(f"  最少: {min(clause_counts)}")

    # 情绪命中
    total_leaves = with_emotion = 0
    for r in rows:
        for leaf in iter_leaves(r["tree"]):
            total_leaves += 1
            if leaf.get("emotions"):
                with_emotion += 1

    print(f"\n情绪命中:")
    print(f"  总子句: {total_leaves}")
    print(f"  有情绪: {with_emotion} ({with_emotion / total_leaves * 100:.1f}%)")

    # VAD 分布
    vads = [r["vad"] for r in rows if r["vad"] != [0.5, 0.5, 0.5]]
    if vads:
        print(f"\nVAD:")
        for i, name in enumerate(["V", "A", "D"]):
            vs = [v[i] for v in vads]
            print(f"  {name}: 均值={sum(vs)/len(vs):.2f} "
                  f"最小={min(vs):.2f} 最大={max(vs):.2f}")

    # 关系
    rels = Counter()
    for r in rows:
        for node in iter_all(r["tree"]):
            if node.get("relation"):
                rels[node["relation"]] += 1

    print(f"\n关系:")
    for rel, cnt in rels.most_common():
        print(f"  {rel}: {cnt}")

    # 置信度分布
    buckets = Counter()
    for r in rows:
        for leaf in iter_leaves(r["tree"]):
            c = leaf["confidence"]
            if c >= 0.95:    buckets["0.95+"] += 1
            elif c >= 0.85:  buckets["0.85-0.95"] += 1
            elif c >= 0.75:  buckets["0.75-0.85"] += 1
            elif c >= 0.65:  buckets["0.65-0.75"] += 1
            else:            buckets["< 0.65"] += 1

    print(f"\n置信度分布:")
    for k in ["0.95+", "0.85-0.95", "0.75-0.85", "0.65-0.75", "< 0.65"]:
        print(f"  {k}: {buckets[k]}")


if __name__ == "__main__":
    main()