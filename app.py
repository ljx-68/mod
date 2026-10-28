import gradio as gr
import plotly.graph_objects as go
import json
from mod.intent_core.main import Intent

intent = Intent(use_cache=True)

EMOTION_MAP = {
    "Joy": "Joy", "Sad": "Sad", "Fear": "Fear", "Anger": "Anger",
    "Surprise": "Surprise", "Anticipation": "Anticipation", "Love": "Love",
    "Disgust": "Disgust", "Calm": "Calm", "Trust": "Trust",
    "Contempt": "Contempt", "Anxiety": "Anxiety", "Shame": "Shame"
}

# 颜色映射：根据断句层级或情绪给文字上色
COLOR_MAP = {
    1: "#60A5FA",  # 亮蓝：L1 标点
    2: "#34D399",  # 亮绿：L2 主谓宾
    3: "#FBBF24",  # 亮黄：L3 语气
    4: "#F87171",  # 亮红：L4 关系（因果/转折）
    5: "#A78BFA"  # 亮紫：L5 树化
}


def generate_highlighted_html(tree):
    """更安全的递归高亮生成器，确保不会破坏 HTML 结构"""
    text = tree.get("text", "")
    if not text:
        return ""

    level = tree.get("level", 1)
    color = COLOR_MAP.get(level, "#E5E7EB")  # 默认浅灰色
    rel = tree.get("relation")

    # 如果有关系标签（比如 so/but），并且是父节点
    rel_tag = f"<span style='font-size:12px;background:{color};color:white;border-radius:4px;padding:0 4px;margin-right:4px;'>{rel}</span>" if rel else ""

    if tree.get("children"):
        inner_html = "".join([generate_highlighted_html(c) for c in tree["children"]])
        # 父节点不重复显示文本，只显示关系标签和子节点内容
        return f"<span style='margin-right:8px;'>{rel_tag}{inner_html}</span>"
    else:
        # 叶子节点显示文本
        return f"<span style='color:{color}; margin-right:8px;'>{text}</span>"


def create_radar_chart(emotions_dict):
    categories = list(EMOTION_MAP.values())
    # 如果没有任何情绪，给一个极小的底数值，防止雷达图完全缩成一个点
    values = [emotions_dict.get(k, 0) for k in EMOTION_MAP.keys()]
    max_val = max(max(values), 1.0)

    categories.append(categories[0])
    values.append(values[0])

    fig = go.Figure(data=go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        line_color='#8B5CF6',
        fillcolor='rgba(139, 92, 246, 0.3)'
    ))

    fig.update_layout(
        polar=dict(
            bgcolor='rgba(0,0,0,0)',  # 透明背景
            radialaxis=dict(
                visible=True,
                range=[0, max_val],
                gridcolor='#4B5563',
                tickfont=dict(color='#9CA3AF')
            ),
            angularaxis=dict(
                gridcolor='#4B5563',
                tickfont=dict(color='#E5E7EB')
            )
        ),
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',  # 图表整体透明
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=50, r=50, t=50, b=50),
        height=400
    )
    return fig


def analyze_text(text):
    if not text.strip():
        return "Please enter text", "", "", None, "{}"

    result = intent.analyze(text)
    tree = result["tree"]

    vad = result["vad"]
    vad_text = f"**V (Valence):** {vad[0]}\n\n**A (Arousal):** {vad[1]}\n\n**D (Dominance):** {vad[2]}"

    # 彩色高亮 HTML
    highlighted_html = f"<div style='font-size: 22px; line-height: 2; font-family: sans-serif;'>{generate_highlighted_html(tree)}</div>"

    clauses = result["clauses"]
    clause_info = []
    for c in clauses:
        emos = ", ".join(c["emotions"]) if c["emotions"] else "Neutral"
        clause_info.append(f"• {c['text']} -> [{emos}] VAD: {c['vad']}")
    clauses_text = "\n".join(clause_info)

    global_emotions = intent.emotions_only(text)
    radar_fig = create_radar_chart(global_emotions)

    tree_text = json.dumps(tree, ensure_ascii=False, indent=2)

    return highlighted_html, vad_text, clauses_text, radar_fig, tree_text


with gr.Blocks(title="Emotion Engine") as demo:
    gr.Markdown("## 🧠 Chinese Text Segmentation & Emotion Analysis")

    with gr.Row():
        with gr.Column(scale=2):
            text_input = gr.Textbox(label="Input Chinese Text", lines=3,
                                    placeholder="Example: 虽然今天很累，但是我很开心！")
            btn = gr.Button("Analyze Text", variant="primary")
            gr.Markdown("### 🔍 Segmentation Highlight")
            html_output = gr.HTML()

        with gr.Column(scale=1):
            gr.Markdown("### 📊 Emotion Radar")
            radar_output = gr.Plot()
            gr.Markdown("### 📈 Overall VAD")
            vad_output = gr.Markdown()

    with gr.Accordion("📝 Clause Details & Raw JSON", open=False):
        with gr.Row():
            clause_output = gr.Textbox(label="Clause Breakdown", lines=6)
            tree_output = gr.Code(label="Structure Tree (JSON)", language="json")

    btn.click(fn=analyze_text, inputs=text_input,
              outputs=[html_output, vad_output, clause_output, radar_output, tree_output])
    text_input.submit(fn=analyze_text, inputs=text_input,
                      outputs=[html_output, vad_output, clause_output, radar_output, tree_output])

if __name__ == "__main__":
    # 如果你在国内，启动前请在终端运行：$env:HF_ENDPOINT="https://hf-mirror.com"
    demo.launch(share = True)