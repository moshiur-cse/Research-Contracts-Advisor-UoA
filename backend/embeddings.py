from sentence_transformers import SentenceTransformer

# Load once globally
model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

def generate_embedding(text):

    embedding = model.encode(
        text,
        convert_to_numpy=True
    )

    return embedding
# from openai import AzureOpenAI
# import os

# client = AzureOpenAI(
#     api_key=os.getenv("AZURE_OPENAI_API_KEY"),
#     api_version="2024-02-15-preview",
#     azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
# )

# MODEL = "text-embedding-3-small-2"

# def generate_embedding(text):

#     response = client.embeddings.create(
#         model=MODEL,
#         input=text
#     )

#     return response.data[0].embedding
# import os
# import numpy as np
# from dotenv import load_dotenv
# from openai import AzureOpenAI


# client = AzureOpenAI(
#     api_key=AZURE_OPENAI_API_KEY,
#     api_version="2024-02-15-preview",
#     azure_endpoint=AZURE_OPENAI_ENDPOINT
# )

# # This must be your Azure deployment name.
# # Example: text-embedding-3-small
# MODEL = AZURE_OPENAI_EMBEDDING_DEPLOYMENT

# def generate_embedding(text):
#     response = client.embeddings.create(
#         model=MODEL,
#         input=text
#     )

#     embedding = response.data[0].embedding

#     # Keep numpy output so the rest of your code works like before
#     return np.array(embedding, dtype=np.float32)
