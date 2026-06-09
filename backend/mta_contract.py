# Before running:
# pip install azure-ai-projects>=2.1.0 azure-identity

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
import base64
import mimetypes

# Azure AI Project endpoint
endpoint = "https://ai-team-27-hack.services.ai.azure.com/api/projects/team-27"

project_client = AIProjectClient(
    endpoint=endpoint,
    credential=DefaultAzureCredential(),
)

my_agent = "mtaContractagent"
my_version = "2"

openai_client = project_client.get_openai_client()

# PDF file path
pdf_path = "documents.pdf"

# Read and encode PDF
with open(pdf_path, "rb") as f:
    pdf_bytes = f.read()

pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

# Detect mime type
mime_type = mimetypes.guess_type(pdf_path)[0] or "application/pdf"

# Send PDF + question to agent
response = openai_client.responses.create(
    input=[
        {
            "role": "user",
            "content": [
                {
                    "type": "input_file",
                    "filename": "sample.pdf",
                    "file_data": f"data:{mime_type};base64,{pdf_base64}",
                },
                {
                    "type": "input_text",
                    "text": ""
                }
            ],
        }
    ],
    extra_body={
        "agent_reference": {
            "name": my_agent,
            "version": my_version,
            "type": "agent_reference",
        }
    },
)

print("Response output:")
print(response.output_text)