import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai


# --------------------------------------------------
# Paths
# --------------------------------------------------

# This file is:
# EvoMem/phase-1/retrieval/build_index.py

BASE_DIR = Path(__file__).resolve().parent

# Validated memories are:
# EvoMem/phase-1/validation/validated/
VALIDATED_DIR = BASE_DIR.parent / "validation" / "validated"

# Retrieval index will be:
# EvoMem/phase-1/retrieval/index.json
INDEX_PATH = BASE_DIR / "index.json"


# --------------------------------------------------
# Environment
# --------------------------------------------------

# .env is:
# EvoMem/.env
load_dotenv(BASE_DIR.parent.parent / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not found in .env")

client = genai.Client(api_key=GEMINI_API_KEY)

EMBEDDING_MODEL = "gemini-embedding-001"


# --------------------------------------------------
# Load validated memories
# --------------------------------------------------

def load_memories():
    memories = []

    for file_path in VALIDATED_DIR.glob("*.json"):
        with open(file_path, "r") as f:
            memory = json.load(f)

        memories.append(memory)

    return memories


# --------------------------------------------------
# Convert memory into text
# --------------------------------------------------

def memory_to_text(memory):
    task = memory.get("task", {})
    solution = memory.get("solution", {})
    experience = memory.get("experience", {})

    text = f"""
Task:
{task.get("description", "")}

Language:
{task.get("language", "")}

Domain:
{task.get("domain", "")}

Approach:
{solution.get("approach", "")}

Key ideas:
{" ".join(solution.get("key_ideas", []))}

Failures:
{" ".join(experience.get("failures", []))}

Recovery:
{" ".join(experience.get("recovery", []))}

Lessons:
{" ".join(experience.get("lessons", []))}
"""

    return text.strip()


# --------------------------------------------------
# Generate embedding
# --------------------------------------------------

def generate_embedding(text):
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text
    )

    return response.embeddings[0].values


# --------------------------------------------------
# Build retrieval index
# --------------------------------------------------

def build_index():
    memories = load_memories()

    if not memories:
        raise RuntimeError(
            f"No validated memories found in:\n{VALIDATED_DIR}"
        )

    index = []

    for i, memory in enumerate(memories, start=1):

        memory_id = memory.get("memory_id")

        print(
            f"Embedding memory {i}/{len(memories)}: "
            f"{memory_id}"
        )

        text = memory_to_text(memory)

        embedding = generate_embedding(text)

        index.append({
            "memory_id": memory_id,
            "text": text,
            "embedding": embedding
        })

    INDEX_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(INDEX_PATH, "w") as f:
        json.dump(index, f, indent=2)

    print()
    print("Retrieval index created successfully:")
    print(INDEX_PATH)
    print(f"Memories indexed: {len(index)}")


# --------------------------------------------------
# Main
# --------------------------------------------------

if __name__ == "__main__":
    build_index()