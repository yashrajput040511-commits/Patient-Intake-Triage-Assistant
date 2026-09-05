"""
Patient Intake Triage Assistant
Track ID: PS01

This assistant processes a patient's description of their condition in plain language,
asks follow-up questions for missing critical details, evaluates against triage rules,
and generates a structured triage note.

IMPORTANT: This system does NOT diagnose patients. It is a triage routing tool only.
"""

import os
import sys
from dotenv import load_dotenv
from google import genai
from google.genai import types

# ---------------------------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------------------------
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("\n[ERROR] GEMINI_API_KEY not found.")
    print("  1. Copy .env.example to .env")
    print("  2. Set your Gemini API key inside .env")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Triage Rules (Single Source of Truth)
# ---------------------------------------------------------------------------
TRIAGE_RULES = """
=== OFFICIAL TRIAGE RULES ===

Rule CP-01 (Chest Pain - Critical):
  IF patient reports chest pain AND (pain radiates to arm/jaw OR accompanied by sweating/nausea/shortness of breath)
  THEN Urgency: Level 1 (Resuscitation/Immediate) | Department: Emergency Department

Rule BD-01 (Breathing Difficulty - Critical):
  IF patient reports severe breathing difficulty OR cannot speak in full sentences OR has bluish lips/face/fingertips
  THEN Urgency: Level 1 (Resuscitation/Immediate) | Department: Emergency Department

Rule FV-01 (Fever - High Risk):
  IF patient reports fever AND (stiff neck OR confusion/disorientation OR non-blanching rash)
  THEN Urgency: Level 2 (Emergent) | Department: Emergency Department

Rule FV-02 (Fever - Standard):
  IF patient reports fever WITHOUT the high-risk symptoms in FV-01 AND fever > 38.5°C (101.3°F)
  THEN Urgency: Level 3 (Urgent) | Department: General Walk-In Clinic

Rule AP-01 (Abdominal Pain - High Risk):
  IF patient reports sudden/severe abdominal pain OR pain localized to lower-right quadrant (possible appendicitis area)
  THEN Urgency: Level 2 (Emergent) | Department: Emergency Department

Rule AP-02 (Abdominal Pain - Moderate):
  IF patient reports abdominal pain that is NOT sudden/severe and NOT in lower-right quadrant
  THEN Urgency: Level 3 (Urgent) | Department: General Walk-In Clinic

Rule IN-01 (Minor Injury):
  IF patient reports minor cuts (bleeding is controlled), sprains, bruising, or contusions
  AND no loss of consciousness AND no severe/worsening pain AND no numbness/tingling
  THEN Urgency: Level 4/5 (Less Urgent / Non-Urgent) | Department: Urgent Care / Minor Injuries Unit

Rule IN-02 (Serious Injury):
  IF patient reports injury AND (loss of consciousness occurred OR severe pain OR visible bone/deformity)
  THEN Urgency: Level 2 (Emergent) | Department: Emergency Department

Rule ESC-01 (Escalation - Human Review Required):
  IF no rule above can be clearly and confidently matched
  OR if the patient's responses are ambiguous or contradictory
  OR if symptoms suggest a high-risk condition but information is insufficient
  THEN Urgency: REQUIRES HUMAN REVIEW | Route to: On-Duty Triage Nurse immediately

=== END OF TRIAGE RULES ===
"""

# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = f"""
You are a Patient Intake Triage Assistant operating in a walk-in medical clinic.
Your role is to collect information from patients, evaluate their condition against
official triage rules, and generate a structured triage note.

{TRIAGE_RULES}

=== YOUR STRICT OPERATING INSTRUCTIONS ===

1.  **NEVER DIAGNOSE.** You are forbidden from diagnosing any medical condition.
    You only route patients based on their reported symptoms. If you are asked
    for a diagnosis, firmly decline and redirect to triage.

2.  **ASK FOLLOW-UP QUESTIONS.** If a patient's initial description does not
    provide enough information to confidently match a triage rule, you MUST ask
    specific, targeted follow-up questions one at a time. Do NOT bombard the
    patient with multiple questions at once. Prioritize the most critical
    missing information first.

3.  **CITE RULES EXPLICITLY.** Every triage recommendation you make MUST
    explicitly name the rule (e.g., "Based on Rule CP-01..."). Never make
    a recommendation without a rule citation.

4.  **ESCALATE WHEN UNCERTAIN.** If you cannot confidently match a rule, or
    if the case seems high-risk but lacks clarity, you MUST apply Rule ESC-01
    and escalate to a human triage nurse. Never guess on uncertain cases.

5.  **COVERED COMPLAINTS ONLY.** You cover: Fever, Injury, Chest Pain,
    Breathing Difficulty, and Abdominal Pain. If a patient presents with
    something outside this scope, acknowledge their concern and politely
    direct them to speak with the front desk for proper routing.

6.  **GENERATE THE TRIAGE NOTE** once you have gathered sufficient information.
    Use the following exact format. Wrap it between the markers shown below:

--- TRIAGE NOTE START ---
**Triage Note**
- Date/Time: [current date/time - use "See system timestamp"]
- Urgency Level: [Level and label, e.g., Level 1 (Resuscitation/Immediate)]
- Recommended Department: [Department name]
- Rule Applied: [Rule ID and name, e.g., Rule CP-01 (Chest Pain - Critical)]
- Rule Justification: [Explain exactly which condition in the rule was met]

**Patient Report Summary:**
- Initial Complaint: [Verbatim or close paraphrase of what the patient first said]
- Information Gathered via Follow-up: [Bullet list of key facts confirmed during conversation]
- Information Still Unknown: [Bullet list of critical items that could not be confirmed]

**Important Disclaimer:** This triage note is a routing recommendation only.
It does not constitute a medical diagnosis or clinical assessment.
--- TRIAGE NOTE END ---

=== GREETING ===
Start the conversation by warmly greeting the patient and asking them to
describe their current symptoms or reason for their visit in their own words.
"""

# ---------------------------------------------------------------------------
# ANSI Color Codes for better CLI readability
# ---------------------------------------------------------------------------
class Color:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    CYAN    = "\033[96m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    RED     = "\033[91m"
    MAGENTA = "\033[95m"
    DIM     = "\033[2m"
    WHITE   = "\033[97m"

def print_banner():
    """Print the application banner."""
    print(Color.CYAN + Color.BOLD)
    print("=" * 65)
    print("   PATIENT INTAKE TRIAGE ASSISTANT  |  Track PS01")
    print("              Walk-In Clinic System")
    print("=" * 65)
    print(Color.RESET)
    print(Color.YELLOW + "  [!] IMPORTANT: This system does NOT provide medical diagnoses.")
    print("      It is a triage routing tool only. In a life-threatening")
    print("      emergency, please call emergency services (e.g., 911) immediately.")
    print(Color.RESET)
    print(Color.DIM + "-" * 65 + Color.RESET)
    print()

def print_assistant(text: str):
    """Print assistant response with formatting."""
    # Check if it's a triage note
    if "--- TRIAGE NOTE START ---" in text:
        parts = text.split("--- TRIAGE NOTE START ---")
        if parts[0].strip():
            print(Color.CYAN + Color.BOLD + "  Assistant: " + Color.RESET + Color.WHITE + parts[0].strip() + Color.RESET)
            print()
        note_and_rest = parts[1].split("--- TRIAGE NOTE END ---")
        note_content = note_and_rest[0].strip()
        print(Color.GREEN + Color.BOLD)
        print("  +" + "-" * 57 + "+")
        print("  |           [OK]  TRIAGE NOTE GENERATED              |")
        print("  +" + "-" * 57 + "+")
        print(Color.RESET)
        for line in note_content.splitlines():
            print(Color.GREEN + "  | " + Color.RESET + line)
        print(Color.GREEN + Color.BOLD)
        print("  +" + "-" * 57 + "+")
        print(Color.RESET)
        if len(note_and_rest) > 1 and note_and_rest[1].strip():
            print(Color.CYAN + Color.BOLD + "  Assistant: " + Color.RESET + Color.WHITE + note_and_rest[1].strip() + Color.RESET)
    else:
        print(Color.CYAN + Color.BOLD + "  Assistant: " + Color.RESET + Color.WHITE + text + Color.RESET)
    print()

def print_user_prompt():
    """Print the user input prompt."""
    print(Color.MAGENTA + Color.BOLD + "  You: " + Color.RESET, end="")

def print_info(text: str):
    """Print an informational system message."""
    print(Color.DIM + f"  [System] {text}" + Color.RESET)
    print()

# ---------------------------------------------------------------------------
# Main Application
# ---------------------------------------------------------------------------
def main():
    print_banner()

    # Initialize Gemini client
    client = genai.Client(api_key=API_KEY)

    print_info("Initializing triage assistant... connected to Gemini API.")
    print(Color.DIM + "  Type your message and press Enter. Type 'exit' or 'quit' to end the session." + Color.RESET)
    print(Color.DIM + "─" * 65 + Color.RESET)
    print()

    # Create a chat session with the system prompt
    chat = client.chats.create(
        model="gemini-3.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.2,  # Low temperature for consistent, rule-based reasoning
            max_output_tokens=2048,
        ),
    )

    # Send an initial empty message to trigger the greeting
    try:
        response = chat.send_message("BEGIN_SESSION")
        print_assistant(response.text)
    except Exception as e:
        print(Color.RED + f"\n[ERROR] Failed to initialize chat session: {e}" + Color.RESET)
        sys.exit(1)

    triage_note_generated = False

    # Main conversation loop
    while True:
        print_user_prompt()
        try:
            user_input = input().strip()
        except (KeyboardInterrupt, EOFError):
            print()
            print_info("Session interrupted by user. Goodbye.")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "bye"):
            print_info("Triage session ended by user. Please proceed to the front desk.")
            break

        try:
            response = chat.send_message(user_input)
            assistant_text = response.text
            print_assistant(assistant_text)

            # Check if the triage note was just generated
            if "--- TRIAGE NOTE START ---" in assistant_text and not triage_note_generated:
                triage_note_generated = True
                print(Color.YELLOW + Color.BOLD)
                print("  " + "=" * 54)
                print("  Triage note has been generated. Please present this to")
                print("  the nurse at the reception desk. Thank you.")
                print("  " + "=" * 54)
                print(Color.RESET)
                print()
                # Allow a final message from the patient before closing
                print_info("You may ask any final questions or type 'exit' to end.")

        except Exception as e:
            print(Color.RED + f"\n[ERROR] An error occurred while contacting the AI: {e}" + Color.RESET)
            print(Color.YELLOW + "  Please try again or speak with the front desk for assistance." + Color.RESET)
            print()


if __name__ == "__main__":
    main()
