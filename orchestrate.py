# /// script
# dependencies = [
#     "python-dotenv",
#     "openhands-sdk",
#     "openhands-tools",
# ]
# ///

import os
import sys
import json
from dotenv import load_dotenv
from openhands.sdk import LLM, Agent, Conversation, Tool

# --- FIXED IMPORTS: Importing directly from their exact submodules ---
from openhands.tools.file_editor import FileEditorTool
# The default OpenHands terminal system maps to ExecuteBashTool or BashToolExecutor
try:
    from openhands.tools.execute_bash import BashTool
except ImportError:
    # Fallback to general terminal tool if named differently in this environment build
    from openhands.tools.terminal import TerminalTool as BashTool

# Load environment variables from the local .env file
load_dotenv()

def main():
    # Enforce providing the target phase folder name (e.g., phase-1)
    if len(sys.argv) < 2:
        print("❌ Error: Please specify the phase folder. Example: uv run orchestrate.py phase-1")
        sys.exit(1)
        
    target_phase = sys.argv[1]
    phase_path = os.path.join(os.getcwd(), target_phase)
    
    if not os.path.exists(phase_path):
        print(f"❌ Error: The directory '{target_phase}' does not exist.")
        sys.exit(1)

    # Fetch configuration keys directly from your .env file
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")
    model_name = os.getenv("LLM_MODEL", "gemini/gemini-3.6-flash")

    if not api_key:
        print("❌ Error: No API key found in your .env file (checked GEMINI_API_KEY and LLM_API_KEY).")
        sys.exit(1)

    print(f"🤖 Configuring Agent with Model: {model_name}")

    # 1. Initialize LLM Interface using variables fetched from .env
    llm = LLM(
        model=model_name,
        api_key=api_key,
    )

    # 2. Setup Agent with system tools using standard Tool wrapper
    agent = Agent(
        llm=llm,
        tools=[Tool(name=BashTool.name), Tool(name=FileEditorTool.name)],
    )

    # 3. Mount the conversation workspace explicitly to that phase directory
    conversation = Conversation(agent=agent, workspace=phase_path)

    # 4. Dynamic, Language-Detecting Execution Prompt 
    prompt = (
        f"Look inside the 'problem' directory to find the task or code template. "
        f"Detect the programming language used in that file. "
        f"Analyze the problem, fix any syntax/logical bugs present in the template, "
        f"and write the complete working solution into the 'sol' directory using the EXACT SAME programming language. "
        f"Compile and run tests locally using the terminal (e.g., using g++ for C++ or python3 for Python) "
        f"to confirm everything works perfectly before stopping."
    )

    print(f"🚀 Initializing Agent Workspace on: {target_phase}...")
    conversation.send_message(prompt)
    conversation.run()

    # 5. Save the specific phase history trajectory inside a dedicated logs folder
    print("✅ Run complete. Compiling execution trajectory...")
    
    if hasattr(conversation, "state") and hasattr(conversation.state, "events"):
        history = conversation.state.events
    elif hasattr(conversation, "history"):
        history = conversation.history
    elif hasattr(conversation, "events"):
        history = conversation.events
    else:
        history = getattr(conversation, "_history", [])

    # Turn the raw events into serializable dictionary payloads
    trajectory_data = []
    for event in history:
        if hasattr(event, "to_dict"):
            trajectory_data.append(event.to_dict())
        elif hasattr(event, "model_dump"): # For Pydantic-based event layers
            trajectory_data.append(event.model_dump())
        else:
            trajectory_data.append(str(event))

    # Automatically creates a 'trajectory_logs' folder inside your phase directory
    log_dir = os.path.join(phase_path, "trajectory_logs")
    os.makedirs(log_dir, exist_ok=True) 

    # Saves the json file neatly inside that new directory
    output_file = os.path.join(log_dir, "trajectory.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(trajectory_data, f, indent=2, default=str)

    print(f"🎉 Success! Trajectory saved to: {output_file}")


if __name__ == "__main__":
    main()
