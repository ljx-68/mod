
SUBTYPE_TO_TYPE = {
    "exclamation": "strong",
    "question":    "strong",
    "period":      "strong",
    "dash":        "medium",
    "semicolon":   "medium",
    "colon":       "medium",
    "comma":       "weak",
    "enumeration": "weak",
    "tilde":       "weak",
    "ellipsis":    "weak",
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

OPEN_QUOTES = ("“", "”", "‘", "’", '"', "'")

PROTECT_PAIRS = (
    ("“", "”"), ("‘", "’"),
    ("（", "）"), ("(", ")"),
    ("《", "》"), ("【", "】"),
    ("[", "]"), ("{", "}"),
)

URL_STOP = set(" \n\t，。！？；")