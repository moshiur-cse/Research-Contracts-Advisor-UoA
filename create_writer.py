from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

import os

project = AIProjectClient(
    endpoint=os.environ["PROJECT_ENDPOINT"],
    credential=DefaultAzureCredential()
)

writer = project.agents.create_agent(
    model=os.environ["MODEL_DEPLOYMENT"],
    name="writer-agent",
    instructions="""
You are a legal review orchestration agent.

You:
- retrieve sibling clauses
- retrieve semantic neighbors
- retrieve referenced clauses
- retrieve template clauses
- invoke Researcher Agent
- structure final outputs

You NEVER perform legal reasoning yourself.
"""
)

print(writer.id)