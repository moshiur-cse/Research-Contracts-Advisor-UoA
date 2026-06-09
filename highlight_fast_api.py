from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
# from highlight_rules import get_highlight_rules
import fitz  # PyMuPDF
import io
import json
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# @app.get("/highlight-rules")
# async def highlight_rules():

#     rules = get_highlight_rules()

#     return {
#         "success": True,
#         "rules": rules
#     }

COLOR_HEX = {
    "Aligns with Standard":   "#4a7c59",
    "Partial Alignment":     "#8a6914",
    "Conflicts with Standard": "#8b2e2e",
    "Requires Assessment":   "#1e4f7a",
}


def process_pdf(pdf_bytes: bytes) -> bytes:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    for page in doc:
        text = page.get_text()
        for rule in HIGHLIGHT_RULES:
            for match in re.finditer(rule["pattern"], text, re.IGNORECASE):
                hits = page.search_for(match.group(0), quads=False)
                for rect in hits:
                    # Draw filled semi-transparent rectangle
                    r, g, b, a = rule["color"]
                    annot = page.add_highlight_annot(rect)
                    annot.set_colors(stroke=(r, g, b))
                    annot.set_opacity(a + 0.3)
                    annot.set_info(
                        title=rule["label"],
                        content=f"{rule['tooltip']}\n\nMatched: \"{match.group(0)}\"",
                    )
                    annot.update()

    buf = io.BytesIO()
    doc.save(buf, garbage=4, deflate=True)
    doc.close()
    return buf.getvalue()


@app.post("/process-pdf")
async def process_pdf_endpoint(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported.")
    raw = await file.read()
    if len(raw) > 50 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 50 MB).")
    try:
        result = process_pdf(raw)
    except Exception as e:
        raise HTTPException(500, f"PDF processing failed: {e}")

    safe_name = file.filename.replace(".pdf", "_highlighted.pdf")
    return StreamingResponse(
        io.BytesIO(result),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


@app.get("/legend")
def get_legend():
    return [
        {"label": r["label"], "color": COLOR_HEX[r["label"]], "tooltip": r["tooltip"]}
        for r in HIGHLIGHT_RULES
    ]
