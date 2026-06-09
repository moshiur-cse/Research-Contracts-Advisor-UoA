from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
import os

from backend.embeddings import generate_embedding
import json
import re
endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

if not endpoint:
    raise ValueError("Missing endpoint")

if not key:
    raise ValueError("Missing API key")


client = DocumentIntelligenceClient(
    endpoint=endpoint,
    credential=AzureKeyCredential(key)
)
def extract_clauses_from_document(document_path):

    with open(document_path, "rb") as f:

        poller = client.begin_analyze_document(
            "prebuilt-layout",
            body=f
        )

    result = poller.result()

    print("Document processed successfully")

    result_dict = result.as_dict()

    with open("document_layout.json", "w", encoding="utf-8") as json_file:
        json.dump(result_dict, json_file, indent=4)

    # Load Azure Document Intelligence JSON
    with open("document_layout.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    paragraphs = data.get("paragraphs", [])

    # Regex for legal clause numbering
    CLAUSE_PATTERN = re.compile(
        r'^(\d+(\.\d+)*(\([a-z]\))?)\s+'
    )

    clauses = []

    current_clause = None
    text_variable = ""
    for para in paragraphs:

        text = para.get("content", "").strip()
        
        if not text:
            continue

        match = CLAUSE_PATTERN.match(text)
        if not match:
            if para.get("boundingRegions"):
                page = para["boundingRegions"][0].get("pageNumber")
            if current_clause:
                current_clause["text"] += "\n" + text
            else:
                current_clause = {
                "clause_id": 0,
                "text": text,
                "page": page,
                "bounding_regions": para.get("boundingRegions", [])
            }
        # New clause detected
        if match:

            # Save previous clause
            if current_clause:
                current_clause["embedding"] = generate_embedding(current_clause["text"]).tolist()
                clauses.append(current_clause)

            clause_id = match.group(1)

            page = None

            if para.get("boundingRegions"):
                page = para["boundingRegions"][0].get("pageNumber")
            
            current_clause = {
                "clause_id": clause_id,
                "text": text,
                "page": page,
                "bounding_regions": para.get("boundingRegions", [])
            }

        else:
            # Append text to existing clause
            if current_clause:
                current_clause["text"] += "\n" + text
        

    # Save last clause
    if current_clause:
        current_clause["embedding"] = generate_embedding(current_clause["text"]).tolist()
        clauses.append(current_clause)

    # Save output
    with open("clauses.json", "w", encoding="utf-8") as f:
        json.dump(clauses, f, indent=4)

    print(f"Extracted {len(clauses)} clauses")
