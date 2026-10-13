import re
import pandas as pd
def clean(text: str) -> str:
    text = str(text)

    text = re.sub(r"http\S+", "", text)

    text = re.sub(
        r"[^\u4e00-\u9fff\u3000-\u303fa-zA-Z0-9]",
        "",
        text,
    )

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def prepare_data(
    csv_path: str,
    n: int = 1000,
    output: str = "data/ratings.txt",
) -> pd.DataFrame:
    df = pd.read_csv(csv_path, header=None, names=["comment"])

    df = df.dropna(subset=["comment"])
    df["comment"] = df["comment"].astype(str)

    df["comment"] = df["comment"].apply(clean)

    df = df[df["comment"].str.len() >= 5]

    df_sample = df.sample(n = min(n, len(df)), random_state=42)

    with open(output, "w", encoding="utf-8") as f:
        for text in df_sample["comment"]:
            f.write(text + "\n")

    print(f"已存 {len(df_sample)} 条")
    print(f"平均长度: {df_sample['comment'].str.len().mean():.0f} 字")

    return df_sample