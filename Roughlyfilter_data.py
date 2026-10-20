SUBTYPE_TO_TYPE = {
    "question":    "strong",
    "period":      "strong",
    "ellipsis":    "strong",
    "exclamation": "strong",
    "space": "weak",

    "dash":        "protect",
    "semicolon":   "protect",
    "colon":       "protect",
    "comma":       "protect",
    "enumeration": "protect",
    "tilde":       "protect",
    "quotation":   "protect",
    "bracket":     "protect",
}

PARTICLE_CONF_BASE = 0.6
PARTICLE_CONF_STEP = 0.15
PARTICLE_CONF_MAX  = 0.85

BASE_CONF = {
    "strong":  0.95,
    "medium":  0.80,
    "weak":    0.65,
    "tail":    0.50,
    "protect": 0.0,
}

BASE_COORDS = {
    "Joy":          (0.85, 0.72, 0.68),
    "Sad":          (0.12, 0.35, 0.18),
    "Fear":         (0.12, 0.85, 0.20),
    "Anger":        (0.12, 0.78, 0.68),
    "Surprise":     (0.50, 0.85, 0.25),
    "Anticipation": (0.68, 0.62, 0.55),
    "Love":         (0.90, 0.55, 0.60),
    "Disgust":      (0.18, 0.52, 0.58),
    "Calm":         (0.50, 0.12, 0.58),
    "Trust":        (0.78, 0.35, 0.58),
    "Contempt":     (0.15, 0.45, 0.72),
    "Anxiety":      (0.20, 0.72, 0.25),
    "Shame":        (0.15, 0.58, 0.15),
}

NEGATE_MAP = {
    "Joy":          ("Sad",     1.0),
    "Sad":          ("Joy",     1.0),
    "Fear":         ("Calm",    0.5),
    "Calm":         ("Fear",    0.3),
    "Anger":        ("Trust",   0.5),
    "Trust":        ("Anger",   0.5),
    "Love":         ("Disgust", 0.5),
    "Disgust":      ("Love",    0.5),
    "Anticipation": ("Calm",    0.4),
    "Surprise":     ("Calm",    0.3),
    "Contempt":     ("Trust",   0.3),
    "Anxiety":      ("Calm",    0.5),
    "Shame":        ("Joy",     0.2),
}

OPEN_QUOTES = ("“", "”", "‘", "’", '"', "'")

PROTECT_PAIRS = (
    ("“", "”"), ("‘", "’"),
    ("（", "）"), ("(", ")"),
    ("《", "》"), ("【", "】"),
    ("[", "]"), ("{", "}"),
)

URL_STOP = set(" \n\t，。！？；")