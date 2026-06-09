from backend.retriever import retrieve_related_clauses
from docx import Document
from backend.researcher import analyze_clause

def process_clause(clause,template_path,template_content=None):

    related = retrieve_related_clauses(
        clause
    )

    # template_path = r"D:\MAI\714\Hackathon proj\UoA-Data Access Agreement Agency Template (incoming) May 2024 (1).docx"

    if template_content is None:
        doc = Document(template_path)
        template = "\n".join(
            [para.text for para in doc.paragraphs if para.text.strip()]
        )
    else:
        template = template_content


    payload = {
        "main_clause": clause,
        "related_clauses": related,
        "template": template
    }

    research_result = analyze_clause(payload)
    print(research_result)

    final_output = {
        "clause_id": clause["clause_id"],
        "page": clause["page"],
        "flag_color": research_result["flag_color"],
        "severity": research_result["severity"],
        "reason": research_result["reason"],
        "recommendation": research_result["recommendation"],
        "confidence": research_result["confidence"],
        "text": clause["text"]
    }

    return final_output