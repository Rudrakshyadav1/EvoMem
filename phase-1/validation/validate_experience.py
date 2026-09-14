import json
import re
import subprocess
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path


# ============================================================
# Paths
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

MEMORY_PATH = BASE_DIR / "experience" / "memory.json"
TRAJECTORY_PATH = BASE_DIR / "trajectory" / "trajectory.json"

VALIDATED_DIR = BASE_DIR / "validation" / "validated"
OUTPUT_PATH = VALIDATED_DIR / "memory.json"


# ============================================================
# Configuration
# ============================================================

EXECUTION_TIMEOUT = 10

SUPPORTED_LANGUAGES = {
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".py": "Python",
    ".java": "Java",
}


# ============================================================
# Basic utilities
# ============================================================

def load_json(path):
    if not path.exists():
        raise FileNotFoundError(f"File not found:\n{path}")

    with open(path, "r") as f:
        return json.load(f)


def normalize_text(value):
    if value is None:
        return ""

    if isinstance(value, (dict, list)):
        return json.dumps(value)

    return str(value)


def contains_any(text, terms):
    text = text.lower()

    return any(
        term.lower() in text
        for term in terms
    )


# ============================================================
# Extract evidence from trajectory
# ============================================================

def build_trajectory_evidence(trajectory):

    evidence = {
        "actions": [],
        "observations": [],
        "messages": [],
        "all_text": ""
    }

    text_parts = []

    for event in trajectory:

        kind = event.get("kind")

        if kind == "ActionEvent":

            action_data = {
                "id": event.get("id"),
                "tool_name": event.get("tool_name"),
                "action": event.get("action"),
                "summary": event.get("summary"),
                "thought": event.get("thought"),
                "reasoning_content": event.get(
                    "reasoning_content"
                )
            }

            evidence["actions"].append(action_data)

            for value in action_data.values():
                if value:
                    text_parts.append(
                        normalize_text(value)
                    )

        elif kind == "ObservationEvent":

            observation_data = {
                "id": event.get("id"),
                "tool_name": event.get("tool_name"),
                "observation": event.get("observation"),
            }

            evidence["observations"].append(
                observation_data
            )

            if observation_data["observation"]:
                text_parts.append(
                    normalize_text(
                        observation_data["observation"]
                    )
                )

        elif kind == "MessageEvent":

            content = (
                event
                .get("llm_message", {})
                .get("content", [])
            )

            for item in content:

                if item.get("type") == "text":

                    text = item.get("text", "")

                    evidence["messages"].append(text)

                    text_parts.append(text)

    evidence["all_text"] = "\n".join(text_parts)

    return evidence


# ============================================================
# Locate files mentioned by the memory
# ============================================================

def locate_memory_files(memory):

    referenced_files = (
        memory
        .get("solution", {})
        .get("files", [])
    )

    results = []

    for relative_path in referenced_files:

        path = BASE_DIR / relative_path

        results.append({
            "path": relative_path,
            "exists": path.exists(),
            "absolute_path": str(path) if path.exists() else None
        })

    return results


# ============================================================
# Language validation
# ============================================================

def validate_language(memory, file_results, trajectory_text):

    claimed_language = (
        memory
        .get("task", {})
        .get("language")
    )

    if not claimed_language:

        return {
            "status": "unverified",
            "claim": None,
            "evidence": []
        }

    evidence = []

    for file_info in file_results:

        if not file_info["exists"]:
            continue

        suffix = Path(
            file_info["path"]
        ).suffix.lower()

        detected_language = (
            SUPPORTED_LANGUAGES.get(suffix)
        )

        if detected_language:

            if detected_language.lower() == (
                claimed_language.lower()
            ):

                evidence.append(
                    f"{file_info['path']} has "
                    f"extension {suffix}"
                )

    # Also inspect trajectory.
    language_patterns = {
        "c++": [
            r"\.cpp\b",
            r"\bg\+\+\b",
            r"\bc\+\+\b"
        ],
        "python": [
            r"\.py\b",
            r"\bpython3?\b"
        ],
        "java": [
            r"\.java\b",
            r"\bjavac\b"
        ]
    }

    patterns = language_patterns.get(
        claimed_language.lower(),
        []
    )

    for pattern in patterns:

        if re.search(
            pattern,
            trajectory_text,
            re.IGNORECASE
        ):

            evidence.append(
                f"Trajectory matches pattern: {pattern}"
            )

    if evidence:

        return {
            "status": "verified",
            "claim": claimed_language,
            "evidence": evidence
        }

    return {
        "status": "unverified",
        "claim": claimed_language,
        "evidence": []
    }


# ============================================================
# Claim validation
# ============================================================

def validate_text_claim(claim, trajectory_text):

    """
    Lightweight deterministic grounding check.

    We deliberately do NOT ask an LLM to judge the claim.
    Instead we look for meaningful overlap between the
    memory claim and the original trajectory.
    """

    claim_words = re.findall(
        r"\b[a-zA-Z][a-zA-Z0-9_+-]{3,}\b",
        claim.lower()
    )

    # Remove generic words.
    ignored = {
        "this",
        "that",
        "with",
        "from",
        "were",
        "have",
        "been",
        "agent",
        "used",
        "using",
        "solution",
        "problem",
        "task",
        "the",
        "into",
        "then",
        "they",
        "their",
        "which",
        "where",
        "after",
        "before",
    }

    keywords = [
        word
        for word in claim_words
        if word not in ignored
    ]

    trajectory_lower = trajectory_text.lower()

    matches = [
        word
        for word in keywords
        if word in trajectory_lower
    ]

    if not keywords:

        return {
            "status": "unverified",
            "supporting_terms": []
        }

    ratio = len(matches) / len(keywords)

    if ratio >= 0.5:

        status = "verified"

    elif ratio >= 0.25:

        status = "partially_verified"

    else:

        status = "unverified"

    return {
        "status": status,
        "supporting_terms": matches
    }


# ============================================================
# Validate experience claims
# ============================================================

def validate_experience_claims(memory, trajectory_text):

    experience = memory.get(
        "experience",
        {}
    )

    result = {}

    for category in [
        "failures",
        "recovery",
        "lessons"
    ]:

        claims = experience.get(
            category,
            []
        )

        result[category] = []

        for claim in claims:

            claim_result = validate_text_claim(
                claim,
                trajectory_text
            )

            claim_result["claim"] = claim

            result[category].append(
                claim_result
            )

    return result


# ============================================================
# Inspect solution files
# ============================================================

def inspect_files(file_results):

    results = []

    for file_info in file_results:

        if not file_info["exists"]:
            continue

        path = Path(
            file_info["absolute_path"]
        )

        try:

            content = path.read_text(
                encoding="utf-8",
                errors="replace"
            )

            results.append({
                "path": file_info["path"],
                "exists": True,
                "size_bytes": path.stat().st_size,
                "content_available": True,
                "contains_code": bool(
                    content.strip()
                )
            })

        except OSError as error:

            results.append({
                "path": file_info["path"],
                "exists": True,
                "content_available": False,
                "error": str(error)
            })

    return results


# ============================================================
# Execute supported solution
# ============================================================

def validate_execution(file_results):

    execution_results = []

    for file_info in file_results:

        if not file_info["exists"]:
            continue

        solution_path = Path(
            file_info["absolute_path"]
        )

        suffix = solution_path.suffix.lower()

        # ----------------------------------------------------
        # C++
        # ----------------------------------------------------

        if suffix in {".cpp", ".cc", ".cxx"}:

            with tempfile.TemporaryDirectory() as temp_dir:

                executable = (
                    Path(temp_dir) / "solution"
                )

                compile_command = [
                    "g++",
                    "-std=c++17",
                    str(solution_path),
                    "-o",
                    str(executable)
                ]

                compile_result = subprocess.run(
                    compile_command,
                    capture_output=True,
                    text=True
                )

                compile_success = (
                    compile_result.returncode == 0
                )

                run_result = None

                if compile_success:

                    try:

                        run_result = subprocess.run(
                            [str(executable)],
                            capture_output=True,
                            text=True,
                            timeout=EXECUTION_TIMEOUT
                        )

                    except subprocess.TimeoutExpired:

                        run_result = None

                execution_results.append({
                    "file": file_info["path"],
                    "language": "C++",
                    "compile_success": compile_success,
                    "compile_return_code": (
                        compile_result.returncode
                    ),
                    "compile_stdout": (
                        compile_result.stdout
                    ),
                    "compile_stderr": (
                        compile_result.stderr
                    ),
                    "execution_success": (
                        run_result is not None
                        and run_result.returncode == 0
                    ),
                    "execution_return_code": (
                        run_result.returncode
                        if run_result
                        else None
                    ),
                    "execution_stdout": (
                        run_result.stdout
                        if run_result
                        else ""
                    ),
                    "execution_stderr": (
                        run_result.stderr
                        if run_result
                        else ""
                    )
                })

        # ----------------------------------------------------
        # Python
        # ----------------------------------------------------

        elif suffix == ".py":

            try:

                run_result = subprocess.run(
                    [
                        "python3",
                        str(solution_path)
                    ],
                    capture_output=True,
                    text=True,
                    timeout=EXECUTION_TIMEOUT
                )

                execution_results.append({
                    "file": file_info["path"],
                    "language": "Python",
                    "compile_success": True,
                    "execution_success": (
                        run_result.returncode == 0
                    ),
                    "execution_return_code": (
                        run_result.returncode
                    ),
                    "execution_stdout": (
                        run_result.stdout
                    ),
                    "execution_stderr": (
                        run_result.stderr
                    )
                })

            except subprocess.TimeoutExpired:

                execution_results.append({
                    "file": file_info["path"],
                    "language": "Python",
                    "compile_success": True,
                    "execution_success": False,
                    "execution_return_code": None,
                    "execution_stdout": "",
                    "execution_stderr": (
                        "Execution timed out."
                    )
                })

        # ----------------------------------------------------
        # Unsupported language
        # ----------------------------------------------------

        else:

            execution_results.append({
                "file": file_info["path"],
                "language": "unknown",
                "status": "unsupported"
            })

    return execution_results


# ============================================================
# Determine overall trust
# ============================================================

def determine_status(
    language_result,
    claim_results,
    execution_results
):

    language_verified = (
        language_result["status"] == "verified"
    )

    claims = []

    for category_results in claim_results.values():

        claims.extend(category_results)

    unverified_claims = [
        claim
        for claim in claims
        if claim["status"] == "unverified"
    ]

    execution_success = any(
        result.get("execution_success") is True
        for result in execution_results
    )

    # --------------------------------------------------------
    # Trusted memory
    # --------------------------------------------------------

    if (
        language_verified
        and not unverified_claims
        and execution_success
    ):

        return "validated"

    # --------------------------------------------------------
    # Some evidence exists, but memory isn't fully trusted
    # --------------------------------------------------------

    if (
        language_verified
        or execution_success
        or any(
            claim["status"] == "verified"
            for claim in claims
        )
    ):

        return "partially_validated"

    return "failed_validation"


# ============================================================
# Main validation pipeline
# ============================================================

def validate_memory(memory, trajectory):

    trajectory_evidence = (
        build_trajectory_evidence(
            trajectory
        )
    )

    trajectory_text = (
        trajectory_evidence["all_text"]
    )

    file_results = locate_memory_files(
        memory
    )

    language_result = validate_language(
        memory,
        file_results,
        trajectory_text
    )

    claim_results = validate_experience_claims(
        memory,
        trajectory_text
    )

    file_inspection = inspect_files(
        file_results
    )

    execution_results = validate_execution(
        file_results
    )

    status = determine_status(
        language_result,
        claim_results,
        execution_results
    )

    return {
        "status": status,

        "validated_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "language": language_result,

        "claims": claim_results,

        "files": file_inspection,

        "execution": execution_results,

        "evidence_summary": {
            "trajectory_events": len(
                trajectory
            ),
            "files_checked": len(
                file_results
            ),
            "execution_checks": len(
                execution_results
            )
        }
    }


# ============================================================
# Save trusted memory
# ============================================================

def save_validated_memory(
    memory,
    validation
):

    validated_memory = deepcopy(memory)

    validated_memory["validation"] = validation

    validated_memory["status"] = (
        validation["status"]
    )

    VALIDATED_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(OUTPUT_PATH, "w") as f:

        json.dump(
            validated_memory,
            f,
            indent=2
        )

    return OUTPUT_PATH


# ============================================================
# Main
# ============================================================

def main():

    print("Loading candidate memory...")
    memory = load_json(MEMORY_PATH)

    print("Loading trajectory...")
    trajectory = load_json(
        TRAJECTORY_PATH
    )

    print("Validating memory...")

    validation = validate_memory(
        memory,
        trajectory
    )

    output_path = save_validated_memory(
        memory,
        validation
    )

    print()
    print("=" * 50)
    print(
        f"Validation status: "
        f"{validation['status']}"
    )
    print("=" * 50)

    print()
    print(
        "Validated memory saved to:"
    )

    print(output_path)


if __name__ == "__main__":
    main()