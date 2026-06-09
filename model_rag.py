import os
from dotenv import load_dotenv
import pdfplumber
import faiss
import numpy as np
import requests
from openai import AzureOpenAI

# Load .env file
load_dotenv()

# ------------------- CONFIG -------------------
PDF_PATH = "documents.pdf"

AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
SERP_API_KEY = os.getenv("SERP_API_KEY")

# Azure model deployment names
CHAT_MODEL = "gpt-4o"
EMBED_MODEL = "text-embedding-3-small"

# ------------------- CLIENT -------------------
client = AzureOpenAI(
    api_version="2024-12-01-preview", #"2024-12-01-preview",  #2024-11-20
    azure_endpoint=AZURE_ENDPOINT,
    api_key=AZURE_API_KEY,
)

# ------------------- LOAD PDF -------------------
def load_pdf_text(path):
    text = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
    return text

# ------------------- CHUNKING -------------------
def chunk_text(text, chunk_size=500, overlap=100):
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap

    return chunks

# ------------------- EMBEDDING -------------------
def get_embedding(text):
    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=text
    )
    return response.data[0].embedding

# ------------------- BUILD VECTOR DB -------------------
def build_index(chunks):
    embeddings = [get_embedding(c) for c in chunks]
    dim = len(embeddings[0])

    index = faiss.IndexFlatL2(dim)
    index.add(np.array(embeddings).astype("float32"))

    return index

# ------------------- RETRIEVE -------------------
def retrieve(query, chunks, index, k=3):
    q_emb = np.array([get_embedding(query)]).astype("float32")
    distances, indices = index.search(q_emb, k)

    return [chunks[i] for i in indices[0]]

# ------------------- CHECK IF ANSWER EXISTS -------------------
def is_answer_in_context(question, context):
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": "Answer only YES or NO."},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
        ],
        max_tokens=5,
        temperature=0
    )
    return "yes" in response.choices[0].message.content.lower()

# ------------------- WEB SEARCH -------------------
def web_search(query):
    if not SERP_API_KEY:
        return "No web API key provided."

    url = "https://serpapi.com/search"
    params = {
        "q": query,
        "api_key": SERP_API_KEY,
        "engine": "google"
    }

    res = requests.get(url, params=params).json()

    results = []
    for r in res.get("organic_results", [])[:3]:
        results.append(f"{r['title']}\n{r['link']}\n{r['snippet']}")

    return "\n\n".join(results)

# ------------------- GENERATE ANSWER -------------------
def generate_answer(question, context, use_web=False):
    system_prompt = (
        "You are an assistant answering questions.\n"
        "If the answer is from CV context, write 'Source: CV'.\n"
        "If from web, write 'Source: External' and include references.\n"
        "Do not hallucinate."
    )

    if use_web:
        system_prompt += "\nUse external sources if needed."

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
        ],
        temperature=0,
        max_tokens=500
    )

    return response.choices[0].message.content

# ------------------- MAIN PIPELINE -------------------
def main():
    print("Loading PDF...")
    text = load_pdf_text(PDF_PATH)

    print("Chunking...")
    chunks = chunk_text(text)

    print("Building vector index...")
    index = build_index(chunks)

    while True:
        question = input("\nAsk a question (or 'exit'): ")
        if question.lower() == "exit":
            break

        # Retrieve relevant chunks
        retrieved_chunks = retrieve(question, chunks, index)
        context = "\n\n".join(retrieved_chunks)

        # Check if answer exists in CV
        found = is_answer_in_context(question, context)

        if found:
            print("\nAnswer from CV:\n")
            answer = generate_answer(question, context)
        else:
            print("\nNot found in CV. Searching web...\n")
            web_data = web_search(question)

            full_context = context + "\n\nExternal Sources:\n" + web_data
            answer = generate_answer(question, full_context, use_web=True)

        print(answer)


# ------------------- RUN -------------------
if __name__ == "__main__":
    main()