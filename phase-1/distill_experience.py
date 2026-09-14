import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

import time
from google.genai import errors
# --------------------------------------------------
# Paths
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

INPUT_PATH = BASE_DIR / "experience" / "experience.json"
OUTPUT_PATH = BASE_DIR / "experience" / "memory.json"


# --------------------------------------------------
# Load environment variables
# --------------------------------------------------

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY not found in .env"
    )

if not LLM_MODEL:
    raise RuntimeError(
        "LLM_MODEL not found in .env"
    )


# --------------------------------------------------
# Model name
# --------------------------------------------------

# Your .env contains:
#
# LLM_MODEL="gemini/gemini-3.6-flash"
#
# The Google GenAI SDK expects:
#
# gemini-3.6-flash

MODEL_NAME = LLM_MODEL.removeprefix("gemini/")


# --------------------------------------------------
# Gemini client
# --------------------------------------------------

client = genai.Client(
    api_key=GEMINI_API_KEY
)


# --------------------------------------------------
# Memory schema
# --------------------------------------------------

MEMORY_SCHEMA = {
    "type": "object",

    "properties": {

        # ------------------------------------------
        # Memory ID
        # ------------------------------------------

        "memory_id": {
            "type": "string"
        },

        # ------------------------------------------
        # Task information
        # ------------------------------------------

        "task": {
            "type": "object",

            "properties": {

                "description": {
                    "type": "string"
                },

                "language": {
                    "type": "string"
                },

                "domain": {
                    "type": "string"
                }
            },

            "required": [
                "description",
                "language",
                "domain"
            ]
        },

        # ------------------------------------------
        # Solution information
        # ------------------------------------------

        "solution": {
            "type": "object",

            "properties": {

                "approach": {
                    "type": "string"
                },

                "key_ideas": {
                    "type": "array",

                    "items": {
                        "type": "string"
                    }
                },

                "files": {
                    "type": "array",

                    "items": {
                        "type": "string"
                    }
                }
            },

            "required": [
                "approach",
                "key_ideas",
                "files"
            ]
        },

        # ------------------------------------------
        # Experience
        # ------------------------------------------

        "experience": {
            "type": "object",

            "properties": {

                "failures": {
                    "type": "array",

                    "items": {
                        "type": "string"
                    }
                },

                "recovery": {
                    "type": "array",

                    "items": {
                        "type": "string"
                    }
                },

                "lessons": {
                    "type": "array",

                    "items": {
                        "type": "string"
                    }
                }
            },

            "required": [
                "failures",
                "recovery",
                "lessons"
            ]
        },

        # ------------------------------------------
        # Memory status
        # ------------------------------------------

        "status": {
            "type": "string"
        }
    },

    "required": [
        "memory_id",
        "task",
        "solution",
        "experience",
        "status"
    ]
}


# --------------------------------------------------
# Load extracted experience
# --------------------------------------------------

def load_experience():

    if not INPUT_PATH.exists():

        raise FileNotFoundError(
            f"Experience file not found:\n{INPUT_PATH}"
        )

    with open(INPUT_PATH, "r") as f:

        return json.load(f)


# --------------------------------------------------
# Build distillation prompt
# --------------------------------------------------

def build_prompt(experience):

    return f"""
You are the experience-distillation component of EvoMem.

EvoMem is a memory system for coding agents.

Your job is to transform a raw coding-agent experience
into a concise, reusable memory that another coding agent
could use when solving a similar task.

Follow these rules carefully:

1. Extract only information supported by the trajectory.

2. Identify the programming language if it can be inferred.

3. Identify the general domain of the task.

4. Explain the approach that the agent ultimately used.

5. Identify meaningful failures, bugs, or mistakes.

6. Explain how those failures were recovered from.

7. Extract reusable lessons that could help an agent
   solve similar tasks in the future.

8. Do NOT invent information.

9. Do NOT claim that tests passed unless the trajectory
   provides evidence that they passed.

10. Do NOT simply reproduce the event-by-event trajectory.

11. Focus on reusable experience rather than narration.

12. The memory should be useful for retrieval later.

13. Preserve important technical details when they are
    relevant to solving a similar problem.

14. If there were no meaningful failures, return an empty
    list for "failures".

15. If there was no meaningful recovery process, return an
    empty list for "recovery".

The raw extracted experience is:

{json.dumps(experience, indent=2)}

Return ONLY the structured JSON matching the provided schema.
"""


# --------------------------------------------------
# Distill experience using Gemini
# --------------------------------------------------

import time
from google.genai import errors


def distill(experience):

    prompt = build_prompt(experience)

    max_retries = 5

    for attempt in range(max_retries):

        try:

            print(
                f"LLM attempt {attempt + 1}/{max_retries}..."
            )

            response = client.models.generate_content(

                model=MODEL_NAME,

                contents=prompt,

                config=types.GenerateContentConfig(

                    response_mime_type="application/json",

                    response_schema=MEMORY_SCHEMA
                )
            )

            if not response.text:

                raise RuntimeError(
                    "Gemini returned an empty response."
                )

            return json.loads(response.text)

        except errors.ServerError as e:

            # 503 = temporary server-side availability problem
            if attempt == max_retries - 1:
                raise RuntimeError(
                    "Gemini remained unavailable after "
                    f"{max_retries} attempts."
                ) from e

            wait_time = 2 ** attempt

            print(
                f"Gemini temporarily unavailable (503). "
                f"Retrying in {wait_time} seconds..."
            )

            time.sleep(wait_time)

        except errors.ClientError as e:

            # Client errors such as invalid API request,
            # invalid model, invalid schema, etc.
            raise RuntimeError(
                f"Gemini API client error:\n{e}"
            ) from e

# --------------------------------------------------
# Main
# --------------------------------------------------

def main():

    print("Loading experience...")

    experience = load_experience()

    print(f"Using model: {MODEL_NAME}")

    print("Sending experience to Gemini...")

    memory = distill(experience)

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(OUTPUT_PATH, "w") as f:

        json.dump(
            memory,
            f,
            indent=2
        )

    print()
    print("Memory created successfully:")
    print(OUTPUT_PATH)


# --------------------------------------------------
# Entry point
# --------------------------------------------------

if __name__ == "__main__":

    main()