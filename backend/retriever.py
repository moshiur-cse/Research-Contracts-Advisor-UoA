import json
import re
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity





def get_clause(clause_id):
    with open("clauses.json", "r") as f:
        CLAUSES = json.load(f)
    for c in CLAUSES:
        if c["clause_id"] == clause_id:
            return c

    return None



def retrieve_related_clauses(target_clause, threshold=0.8):
    with open("clauses.json", "r") as f:
        CLAUSES = json.load(f)

    target_embedding = np.array(target_clause.get("embedding"))

    related = []

    for clause in CLAUSES:

        if clause["clause_id"] == target_clause["clause_id"]:
            continue

        clause_embedding = np.array(clause["embedding"])
        similarity = cosine_similarity(
            [target_embedding],
            [clause_embedding]
        )[0][0]


        final_score = similarity 

        if final_score <= 1-threshold:
            related.append({
                "clause_id": clause["clause_id"],
                "text": clause["text"],
                "score": round(float(final_score), 3)
            })

    related = sorted(
        related,
        key=lambda x: x["score"],
        reverse=True
    )

    return related[:5]