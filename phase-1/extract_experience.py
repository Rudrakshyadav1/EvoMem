# import json
# import sys
# from pathlib import Path


# def load_trajectory(path):
#     with open(path, "r") as f:
#         return json.load(f)


# def extract_experience(trajectory):
#     actions = []
#     observations = []

#     # Extract agent actions
#     for event in trajectory:
#         if event.get("kind") == "ActionEvent":
#             actions.append({
#                 "id": event.get("id"),
#                 "timestamp": event.get("timestamp"),
#                 "tool_name": event.get("tool_name"),
#                 "tool_call_id": event.get("tool_call_id"),
#                 "summary": event.get("summary"),
#                 "action": event.get("action")
#             })

#     # Extract tool observations
#     for event in trajectory:
#         if event.get("kind") == "ObservationEvent":
#             observations.append({
#                 "id": event.get("id"),
#                 "timestamp": event.get("timestamp"),
#                 "action_id": event.get("action_id"),
#                 "tool_name": event.get("tool_name"),
#                 "observation": event.get("observation")
#             })

#     # Extract the original user problem
#     problem = None

#     for event in trajectory:
#         if event.get("kind") == "MessageEvent":

#             content = event.get("llm_message", {}).get("content", [])

#             for item in content:
#                 if item.get("type") == "text":
#                     problem = item.get("text")
#                     break

#             if problem:
#                 break

#     experience = {
#         "memory_id": None,

#         "problem": problem,

#         "actions": actions,

#         "observations": observations,

#         "files_touched": [],

#         "commands": [],

#         "errors": [],

#         "validation": {
#             "tests_run": [],
#             "tests_passed": False
#         },

#         "context": {
#             "repo": None,
#             "commit": None
#         },

#         "status": "candidate"
#     }

#     return experience


# def main():

#     if len(sys.argv) != 2:
#         print("Usage:")
#         print("python3 extract_experience.py trajectory/trajectory.json")
#         return

#     trajectory_path = Path(sys.argv[1])

#     if not trajectory_path.exists():
#         print(f"Error: trajectory file not found: {trajectory_path}")
#         return

#     trajectory = load_trajectory(trajectory_path)

#     experience = extract_experience(trajectory)

#     # Save inside the separate experience folder
#     output_path = Path("experience") / "experience.json"

#     output_path.parent.mkdir(parents=True, exist_ok=True)

#     with open(output_path, "w") as f:
#         json.dump(experience, f, indent=2)

#     print(f"Experience written to: {output_path}")


# if __name__ == "__main__":
#     main()
import json
import sys
from pathlib import Path


# Always use the folder containing this script as phase-1
BASE_DIR = Path(__file__).resolve().parent


def load_trajectory(path):
    with open(path, "r") as f:
        return json.load(f)


def extract_experience(trajectory):
    actions = []
    observations = []

    # Extract ActionEvents
    for event in trajectory:
        if event.get("kind") == "ActionEvent":
            actions.append({
                "id": event.get("id"),
                "timestamp": event.get("timestamp"),
                "tool_name": event.get("tool_name"),
                "tool_call_id": event.get("tool_call_id"),
                "summary": event.get("summary"),
                "action": event.get("action")
            })

    # Extract ObservationEvents
    for event in trajectory:
        if event.get("kind") == "ObservationEvent":
            observations.append({
                "id": event.get("id"),
                "timestamp": event.get("timestamp"),
                "action_id": event.get("action_id"),
                "tool_name": event.get("tool_name"),
                "observation": event.get("observation")
            })

    # Extract original user problem
    problem = None

    for event in trajectory:
        if event.get("kind") == "MessageEvent":

            content = event.get("llm_message", {}).get("content", [])

            for item in content:
                if item.get("type") == "text":
                    problem = item.get("text")
                    break

            if problem:
                break

    return {
        "memory_id": None,

        "problem": problem,

        "actions": actions,

        "observations": observations,

        "files_touched": [],

        "commands": [],

        "errors": [],

        "validation": {
            "tests_run": [],
            "tests_passed": False
        },

        "context": {
            "repo": None,
            "commit": None
        },

        "status": "candidate"
    }


def main():

    if len(sys.argv) != 2:
        print("Usage:")
        print("python3 extract_experience.py trajectory/trajectory.json")
        return

    trajectory_path = Path(sys.argv[1])

    # If a relative path is provided, interpret it relative to phase-1
    if not trajectory_path.is_absolute():
        trajectory_path = BASE_DIR / trajectory_path

    if not trajectory_path.exists():
        print(f"Error: trajectory file not found:")
        print(trajectory_path)
        return

    trajectory = load_trajectory(trajectory_path)

    experience = extract_experience(trajectory)

    
    output_path = BASE_DIR / "experience" / "experience.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(experience, f, indent=2)

    print(f"Experience written to:")
    print(output_path)


if __name__ == "__main__":
    main()