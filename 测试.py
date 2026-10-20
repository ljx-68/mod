from main import Intent

intent = Intent()

text = "感觉有点像仓库，可是东西好啊，买得多的话就更好了"

# 第一次
tree1 = intent.process(text)
print("第一次:", [e.emotion for e in tree1.emotions], tree1.vad)

# 第二次（应该命中缓存）
tree2 = intent.process(text)
print("第二次:", [e.emotion for e in tree2.emotions], tree2.vad)

print("缓存统计:", intent.cache_stats())