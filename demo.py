"""
Automated demo script — simulates a full patient triage conversation
and prints the complete exchange including the final Triage Note.
"""

import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

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
2.  ASK FOLLOW-UP QUESTIONS one at a time to gather missing critical info.
3.  CITE RULES EXPLICITLY in every triage recommendation.
4.  ESCALATE WHEN UNCERTAIN using Rule ESC-01.
5.  GENERATE THE TRIAGE NOTE using this exact format once you have enough info:

--- TRIAGE NOTE START ---
**Triage Note**
- Date/Time: See system timestamp
- Urgency Level: [Level and label]
- Recommended Department: [Department]
- Rule Applied: [Rule ID and name]
- Rule Justification: [Which condition in the rule was met]

**Patient Report Summary:**
- Initial Complaint: [What the patient first said]
- Information Gathered via Follow-up: [Key facts confirmed]
- Information Still Unknown: [Items that could not be confirmed]

**Important Disclaimer:** This triage note is a routing recommendation only.
It does not constitute a medical diagnosis or clinical assessment.
--- TRIAGE NOTE END ---
"""

SEP = "=" * 65

def run_demo():
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    chat = client.chats.create(
        model="gemini-3.6-flash",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.2,
            max_output_tokens=2048,
        ),
    )

    # --- SCENARIO: Fever + Stiff Neck (should trigger Rule FV-01) ---
    conversation = [
        "BEGIN_SESSION",
        "I've had a high fever since yesterday night and I have a terrible headache",
        "Yes, my neck feels very stiff and I can barely turn it",
        "I don't think so, no rash that I can see. But I feel a bit confused and disoriented",
    ]

    print(SEP)
    print("  LIVE DEMO — Patient Intake Triage Assistant")
    print("  Scenario: Patient with Fever + Stiff Neck")
    print(SEP)
    print()

    for i, message in enumerate(conversation):
        if i == 0:
            # Initial greeting trigger
            resp = chat.send_message(message)
            print(f"ASSISTANT: {resp.text}\n")
            print(f"{'─'*65}\n")
        else:
            print(f"PATIENT: {message}\n")
            resp = chat.send_message(message)
            print(f"ASSISTANT: {resp.text}\n")
            print(f"{'─'*65}\n")

            if "--- TRIAGE NOTE START ---" in resp.text:
                print()
                print(SEP)
                print("  DEMO COMPLETE - Triage note successfully generated!")
                print(SEP)
                break

if __name__ == "__main__":
    run_demo()
