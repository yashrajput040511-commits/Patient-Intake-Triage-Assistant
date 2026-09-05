"""
Patient Intake Triage Assistant — Flask Web Server
Track ID: PS01

Architecture note: google-genai's httpx client closes itself between
requests in a synchronous Flask context. The fix is to store only the
conversation history (list of dicts) per session, and create a fresh
genai.Client + chat replay on every request.
"""

import os
import uuid
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from google import genai
from google.genai import types
import traceback as tb

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# In-memory store: session_id -> list of {"role": "user"|"model", "text": "..."}
session_histories: dict = {}

# ── Triage Rules ─────────────────────────────────────────────────────────────

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
  IF patient reports fever WITHOUT the high-risk symptoms in FV-01 AND fever > 38.5C (101.3F)
  THEN Urgency: Level 3 (Urgent) | Department: General Walk-In Clinic

Rule AP-01 (Abdominal Pain - High Risk):
  IF patient reports sudden/severe abdominal pain OR pain localized to lower-right quadrant
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

SYSTEM_PROMPT = f"""
You are a Patient Intake Triage Assistant operating in a walk-in medical clinic.
Your role is to collect information from patients, evaluate their condition against
official triage rules, and generate a structured triage note.

{TRIAGE_RULES}

=== YOUR STRICT OPERATING INSTRUCTIONS ===

1.  NEVER DIAGNOSE. You are forbidden from diagnosing any medical condition.
    You only route patients based on their reported symptoms.

2.  ASK FOLLOW-UP QUESTIONS. If a patient's initial description does not
    provide enough information to confidently match a triage rule, you MUST ask
    specific, targeted follow-up questions ONE AT A TIME. Prioritize the most
    critical missing information first.

3.  CITE RULES EXPLICITLY. Every triage recommendation MUST explicitly name the
    rule (e.g., "Based on Rule CP-01..."). Never make a recommendation without
    a rule citation.

4.  ESCALATE WHEN UNCERTAIN. If you cannot confidently match a rule, apply
    Rule ESC-01 and escalate to a human triage nurse. Never guess.

5.  COVERED COMPLAINTS ONLY: Fever, Injury, Chest Pain, Breathing Difficulty,
    Abdominal Pain. For anything else, direct the patient to the front desk.

6.  GENERATE THE TRIAGE NOTE once you have sufficient information.
    You MUST use this EXACT format with these EXACT markers:

--- TRIAGE NOTE START ---
**Triage Note**
- Date/Time: See system timestamp
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

# ── Gemini helper with Quota-Proof Fallback Chain ─────────────────────────────

MODEL_FALLBACK_LIST = [
    "gemini-3.5-flash",
    "gemini-3.7-flash",
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "gemini-flash-latest",
    "gemini-3.6-flash",
]

def call_gemini(history: list) -> str:
    """
    Call Gemini with an automatic model fallback chain.
    If the primary model hits a 429 quota limit, it immediately tries alternative models.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    # Build the contents list for the API
    contents = []
    for turn in history:
        role = turn["role"]   # "user" or "model"
        contents.append(
            types.Content(
                role=role,
                parts=[types.Part(text=turn["text"])]
            )
        )

    last_err = None
    for model_name in MODEL_FALLBACK_LIST:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.2,
                    max_output_tokens=2048,
                ),
            )
            return response.text or ""
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                print(f"[WARN] Model {model_name} hit 429 quota. Falling back to next model...")
                last_err = e
                continue
            else:
                # Non-quota error, raise immediately
                raise e

    raise last_err or RuntimeError("All model fallback attempts failed.")

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/start", methods=["POST"])
def start_session():
    """Create a new triage session and return the initial greeting."""
    session_id = str(uuid.uuid4())
    try:
        # Start with a trigger message to get the greeting
        history = [{"role": "user", "text": "BEGIN_SESSION"}]
        greeting = call_gemini(history)
        history.append({"role": "model", "text": greeting})
        session_histories[session_id] = history

        return jsonify({
            "session_id": session_id,
            "message": greeting,
            "note": None,
        })
    except Exception as e:
        tb.print_exc()
        return jsonify({"error": f"Failed to start session: {str(e)}"}), 500


@app.route("/api/chat", methods=["POST"])
def chat_endpoint():
    """Send a patient message and get the assistant's response."""
    data = request.get_json()
    session_id = data.get("session_id")
    user_message = data.get("message", "").strip()

    if not session_id or session_id not in session_histories:
        return jsonify({"error": "Invalid or expired session. Please refresh and start a new session."}), 400

    if not user_message:
        return jsonify({"error": "Empty message."}), 400

    try:
        history = session_histories[session_id]

        # Append user message and call Gemini with full history
        history.append({"role": "user", "text": user_message})
        assistant_text = call_gemini(history)
        history.append({"role": "model", "text": assistant_text})

        # Check if a triage note was generated
        note_data = None
        text_to_return = assistant_text

        if "--- TRIAGE NOTE START ---" in assistant_text and "--- TRIAGE NOTE END ---" in assistant_text:
            start_idx = assistant_text.index("--- TRIAGE NOTE START ---") + len("--- TRIAGE NOTE START ---")
            end_idx   = assistant_text.index("--- TRIAGE NOTE END ---")
            note_raw  = assistant_text[start_idx:end_idx].strip()

            # Parse urgency level for color-coding in the UI
            urgency_level = 0
            if "Level 1" in note_raw:        urgency_level = 1
            elif "Level 2" in note_raw:      urgency_level = 2
            elif "Level 3" in note_raw:      urgency_level = 3
            elif "Level 4" in note_raw or "Level 5" in note_raw:
                                             urgency_level = 4
            # else 0 = ESC-01 / human review

            note_data = {"raw": note_raw, "urgency_level": urgency_level}

            # Strip the note block from the conversational reply
            before = assistant_text[:assistant_text.index("--- TRIAGE NOTE START ---")].strip()
            after  = assistant_text[assistant_text.index("--- TRIAGE NOTE END ---") + len("--- TRIAGE NOTE END ---"):].strip()
            text_to_return = (before + "\n\n" + after).strip()

            # Session is complete — clean up
            del session_histories[session_id]

        return jsonify({"message": text_to_return, "note": note_data})

    except Exception as e:
        tb.print_exc()
        return jsonify({"error": f"Internal error: {str(e)}"}), 500


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Patient Intake Triage Assistant  |  Track PS01")
    print("  Running on http://localhost:8000")
    print("=" * 60 + "\n")
    app.run(debug=False, port=8000, host="0.0.0.0")
