"""
template_matcher.py

Connects to Azure Blob Storage using DefaultAzureCredential (no keys needed).
Downloads UoA contract templates, embeds them, and returns the top 3 best
matches for a given uploaded contract PDF.

Usage:
    from template_matcher import match_templates
    results = match_templates("path/to/uploaded_contract.pdf")
    for r in results:
        print(r["template_name"], r["confidence"])
"""

import os
import json
import io
import re
import pdfplumber
import numpy as np
from docx import Document
from sklearn.metrics.pairwise import cosine_similarity
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential

from backend.embeddings import generate_embedding

# ── Azure Blob config ──────────────────────────────────────────────────────────
STORAGE_ACCOUNT_NAME = "stuoahackathonad91e50e6d"
CONTAINER_NAME       = "shared-hackathon-data"
BLOB_FOLDER          = "Contract Reviewer Agent"   # folder prefix inside container
ACCOUNT_URL          = f"https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net"

# Local cache so we don't re-embed templates on every run
CACHE_FILE = "template_embeddings_cache.json"
EXCLUDED_BLOB_FOLDERS = {"example", "examples", "redacted examples"}


def is_excluded_blob(blob_name: str) -> bool:
    """Return True when a blob path is in a folder that should not be indexed."""
    path_parts = [part.strip().lower() for part in blob_name.split("/") if part.strip()]
    return any(part in EXCLUDED_BLOB_FOLDERS for part in path_parts)


# ── Text extraction helpers ───────────────────────────────────────────────────

def extract_text_from_pdf_bytes(data: bytes) -> str:
    """Extract plain text from raw PDF bytes using pdfplumber."""
    text = ""
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
    return text.strip()


def extract_text_from_docx_bytes(data: bytes) -> str:
    """Extract plain text from raw DOCX bytes using python-docx."""
    doc = Document(io.BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_text(blob_name: str, data: bytes) -> str:
    """Dispatch to the correct extractor based on file extension."""
    lower = blob_name.lower()
    if lower.endswith(".pdf"):
        return extract_text_from_pdf_bytes(data)
    elif lower.endswith(".docx"):
        return extract_text_from_docx_bytes(data)
    elif lower.endswith(".json"):
        text=""
        for i in data:
            text+=i["text"]
        return text
    else:
        # Fallback: try UTF-8 decode (e.g. .txt)
        try:
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return ""


# ── Blob Storage helpers ──────────────────────────────────────────────────────

def get_blob_client() -> BlobServiceClient:
    from azure.identity import InteractiveBrowserCredential
    credential = InteractiveBrowserCredential(
        tenant_id="auckland.ac.nz"
    )
    return BlobServiceClient(account_url=ACCOUNT_URL, credential=credential)

def list_template_blobs(client: BlobServiceClient) -> list[str]:

    container = client.get_container_client(CONTAINER_NAME)
    blobs = container.list_blobs(name_starts_with=BLOB_FOLDER + "/")
    names = []
    for blob in blobs:
        name = blob.name
        # Skip the folder entry itself and anything that isn't a doc/pdf
        if name.endswith("/"):
            continue
        if is_excluded_blob(name):
            continue
        if not (name.lower().endswith(".pdf") or name.lower().endswith(".docx")):
            continue
        names.append(name)
    return names


def download_blob(client: BlobServiceClient, blob_name: str) -> bytes:
    """Download a single blob and return its raw bytes."""
    blob = client.get_blob_client(container=CONTAINER_NAME, blob=blob_name)
    stream = blob.download_blob()
    return stream.readall()

def get_template_content(template_path, force_refresh: bool = False) -> str:
    """Return extracted text for a single template stored in blob storage.

    The template_path may be either the full blob name returned by
    match_templates() or the friendly filename of the template.
    """
    client = get_blob_client()
    blob_names = list_template_blobs(client)

    if not blob_names:
        raise RuntimeError(
            f"No .pdf or .docx files found in "
            f"'{CONTAINER_NAME}/{BLOB_FOLDER}'. "
            "Check the folder name and your Azure permissions."
        )

    blob_name = template_path
    if blob_name not in blob_names:
        candidate = template_path
        if not candidate.startswith(f"{BLOB_FOLDER}/"):
            candidate = f"{BLOB_FOLDER}/{template_path}"
        if candidate in blob_names:
            blob_name = candidate
        else:
            raise ValueError(
                f"Template '{template_path}' was not found in blob storage folder '{BLOB_FOLDER}'."
            )

    cache = {} if force_refresh else load_cache()
    if not force_refresh and blob_name in cache and isinstance(cache[blob_name], dict):
        text = cache[blob_name].get("text")
        if text:
            return text

    data = download_blob(client, blob_name)
    content = extract_text(blob_name, data)
    if not content:
        raise ValueError(f"Could not extract any text from blob '{blob_name}'.")

    if blob_name not in cache or cache.get(blob_name, {}).get("text") != content:
        cache.setdefault(blob_name, {})["text"] = content
        save_cache(cache)

    return content


# ── Embedding cache ───────────────────────────────────────────────────────────

def load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache: dict) -> None:
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)


# ── Core: build template index ────────────────────────────────────────────────

def build_template_index(force_refresh: bool = False) -> list[dict]:
    """
    Download all templates from blob storage, extract their text, embed them,
    and return a list of dicts:
        { "blob_name": str, "template_name": str, "embedding": list[float] }

    Results are cached in CACHE_FILE so subsequent calls are fast.
    Set force_refresh=True to re-download and re-embed everything.
    """
    cache = {} if force_refresh else load_cache()
    client = get_blob_client()
    blob_names = list_template_blobs(client)

    if not blob_names:
        raise RuntimeError(
            f"No .pdf or .docx files found in "
            f"'{CONTAINER_NAME}/{BLOB_FOLDER}'. "
            "Check the folder name and your Azure permissions."
        )

    index = []
    cache_updated = False

    for blob_name in blob_names:
        # Friendly display name — strip the folder prefix
        template_name = blob_name.replace(BLOB_FOLDER + "/", "")

        if blob_name in cache:
            # Use cached embedding
            index.append({
                "blob_name":     blob_name,
                "template_name": template_name,
                "embedding":     cache[blob_name]["embedding"],
            })
            print(f"  [cache] {template_name}")
        else:
            print(f"  [download] {template_name} ...", end=" ", flush=True)
            try:
                data = download_blob(client, blob_name)
                text = extract_text(blob_name, data)
                if not text:
                    print("(no text extracted, skipping)")
                    continue
                embedding = generate_embedding(text).tolist()
                cache[blob_name] = {"embedding": embedding}
                cache_updated = True
                index.append({
                    "blob_name":     blob_name,
                    "template_name": template_name,
                    "embedding":     embedding,
                })
                print("done")
            except Exception as e:
                print(f"ERROR: {e}")

    if cache_updated:
        save_cache(cache)
        print(f"Cache saved to {CACHE_FILE}")

    return index


# ── Core: match contract against templates ────────────────────────────────────

def match_templates(
    contract_path: str,
    top_k: int = 3,
    force_refresh: bool = False,
) -> list[dict]:
    """
    Given a path to an uploaded contract (PDF or DOCX), return the top_k
    best-matching UoA templates with confidence scores.

    Args:
        contract_path:  Path to the uploaded contract file.
        top_k:          Number of top matches to return (default 3).
        force_refresh:  Re-download and re-embed all templates (default False).

    Returns:
        List of dicts, sorted by confidence descending:
        [
            {
                "rank": 1,
                "template_name": "UoA-Data Transfer Agreement Template (incoming).docx",
                "blob_name": "Contract Reviewer Agent/UoA-Data Transfer...",
                "confidence": 0.87,        # cosine similarity, 0–1
                "confidence_label": "High" # High / Medium / Low
            },
            ...
        ]
    """
    # 1. Extract text from the uploaded contract
    print(f"\nExtracting text from contract: {contract_path}")
    with open("clauses.json", "r") as f:
        data = json.load(f)
    contract_text = extract_text("clauses.json", data)

    if not contract_text:
        raise ValueError(f"Could not extract any text from '{contract_path}'. "
                         "Check the file is not scanned/image-only.")

    # 2. Embed the contract
    print("Embedding contract...")
    contract_embedding = np.array(generate_embedding(contract_text)).reshape(1, -1)

    # 3. Load (or build) the template index
    print("\nLoading template index...")
    template_index = build_template_index(force_refresh=force_refresh)

    # 4. Compute cosine similarity against every template
    results = []
    for tmpl in template_index:
        tmpl_embedding = np.array(tmpl["embedding"]).reshape(1, -1)
        score = float(cosine_similarity(contract_embedding, tmpl_embedding)[0][0])
        contract_name = contract_path.split("/")[-1].split("\\")[-1]
        contract_nameembedding = np.array(generate_embedding(contract_name)).reshape(1, -1)
        template_nameembedding = np.array(generate_embedding(tmpl["template_name"])).reshape(1, -1)
        name_score = float(cosine_similarity(contract_nameembedding, template_nameembedding)[0][0])
        final_score = score*0.4 + name_score*0.6
        results.append({
            "template_name": tmpl["template_name"],
            "blob_name":     tmpl["blob_name"],
            "confidence":    round(final_score, 4),
        })

    # 5. Sort and take top_k
    results.sort(key=lambda x: x["confidence"], reverse=True)
    top_results = results[:top_k]

    # 6. Add rank and human-readable label
    for i, r in enumerate(top_results):
        r["rank"] = i + 1
        score = r["confidence"]
        if score >= 0.75:
            r["confidence_label"] = "High"
        elif score >= 0.50:
            r["confidence_label"] = "Medium"
        else:
            r["confidence_label"] = "Low"

    return top_results


# ── CLI entry point ───────────────────────────────────────────────────────────

# if __name__ == "__main__":
#     import sys

#     if len(sys.argv) < 2:
#         print("Usage: python template_matcher.py <path_to_contract.pdf>")
#         sys.exit(1)

#     contract_file = sys.argv[1]
#     matches = match_templates(contract_file)

#     print("\n" + "=" * 60)
#     print("TOP TEMPLATE MATCHES")
#     print("=" * 60)
#     for m in matches:
#         print(f"\nRank #{m['rank']} — {m['confidence_label']} confidence ({m['confidence']:.2%})")
#         print(f"  Template: {m['template_name']}")
#         print(f"  Blob:     {m['blob_name']}")