import json
import math
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai


# --------------------------------------------------
# Paths
# --------------------------------------------------

# This file:
# EvoMem/phase-1/retrieval/retrieve.py

BASE_DIR = Path(__file__).resolve().parent

INDEX_PATH = BASE_DIR / "index.json"


# --------------------------------------------------
# Environment
# --------------------------------------------------

# .env:
# EvoMem/.env
load_dotenv(BASE_DIR.parent.parent / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not found in .env")

client = genai.Client(api_key=GEMINI_API_KEY)

EMBEDDING_MODEL = "gemini-embedding-001"


# --------------------------------------------------
# Load index
# --------------------------------------------------

def load_index():
    if not INDEX_PATH.exists():
        raise FileNotFoundError(
            f"Retrieval index not found:\n{INDEX_PATH}\n\n"
            "Run build_index.py first."
        )

    with open(INDEX_PATH, "r") as f:
        return json.load(f)


# --------------------------------------------------
# Generate query embedding
# --------------------------------------------------

def generate_embedding(text):
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text
    )

    return response.embeddings[0].values


# --------------------------------------------------
# Cosine similarity
# --------------------------------------------------

def cosine_similarity(a, b):
    dot_product = sum(x * y for x, y in zip(a, b))

    magnitude_a = math.sqrt(
        sum(x * x for x in a)
    )

    magnitude_b = math.sqrt(
        sum(y * y for y in b)
    )

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)


# --------------------------------------------------
# Retrieve memories
# --------------------------------------------------

def retrieve(query, top_k=3):
    index = load_index()

    print("Generating query embedding...")

    query_embedding = generate_embedding(query)

    results = []

    for memory in index:

        similarity = cosine_similarity(
            query_embedding,
            memory["embedding"]
        )

        results.append({
            "memory_id": memory["memory_id"],
            "similarity": similarity,
            "text": memory["text"]
        })

    # Highest similarity first
    results.sort(
        key=lambda x: x["similarity"],
        reverse=True
    )

    return results[:top_k]


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():

    if len(sys.argv) < 2:
        print("Usage:")
        print('python3 retrieval/retrieve.py "your coding problem"')
        return

    query = " ".join(sys.argv[1:])

    print()
    print("Query:")
    print(query)
    print()

    results = retrieve(query)

    print("Retrieved memories:")
    print("=" * 60)

    if not results:
        print("No memories found.")
        return

    for i, result in enumerate(results, start=1):

        print(f"\nRank {i}")
        print(f"Memory ID: {result['memory_id']}")
        print(
            f"Similarity: "
            f"{result['similarity']:.4f}"
        )

        print("\nMemory:")
        print(result["text"])

        print("-" * 60)


if __name__ == "__main__":
    main()