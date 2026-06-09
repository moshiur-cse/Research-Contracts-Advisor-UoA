import sys
import os
import re
import pdfplumber
from pypdf import PdfReader, PdfWriter
import pypdf.annotations as ann
from pypdf.generic import ArrayObject, FloatObject, NameObject, TextStringObject

#
HIGHLIGHTS = [
    {
        "text": "Artificial intelligence is rapidly transforming",
        "comment": "Strong opening claim — needs a citation.",
        "color": "yellow",
        "author": "Reviewer 1",
    },
    {
        "text": "concerns about academic integrity",
        "comment": "Key concern — expand with recent statistics.",
        "color": "red",
        "author": "Reviewer 1",
    },
    {
        "text": "150 peer-reviewed studies",
        "comment": "Good sample size. Clarify inclusion/exclusion criteria.",
        "color": "green",
        "author": "Reviewer 2",
    },
    {
        "text": "12 countries",
        "comment": "Which countries? List them in an appendix.",
        "color": "blue",
        "author": "Reviewer 2",
    },
    {
        "text": "Preferred Contracting Position",
        "comment": "Define this term — it means different things to different readers.",
        "color": "purple",
        "author": "Reviewer 1",
    },
]

# ── Color map: name → hex RGB (no #) ──────────────────────────────
COLOR_MAP = {
    "yellow": "ffff00",
    "green":  "00cc66",
    "red":    "ff4444",
    "blue":   "4499ff",
    "purple": "bb44ff",
    "orange": "ff9900",
    "pink":   "ff66aa",
}


def hex_to_rgb_floats(hex_color: str) -> tuple[float, float, float]:
    """Convert 6-char hex string to (r, g, b) floats in [0, 1]."""
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))


def normalize(text: str) -> str:
    """Collapse whitespace for robust matching."""
    return re.sub(r"\s+", " ", text).strip()


def find_phrase_words(words: list[dict], phrase: str) -> list[list[dict]]:
    """
    Return all groups of consecutive word dicts that together form `phrase`.
    Handles multi-word phrases and partial-line wrapping.
    """
    phrase_tokens = normalize(phrase).lower().split()
    n = len(phrase_tokens)
    matches = []

    word_texts = [normalize(w["text"]).lower() for w in words]

    for i in range(len(word_texts) - n + 1):
        if word_texts[i : i + n] == phrase_tokens:
            matches.append(words[i : i + n])

    return matches


def annotate_pdf(input_path: str, output_path: str, highlights: list[dict]) -> int:
    """
    Read input_path, add highlight + popup annotations, write to output_path.
    Returns the total number of annotations added.
    """
    reader = PdfReader(input_path)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    total = 0

    with pdfplumber.open(input_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            page_h = float(page.height)

            words = page.extract_words(
                x_tolerance=4,
                y_tolerance=4,
                keep_blank_chars=False,
                use_text_flow=True,
            )

            for hl in highlights:
                phrase  = normalize(hl["text"])
                comment = hl.get("comment", "")
                color   = COLOR_MAP.get(hl.get("color", "yellow"), "ffff00")
                author  = hl.get("author", "Reviewer")

                matched_groups = find_phrase_words(words, phrase)

                for group in matched_groups:
                    x0     = min(w["x0"]     for w in group)
                    x1     = max(w["x1"]     for w in group)
                    top    = min(w["top"]    for w in group)
                    bottom = max(w["bottom"] for w in group)

                    # pdfplumber: y=0 at top; PDF spec: y=0 at bottom
                    pdf_y0 = page_h - bottom   # lower edge in PDF coords
                    pdf_y1 = page_h - top       # upper edge in PDF coords

                    # Slight vertical padding so highlight is visible
                    pad = 1.5
                    pdf_y0 -= pad
                    pdf_y1 += pad

                    # QuadPoints: 4 corners per highlighted quad
                    # PDF spec order: UL, UR, LL, LR
                    qp = ArrayObject([
                        FloatObject(x0),  FloatObject(pdf_y1),   # upper-left
                        FloatObject(x1),  FloatObject(pdf_y1),   # upper-right
                        FloatObject(x0),  FloatObject(pdf_y0),   # lower-left
                        FloatObject(x1),  FloatObject(pdf_y0),   # lower-right
                    ])

                    highlight_ann = ann.Highlight(
                        rect=(x0, pdf_y0, x1, pdf_y1),
                        quad_points=qp,
                        highlight_color=color,
                    )
                    # /Contents  → tooltip text shown on hover
                    # /T         → author label in popup title bar
                    highlight_ann[NameObject("/Contents")] = TextStringObject(comment)
                    highlight_ann[NameObject("/T")]        = TextStringObject(author)

                    writer.add_annotation(page_number=page_num, annotation=highlight_ann)
                    total += 1
                    print(f"  ✅  Page {page_num+1} | [{hl.get('color','yellow'):6s}] "
                          f"\"{phrase[:55]}{'…' if len(phrase)>55 else ''}\"")

    with open(output_path, "wb") as f:
        writer.write(f)

    return total


def main():
    if len(sys.argv) < 2:
        # Demo mode: look for a local sample PDF
        candidates = ["documents.pdf", "sample_test.pdf"]
        input_path = next((p for p in candidates if os.path.exists(p)), None)
        if not input_path:
            print("Usage:  python pdf_highlighter.py input.pdf [output.pdf]")
            sys.exit(1)
    else:
        input_path = sys.argv[1]

    if not os.path.exists(input_path):
        print(f"❌  File not found: {input_path}")
        sys.exit(1)

    stem = os.path.splitext(input_path)[0]
    output_path = sys.argv[2] if len(sys.argv) >= 3 else f"{stem}_highlighted.pdf"

    print(f"\n📄  Input  : {input_path}")
    print(f"💾  Output : {output_path}")
    print(f"🔍  Applying {len(HIGHLIGHTS)} highlight rule(s)…\n")

    count = annotate_pdf(input_path, output_path, HIGHLIGHTS)

    print(f"\n🎉  Done! {count} annotation(s) added → {output_path}")
    print("   Open the PDF in Adobe Reader, Chrome, or any PDF viewer")
    print("   to see highlights and hover/click for comments.\n")


if __name__ == "__main__":
    print("\n=== PDF Highlighter with Mouse-Over Comments ===\n")
    main()
