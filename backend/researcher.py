import json
import os
from unittest import result
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.core.rest import HttpRequest
from backend.agent_27 import get_response
#print("ENDPOINT:", os.environ.get("PROJECT_ENDPOINT"))  
def analyze_clause(payload):
    payload["main_clause"].pop("embedding", None)
    for i in range(len(payload["related_clauses"])):
        payload["related_clauses"][i].pop("embedding", None)
    response=get_response(payload)
    raw_text = response.output[0].content[0].text
    # Strip markdown code blocks if agent wraps in ```json ... ```
    raw_text = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    result = json.loads(raw_text)
    return result
