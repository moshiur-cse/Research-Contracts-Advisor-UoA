HIGHLIGHT_RULES = [
    {
        "pattern": r"\b(important|critical|urgent|required|must|shall|mandatory)\b",
        "color": (1.0, 0.2, 0.2, 0.35),
        "label": "Aligns with Standard",
        "tooltip": "Clause aligns with UoA standard position.",
    },
    {
        "pattern": r"\b(note|notice|warning|caution|attention)\b",
        "color": (1.0, 0.75, 0.0, 0.35),
        "label": "Partial Alignment",
        "tooltip": "Partial match — review recommended.",
    },
    {
        "pattern": r"\b(definition|defined|means|refers to|hereinafter)\b",
        "color": (0.2, 0.6, 1.0, 0.35),
        "label": "Conflicts with Standard",
        "tooltip": "Conflicts with UoA standard — action required",
    },
    {
        "pattern": r"\b(section|clause|article|paragraph|chapter)\s+\d+[\.\d]*",
        "color": (0.4, 0.85, 0.4, 0.35),
        "label": "Requires Assessment",
        "tooltip": "Not addressed in current UoA standard positions",
    },
]


def get_highlight_rules():
    return HIGHLIGHT_RULES