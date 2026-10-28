import gradio as gr
import json
import math
from mod.intent_core.main import Intent

intent = Intent(use_cache=True)

EMOTION_MAP = {
    "Joy": "Joy", "Sad": "Sad", "Fear": "Fear", "Anger": "Anger",
    "Surprise": "Surprise", "Anticipation": "Anticipation", "Love": "Love",
    "Disgust": "Disgust", "Calm": "Calm", "Trust": "Trust",
    "Contempt": "Contempt", "Anxiety": "Anxiety", "Shame": "Shame"
}

COLOR_MAP = {
    1: "#60A5FA", 2: "#34D399", 3: "#FBBF24", 4: "#F87171", 5: "#A78BFA"
}


def generate_highlighted_html(tree):
    text = tree.get("text", "")
    if not text: return ""
    level = tree.get("level", 1)
    color = COLOR_MAP.get(level, "#E5E7EB")
    rel = tree.get("relation")
    rel_tag = f"<span style='font-size:12px;background:{color};color:white;border-radius:4px;padding:0 4px;margin-right:4px;'>{rel}</span>" if rel else ""

    if tree.get("children"):
        inner_html = "".join([generate_highlighted_html(c) for c in tree["children"]])
        return f"<span style='margin-right:8px;'>{rel_tag}{inner_html}</span>"
    else:
        return f"<span style='color:{color}; margin-right:8px;'>{text}</span>"


def create_svg_radar(emotions_dict):
    categories = list(EMOTION_MAP.keys())
    values = [emotions_dict.get(k, 0) for k in EMOTION_MAP.keys()]
    n = len(categories)
    max_val = max(max(values), 1.0)

    center = 180
    radius = 100

    points = []
    for i, val in enumerate(values):
        angle = math.pi / 2 - 2 * math.pi * i / n
        r = (val / max_val) * radius
        x = center + r * math.cos(angle)
        y = center - r * math.sin(angle)
        points.append(f"{x},{y}")

    polygon_points = " ".join(points)

    svg = f'<svg width="360" height="360" viewBox="0 0 360 360" style="background: transparent;">'

    # 背景同心圆
    for r in [radius * 0.33, radius * 0.66, radius]:
        circle_points = []
        for i in range(n):
            angle = math.pi / 2 - 2 * math.pi * i / n
            x = center + r * math.cos(angle)
            y = center - r * math.sin(angle)
            circle_points.append(f"{x},{y}")
        svg += f'<polygon points="{" ".join(circle_points)}" fill="none" stroke="#4B5563" stroke-width="1"/>'

    for i, (cat, val) in enumerate(zip(categories, values)):
        angle = math.pi / 2 - 2 * math.pi * i / n
        x = center + radius * math.cos(angle)
        y = center - radius * math.sin(angle)
        svg += f'<line x1="{center}" y1="{center}" x2="{x}" y2="{y}" stroke="#4B5563" stroke-width="1"/>'

        tx = center + (radius + 35) * math.cos(angle)
        ty = center - (radius + 35) * math.sin(angle)
        text_anchor = "middle"
        if tx > center + 15:
            text_anchor = "start"
        elif tx < center - 15:
            text_anchor = "end"
        svg += f'<text x="{tx}" y="{ty}" fill="#E5E7EB" font-size="11" font-weight="500" text-anchor="{text_anchor}" dominant-baseline="middle">{cat}</text>'

    svg += f'<polygon points="{polygon_points}" fill="rgba(139, 92, 246, 0.4)" stroke="#8B5CF6" stroke-width="2"/>'
    svg += '</svg>'
    return f'<div style="display:flex; justify-content:center; align-items:center; height:360px;">{svg}</div>'


def analyze_text(text):
    if not text.strip():
        return "Please enter text", "", "", "", "{}"

    result = intent.analyze(text)
    tree = result["tree"]

    vad = result["vad"]
    vad_text = f"**V (Valence):** {vad[0]}\n\n**A (Arousal):** {vad[1]}\n\n**D (Dominance):** {vad[2]}"
    highlighted_html = f"<div style='font-size: 22px; line-height: 2; font-family: sans-serif;'>{generate_highlighted_html(tree)}</div>"

    clauses = result.get("clauses", [])
    clause_info = []
    for c in clauses:
        emos = ", ".join(c["emotions"]) if c.get("emotions") else "Neutral"
        clause_info.append(f"• {c['text']} -> [{emos}] VAD: {c['vad']}")
    clauses_text = "\n".join(clause_info) if clause_info else "No specific clauses found."

    global_emotions = intent.emotions_only(text)
    radar_html = create_svg_radar(global_emotions)
    tree_text = json.dumps(tree, ensure_ascii=False, indent=2)

    return highlighted_html, vad_text, clauses_text, radar_html, tree_text


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
            radar_output = gr.HTML()
            gr.Markdown("### 📈 Overall VAD")
            vad_output = gr.Markdown()

    with gr.Accordion("📝 Clause Details & Raw JSON", open=True):  # 默认展开，方便看Bug
        with gr.Row():
            clause_output = gr.Textbox(label="Clause Breakdown", lines=4)
            tree_output = gr.Code(label="Structure Tree (JSON)", language="json")

    btn.click(fn=analyze_text, inputs=text_input,
              outputs=[html_output, vad_output, clause_output, radar_output, tree_output])
    text_input.submit(fn=analyze_text, inputs=text_input,
                      outputs=[html_output, vad_output, clause_output, radar_output, tree_output])

if __name__ == "__main__":
    demo.launch()