from main import Intent

intent = Intent()

tests = [
    "今天很好！",
    "虽然很累但是我很开心",
    "因为下雨所以没去。",
    "很适合有车一族来采购，因为没有袋子给的，只有纸箱子！",
]

for text in tests:
    print(f"\n{text!r}")
    print(f"  vad: {intent.vad_only(text)}")
    print(f"  emotions: {intent.emotions_only(text)}")
    r = intent.analyze_emotion(text)
    print(f"  has_emotion: {r is not None}")

print(f"\n缓存: {intent.cache_stats()}")