import json
import os
from backend.scanner import extract_clauses_from_document
from backend.writer import process_clause
from backend.template_matcher import match_templates, get_template_content
document_path = r"D:\MAI\714\Hackathon proj\Data Transfer Agreement Example.pdf"
# extract_clauses_from_document(document_path)
# Step 1 - Match contract to top 3 templates

def generate_json(document_path):
    extract_clauses_from_document(document_path)
    template_matches = match_templates(document_path)
    template_paths = [m["blob_name"] for m in template_matches]
    template_path = template_paths[0] if template_paths else None

    print("\nTop matching templates:")
    for m in template_matches:
        print(f"  #{m['rank']} {m['template_name']} ({m['confidence_label']}, {m['confidence']:.2%})")
    return template_path

    # Step 2 - Load clauses
    with open("clauses.json", "r") as f:
        clauses = json.load(f)
    # template_path = r"D:\MAI\714\Hackathon proj\UoA-Data Access Agreement Agency Template (incoming) May 2024 (1).docx"
    template_content=get_template_content(template_path)
    # Step 3 - Process clauses
    results = []
    for clause in clauses:
        result = process_clause(clause, template_path,template_content)
        results.append(result)

        # Step 4 - Save output
        with open("clauses_with_risk.json", "w") as f:
            json.dump(results, f, indent=2)

    print("Done.")
    return "success:"+document_path

generate_json(document_path)
