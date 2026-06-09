import shutil

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
import fitz  # PyMuPDF
import io
import json
import base64

from backend.process_main import generate_json
from backend.writer import process_clause
from backend.template_matcher import match_templates, get_template_content

import re
import sys
from collections import Counter
from pathlib import Path

# ── OCR imports ───────────────────────────────────────────────────────────────
import pytesseract

if sys.platform == "win32":
    import os
    _candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Users\{}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe".format(
            os.environ.get("USERNAME", "")
        ),
    ]
    for _path in _candidates:
        if Path(_path).exists():
            pytesseract.pytesseract.tesseract_cmd = _path
            break
    else:
        pytesseract.pytesseract.tesseract_cmd = "tesseract"

from PIL import Image

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Flag color maps (no emojis) ───────────────────────────────────────────────
FLAG_COLOR_MAP: dict[str, tuple[float, float, float]] = {
    "Red Flag":   (0.85, 0.15, 0.15),
    "Amber Flag": (0.95, 0.70, 0.10),
    "Green Flag": (0.18, 0.65, 0.28),
    "Blue Flag":  (0.15, 0.45, 0.80),
}
FLAG_HEX_MAP: dict[str, str] = {
    "Red Flag":   "#d92626",
    "Amber Flag": "#f2b210",
    "Green Flag": "#2ea647",
    "Blue Flag":  "#2673cc",
}
HIGHLIGHT_OPACITY = 0.45
RULES_PATH = Path(__file__).parent / "clauses_with_risk.json"


def normalize_flag(raw: str) -> str:
    """Normalize any flag_color variant to a plain canonical key (no emojis)."""
    cleaned = raw.strip()
    # Strip leading emoji character(s) if present
    cleaned = re.sub(r'^[\U00010000-\U0010ffff\u2600-\u27BF]\s*', '', cleaned)
    # Title-case so 'red flag' -> 'Red Flag'
    cleaned = cleaned.title()
    return cleaned if cleaned in FLAG_COLOR_MAP else "Amber Flag"


def _fmt_confidence(raw) -> str:
    """Accept float (0.85), int (85), or string ('85%' / '0.85') → '85%'."""
    if isinstance(raw, str):
        raw = raw.strip().rstrip("%")
        try:
            val = float(raw)
            return f"{val:.0%}" if val <= 1.0 else f"{val:.0f}%"
        except ValueError:
            return raw
    try:
        val = float(raw)
        return f"{val:.0%}" if val <= 1.0 else f"{val:.0f}%"
    except (TypeError, ValueError):
        return str(raw)


def load_clause_rules(path: Path = RULES_PATH) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


CLAUSE_RULES: list[dict] = load_clause_rules()

# ── Per-request caches ────────────────────────────────────────────────────────
_ocr_token_cache: dict[int, list] = {}
_image_page_cache: dict[int, bool] = {}


# ── Drawing helpers ───────────────────────────────────────────────────────────

def _hex_to_rgb(h: str) -> tuple[float, float, float]:
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def _draw_rect(shape: fitz.Shape, x0, y0, x1, y1,
               fill=None, color=None, width: float = 0.5) -> None:
    shape.draw_rect(fitz.Rect(x0, y0, x1, y1))
    shape.finish(fill=fill, color=color or fill, width=width)


def _draw_circle(shape: fitz.Shape, cx, cy, r, fill) -> None:
    shape.draw_circle(fitz.Point(cx, cy), r)
    shape.finish(fill=fill, color=fill, width=0)


def _text(page: fitz.Page, x, y, t: str,
          size: float = 10, color=(0.0, 0.0, 0.0), bold: bool = False) -> None:
    page.insert_text(
        (x, y), str(t),
        fontsize=size,
        color=color,
        fontname="Helvetica-Bold" if bold else "Helvetica",
    )


# ── Summary page builder ──────────────────────────────────────────────────────

def build_summary_pages(doc: fitz.Document, annotations: list[dict]) -> None:
    """
    Append summary page(s) at the END of the document.

    • Deduplicates by clause_id so counts and totals always match.
    • Automatically spans multiple pages when there are more clauses than
      fit on a single page.
    • Page 1: header + colour cards + table start.
    • Page 2+: header (with page n of N) + table continuation + footer.
    """
    # ── Deduplicate: keep first occurrence of each clause_id ─────────────────
    seen_ids: set = set()
    unique_rows: list[dict] = []
    for a in annotations:
        if a["clause_id"] not in seen_ids:
            seen_ids.add(a["clause_id"])
            unique_rows.append(a)

    # Counts from unique clauses only → fixes header/card mismatch
    counts = Counter(a["flag_color"] for a in unique_rows)
    total  = len(unique_rows)

    # ── Layout constants ──────────────────────────────────────────────────────
    W, H         = 595, 842
    NAVY         = (0.10, 0.12, 0.22)
    LGRAY        = (0.97, 0.97, 0.98)
    HEADER_H     = 90
    FOOTER_H     = 36
    CARD_W       = 118
    CARD_H       = 88
    CARD_GAP     = 18
    CARDS_Y      = 116
    TABLE_COL_X  = [50, 145, 252, 362, 468]
    HEADERS      = ["Clause", "Flag", "Severity", "Confidence", "Page"]
    ROW_H        = 22
    MAX_Y        = H - FOOTER_H - 10

    # Table header y and first-row y on page 1 (below the colour cards)
    TABLE_Y_P1   = CARDS_Y + CARD_H + 42
    FIRST_ROW_P1 = TABLE_Y_P1 + 24

    # Table header y and first-row y on continuation pages
    TABLE_Y_CONT  = HEADER_H + 20
    FIRST_ROW_CONT = TABLE_Y_CONT + 24

    rows_page1    = max(0, int((MAX_Y - FIRST_ROW_P1)  // ROW_H))
    rows_per_cont = max(0, int((MAX_Y - FIRST_ROW_CONT) // ROW_H))

    # Split unique rows into page-sized chunks
    chunks: list[list[dict]] = []
    chunks.append(unique_rows[:rows_page1])
    rest = unique_rows[rows_page1:]
    while rest:
        chunks.append(rest[:rows_per_cont])
        rest = rest[rows_per_cont:]

    total_pages = len(chunks)

    short_labels = {
        "Red Flag":   "Red",
        "Amber Flag": "Amber",
        "Green Flag": "Green",
        "Blue Flag":  "Blue",
    }

    # ── Sub-renderers ─────────────────────────────────────────────────────────

    def _draw_page_chrome(page: fitz.Page, page_num: int) -> None:
        """Background, navy header bar, navy footer bar."""
        s = page.new_shape()
        _draw_rect(s, 0, 0, W, H, fill=LGRAY)
        _draw_rect(s, 0, 0, W, HEADER_H, fill=NAVY)
        _draw_rect(s, 0, H - FOOTER_H, W, H, fill=NAVY)
        s.commit()

        _text(page, 40, 38, "Clause Review Summary",
              size=22, color=(1.0, 1.0, 1.0), bold=True)

        subtitle = f"Total flagged clauses: {total}"
        if total_pages > 1:
            subtitle += f"   \u2022   Page {page_num} of {total_pages}"
        _text(page, 40, 62, subtitle, size=12, color=(0.75, 0.78, 0.88))

        _text(page, 40, H - 16, "Generated by Team 27",
              size=9, color=(0.60, 0.65, 0.75))
        _text(page, W - 175, H - 16, f"{total} clause(s) flagged",
              size=9, color=(0.60, 0.65, 0.75))

    def _draw_cards(page: fitz.Page) -> None:
        total_cards_w = len(FLAG_HEX_MAP) * CARD_W + (len(FLAG_HEX_MAP) - 1) * CARD_GAP
        sx = (W - total_cards_w) / 2

        for i, (flag, hx) in enumerate(FLAG_HEX_MAP.items()):
            x   = sx + i * (CARD_W + CARD_GAP)
            rgb = _hex_to_rgb(hx)
            s = page.new_shape()
            # Drop shadow
            _draw_rect(s, x+3, CARDS_Y+3, x+CARD_W+3, CARDS_Y+CARD_H+3,
                       fill=(0.82, 0.83, 0.85))
            # Card body
            _draw_rect(s, x, CARDS_Y, x+CARD_W, CARDS_Y+CARD_H,
                       fill=(1.0, 1.0, 1.0), color=(0.88, 0.89, 0.91))
            # Colour accent strip
            _draw_rect(s, x, CARDS_Y, x+CARD_W, CARDS_Y+7, fill=rgb)
            s.commit()

            count   = counts.get(flag, 0)
            num_str = str(count)
            lbl     = short_labels[flag]
            num_x   = x + CARD_W / 2 - len(num_str) * 9
            lbl_x   = x + CARD_W / 2 - len(lbl) * 3.3
            _text(page, num_x, CARDS_Y + 54, num_str, size=34, color=rgb, bold=True)
            _text(page, lbl_x, CARDS_Y + 74, lbl,     size=11, color=(0.45, 0.45, 0.50))

    def _draw_table_header(page: fitz.Page, ty: float) -> None:
        s = page.new_shape()
        _draw_rect(s, 30, ty - 8, W - 30, ty + 16, fill=NAVY)
        s.commit()
        for hx, htxt in zip(TABLE_COL_X, HEADERS):
            _text(page, hx, ty + 6, htxt, size=10, color=(1.0, 1.0, 1.0), bold=True)

    def _draw_rows(page: fitz.Page, rows: list[dict], start_ry: float) -> None:
        for idx, a in enumerate(rows):
            ry  = start_ry + idx * ROW_H
            bg  = (1.0, 1.0, 1.0) if idx % 2 == 0 else (0.94, 0.95, 0.98)
            s   = page.new_shape()
            _draw_rect(s, 30, ry - 6, W - 30, ry + ROW_H - 6, fill=bg, color=bg)
            s.commit()

            dot_rgb = _hex_to_rgb(a["hex"])
            s = page.new_shape()
            _draw_circle(s, TABLE_COL_X[0] - 12, ry + 3, 4, dot_rgb)
            s.commit()

            flag_label = a["flag_color"].replace(" Flag", "")
            row_vals = [
                str(a["clause_id"])[:16],
                flag_label,
                str(a.get("severity",    ""))[:14],
                str(a.get("confidence",  ""))[:10],
                str(a.get("page",        "")),
            ]
            for cx, val in zip(TABLE_COL_X, row_vals):
                _text(page, cx, ry + 7, val, size=9, color=(0.20, 0.20, 0.25))

    # ── Render each page chunk ────────────────────────────────────────────────
    for page_num, chunk_rows in enumerate(chunks, start=1):
        doc.insert_page(-1, width=W, height=H)   # append at end
        page = doc[-1]

        _draw_page_chrome(page, page_num)

        if page_num == 1:
            _draw_cards(page)
            _draw_table_header(page, TABLE_Y_P1)
            _draw_rows(page, chunk_rows, FIRST_ROW_P1)
        else:
            _draw_table_header(page, TABLE_Y_CONT)
            _draw_rows(page, chunk_rows, FIRST_ROW_CONT)


# ── OCR helpers ───────────────────────────────────────────────────────────────

def _is_image_page(page: fitz.Page) -> bool:
    key = id(page)
    if key not in _image_page_cache:
        _image_page_cache[key] = len(page.get_text("text").strip()) < 20
    return _image_page_cache[key]


def _clean_ocr_token(word: str) -> str:
    return re.sub(r'[^\w]', '', word)


def _get_ocr_tokens(page: fitz.Page) -> list:
    key = id(page)
    if key in _ocr_token_cache:
        return _ocr_token_cache[key]
    DPI  = 150
    zoom = DPI / 72.0
    mat  = fitz.Matrix(zoom, zoom)
    pix  = page.get_pixmap(matrix=mat, alpha=False)
    img  = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    tokens = []
    for i in range(len(data["text"])):
        raw = data["text"][i].strip()
        if not raw:
            continue
        cleaned = _clean_ocr_token(raw)
        if cleaned:
            tokens.append((
                cleaned,
                data["left"][i], data["top"][i],
                data["width"][i], data["height"][i],
                zoom,
            ))
    _ocr_token_cache[key] = tokens
    return tokens


def _ocr_search(page: fitz.Page, term: str) -> list[fitz.Rect]:
    tokens     = _get_ocr_tokens(page)
    term_words = [_clean_ocr_token(w) for w in term.split()]
    term_words = [w for w in term_words if w]
    tw_count   = len(term_words)
    if not tw_count:
        return []
    rects = []
    for start_idx in range(len(tokens) - tw_count + 1):
        window = tokens[start_idx: start_idx + tw_count]
        if all(t[0].lower() == tw.lower() for t, tw in zip(window, term_words)):
            zoom  = window[0][5]
            xs    = [t[1]        for t in window]
            ys    = [t[2]        for t in window]
            x2s   = [t[1] + t[3] for t in window]
            y2s   = [t[2] + t[4] for t in window]
            rects.append(fitz.Rect(
                min(xs)/zoom, min(ys)/zoom,
                max(x2s)/zoom, max(y2s)/zoom,
            ))
    return rects


def _search_page(page: fitz.Page, term: str) -> list[fitz.Rect]:
    if not _is_image_page(page):
        return page.search_for(term, flags=fitz.TEXT_DEHYPHENATE)
    return _ocr_search(page, term)


def _add_highlight(page: fitz.Page, rect: fitz.Rect,
                   rgb: tuple, clause_id: str, popup_content: str) -> None:
    annot = page.add_highlight_annot(rect)
    annot.set_colors(stroke=rgb)
    annot.set_opacity(HIGHLIGHT_OPACITY)
    annot.set_info(title=f"Clause {clause_id}", content=popup_content)
    annot.update()


# ── Core processing ───────────────────────────────────────────────────────────

def process_pdf(pdf_bytes: bytes, template_path: str) -> tuple[bytes, list[dict]]:
    global CLAUSE_RULES

    _ocr_token_cache.clear()
    _image_page_cache.clear()

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    annotations: list[dict] = []

    # Step 1 – Load clauses extracted from the uploaded PDF
    with open("clauses.json", "r", encoding="utf-8") as f:
        clauses = json.load(f)

    # Step 2 – Load template content for comparison
    template_content = get_template_content(template_path)

    # Step 3 – Process every clause, collect results, and write clauses_with_risk.json
    results: list[dict] = []
    for clause in clauses:
        rule = process_clause(clause, template_path, template_content)
        results.append(rule)

    with open("clauses_with_risk.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Keep the in-memory cache in sync so /clauses endpoint reflects new data
    CLAUSE_RULES = results

    # Step 4 – Annotate the PDF using the freshly generated results
    for rule in results:
        clause_id      = str(rule.get("clause_id",      "")).strip()
        flag_color     = normalize_flag(rule.get("flag_color", "Amber Flag"))
        severity       = rule.get("severity",            "")
        reason         = rule.get("reason",              "")
        recommendation = rule.get("recommendation",      "")
        confidence     = rule.get("confidence",          0.0)
        target_page    = rule.get("page",                0)

        if not clause_id:
            continue

        rgb       = FLAG_COLOR_MAP.get(flag_color, FLAG_COLOR_MAP["Amber Flag"])
        hex_color = FLAG_HEX_MAP.get(flag_color, "#f2b210")

        search_terms    = [f"Clause {clause_id}", clause_id]
        pages_to_search = (
            [doc[target_page - 1]]
            if 0 < target_page <= len(doc)
            else list(doc)
        )
        popup_content = (
            f"Severity: {severity}\n"
            f"Reason:\n{reason}\n\n"
            f"Recommendation:\n{recommendation}"
        )

        for page in pages_to_search:
            matched = False
            for term in search_terms:
                hits = _search_page(page, term)
                for r in hits:
                    _add_highlight(page, r, rgb, clause_id, popup_content)
                    annotations.append({
                        "clause_id":      clause_id,
                        "flag_color":     flag_color,
                        "hex":            hex_color,
                        "severity":       severity,
                        "confidence":     _fmt_confidence(confidence),
                        "reason":         reason,
                        "recommendation": recommendation,
                        "page":           page.number + 1,
                        "rect":           [r.x0, r.y0, r.x1, r.y1],
                    })
                    matched = True

            if not matched:
                hits = (
                    page.search_for(clause_id, flags=fitz.TEXT_DEHYPHENATE)
                    if not _is_image_page(page)
                    else _ocr_search(page, clause_id)
                )
                for r in hits:
                    _add_highlight(page, r, rgb, clause_id, popup_content)
                    annotations.append({
                        "clause_id":      clause_id,
                        "flag_color":     flag_color,
                        "hex":            hex_color,
                        "severity":       severity,
                        "confidence":     _fmt_confidence(confidence),
                        "reason":         reason,
                        "recommendation": recommendation,
                        "page":           page.number + 1,
                        "rect":           [r.x0, r.y0, r.x1, r.y1],
                    })

    # Step 5 – Append summary page(s) at the end of the annotated PDF
    if annotations:
        build_summary_pages(doc, annotations)

    buf = io.BytesIO()
    doc.save(buf, garbage=4, deflate=True)
    doc.close()
    return buf.getvalue(), annotations


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/process-pdf")
async def process_pdf_endpoint(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported.")
    filename=file.filename
    # Save upload to disk so generate_json can read it
    with open(filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # generate_json reads document.pdf, writes clauses.json, returns template path
    template_path = generate_json(filename)

    # Re-read bytes for in-memory PDF processing
    with open(filename, "rb") as f:
        raw = f.read()

    if len(raw) > 100 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 100 MB).")

    try:
        result, _ = process_pdf(raw, template_path)
    except Exception as e:
        raise HTTPException(500, f"PDF processing failed: {e}")

    safe_name = file.filename.replace(".pdf", "_highlighted.pdf")
    return StreamingResponse(
        io.BytesIO(result),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


@app.post("/view", response_class=HTMLResponse)
async def view_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported.")

    filename = file.filename
    with open(filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    template_path = generate_json(filename)

    with open(filename, "rb") as f:
        raw = f.read()

    if len(raw) > 100 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 100 MB).")

    try:
        pdf_bytes, annotations = process_pdf(raw, template_path)
    except Exception as e:
        raise HTTPException(500, f"PDF processing failed: {e}")

    pdf_b64          = base64.b64encode(pdf_bytes).decode()
    annotations_json = json.dumps(annotations)

    # Deduplicate for sidebar counts
    seen: set = set()
    unique_annots = []
    for a in annotations:
        if a["clause_id"] not in seen:
            seen.add(a["clause_id"])
            unique_annots.append(a)

    counts = Counter(a["flag_color"] for a in unique_annots)
    summary_chips = "".join(
        f'<span class="summary-chip" style="background:{hx}">'
        f'{flag.replace(" Flag","")}: {counts.get(flag, 0)}</span>'
        for flag, hx in FLAG_HEX_MAP.items()
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>PDF Clause Reviewer</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         background: #f0f2f5; display: flex; height: 100vh; overflow: hidden; }}

  #pdf-panel {{ flex: 1; display: flex; flex-direction: column; overflow: hidden; }}
  #pdf-frame {{ flex: 1; border: none; width: 100%; height: 100%; }}

  #side-panel {{
    width: 360px; min-width: 360px; background: #ffffff;
    border-left: 1px solid #dde1e7; display: flex; flex-direction: column;
    overflow: hidden; box-shadow: -2px 0 8px rgba(0,0,0,0.08);
  }}
  #panel-header {{ padding: 18px 20px 14px; border-bottom: 1px solid #dde1e7; }}
  #panel-header h2 {{ font-size: 15px; font-weight: 600; color: #1a1a2e; margin-bottom: 6px; }}
  .summary-chips {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }}
  .summary-chip {{
    font-size: 11px; font-weight: 600; padding: 3px 10px;
    border-radius: 20px; color: #fff;
  }}

  #clause-list {{ flex: 1; overflow-y: auto; padding: 12px; scroll-behavior: smooth; }}
  #clause-list::-webkit-scrollbar {{ width: 6px; }}
  #clause-list::-webkit-scrollbar-track {{ background: #f0f2f5; }}
  #clause-list::-webkit-scrollbar-thumb {{ background: #c0c4ce; border-radius: 3px; }}

  .clause-card {{
    background: #fff; border: 1px solid #e8eaed; border-left: 4px solid #ccc;
    border-radius: 8px; padding: 12px 14px; margin-bottom: 10px; cursor: pointer;
    transition: box-shadow 0.15s, transform 0.1s;
  }}
  .clause-card:hover {{ box-shadow: 0 2px 10px rgba(0,0,0,0.10); transform: translateY(-1px); }}
  .clause-card.active {{ box-shadow: 0 0 0 2px #4a7cdc; }}
  .card-header {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }}
  .clause-id {{ font-size: 13px; font-weight: 700; color: #1a1a2e; }}
  .flag-badge {{ font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 20px; color: #fff; }}
  .severity-row {{ display: flex; gap: 12px; }}
  .meta-chip {{ font-size: 11px; color: #5a6075; background: #f0f2f5; padding: 2px 8px; border-radius: 4px; }}

  #detail-popup {{
    display: none; position: fixed; top: 50%; left: 50%;
    transform: translate(-50%,-50%); width: 480px; max-width: 90vw; max-height: 80vh;
    background: #fff; border-radius: 12px; box-shadow: 0 8px 40px rgba(0,0,0,0.20);
    z-index: 1000; flex-direction: column; overflow: hidden;
  }}
  #detail-popup.open {{ display: flex; }}
  #popup-header {{
    padding: 16px 20px; border-bottom: 1px solid #eee;
    display: flex; align-items: center; justify-content: space-between; flex-shrink: 0;
  }}
  #popup-header h3 {{ font-size: 15px; font-weight: 700; color: #1a1a2e; }}
  #popup-close {{ background: none; border: none; font-size: 20px; cursor: pointer; color: #8a8fa8; padding: 2px 6px; border-radius: 4px; }}
  #popup-close:hover {{ background: #f0f2f5; color: #1a1a2e; }}
  #popup-body {{ overflow-y: auto; padding: 18px 20px; flex: 1; }}
  #popup-body::-webkit-scrollbar {{ width: 6px; }}
  #popup-body::-webkit-scrollbar-thumb {{ background: #c0c4ce; border-radius: 3px; }}
  .popup-row {{ margin-bottom: 14px; }}
  .popup-label {{ font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #8a8fa8; margin-bottom: 4px; }}
  .popup-value {{ font-size: 13px; color: #2c2c3e; line-height: 1.55; white-space: pre-wrap; word-break: break-word; }}
  .popup-divider {{ border: none; border-top: 1px solid #eee; margin: 14px 0; }}

  #overlay {{ display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.35); z-index: 999; }}
  #overlay.open {{ display: block; }}
</style>
</head>
<body>
<div id="pdf-panel">
  <iframe id="pdf-frame"
    src="data:application/pdf;base64,{pdf_b64}#toolbar=1&navpanes=0"
    type="application/pdf"></iframe>
</div>

<div id="side-panel">
  <div id="panel-header">
    <h2>Clause Review</h2>
    <div class="summary-chips">{summary_chips}</div>
    <p style="font-size:12px;color:#8a8fa8;margin-top:8px">Click a clause to see details</p>
  </div>
  <div id="clause-list"></div>
</div>

<div id="overlay"></div>
<div id="detail-popup">
  <div id="popup-header">
    <h3 id="popup-title">Clause Details</h3>
    <button id="popup-close" onclick="closePopup()">&#x2715;</button>
  </div>
  <div id="popup-body">
    <div class="popup-row"><div class="popup-label">Flag</div><div class="popup-value" id="pop-flag"></div></div>
    <hr class="popup-divider"/>
    <div class="popup-row"><div class="popup-label">Severity</div><div class="popup-value" id="pop-severity"></div></div>
    <div class="popup-row"><div class="popup-label">Confidence</div><div class="popup-value" id="pop-confidence"></div></div>
    <hr class="popup-divider"/>
    <div class="popup-row"><div class="popup-label">Reason</div><div class="popup-value" id="pop-reason"></div></div>
    <hr class="popup-divider"/>
    <div class="popup-row"><div class="popup-label">Recommendation</div><div class="popup-value" id="pop-recommendation"></div></div>
  </div>
</div>

<script>
const annotations = {annotations_json};
const seen = new Set();
const unique = annotations.filter(a => {{
  if (seen.has(a.clause_id)) return false;
  seen.add(a.clause_id); return true;
}});
const list = document.getElementById('clause-list');
unique.forEach(a => {{
  const card = document.createElement('div');
  card.className = 'clause-card';
  card.style.borderLeftColor = a.hex;
  card.innerHTML = `
    <div class="card-header">
      <span class="clause-id">Clause ${{a.clause_id}}</span>
      <span class="flag-badge" style="background:${{a.hex}}">${{a.flag_color}}</span>
    </div>
    <div class="severity-row">
      <span class="meta-chip">Severity: ${{a.severity}}</span>
      <span class="meta-chip">Confidence: ${{a.confidence}}</span>
      <span class="meta-chip">Page ${{a.page}}</span>
    </div>`;
  card.addEventListener('click', () => openPopup(a, card));
  list.appendChild(card);
}});

function openPopup(a, card) {{
  document.querySelectorAll('.clause-card').forEach(c => c.classList.remove('active'));
  card.classList.add('active');
  document.getElementById('popup-title').textContent = 'Clause ' + a.clause_id;
  document.getElementById('pop-flag').textContent     = a.flag_color;
  document.getElementById('pop-flag').style.color     = a.hex;
  document.getElementById('pop-severity').textContent   = a.severity;
  document.getElementById('pop-confidence').textContent = a.confidence;
  document.getElementById('pop-reason').textContent     = a.reason;
  document.getElementById('pop-recommendation').textContent = a.recommendation;
  document.getElementById('detail-popup').classList.add('open');
  document.getElementById('overlay').classList.add('open');
  document.getElementById('popup-body').scrollTop = 0;
}}
function closePopup() {{
  document.getElementById('detail-popup').classList.remove('open');
  document.getElementById('overlay').classList.remove('open');
}}
document.getElementById('overlay').addEventListener('click', closePopup);
</script>
</body>
</html>"""
    return HTMLResponse(content=html)


@app.get("/legend")
def get_legend():
    seen: set[str] = set()
    legend = []
    for rule in CLAUSE_RULES:
        flag = rule.get("flag_color", "")
        if flag and flag not in seen:
            seen.add(flag)
            legend.append({
                "flag_color": flag,
                "hex":        FLAG_HEX_MAP.get(flag, "#888888"),
                "severity":   rule.get("severity", ""),
            })
    return legend


@app.get("/clauses")
def get_clauses():
    return CLAUSE_RULES