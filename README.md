TRACKID=PS01

# Product Requirements Document (PRD): Patient Intake Triage Assistant

## 1. Project Overview
**Project Name:** Patient Intake Triage Assistant
**Track ID:** PS01
**Core Objective:** Build a triage assistant that processes a patient's description of their condition written in plain, everyday language. It must ask relevant follow-up questions if critical details are missing, and evaluate the case against a set of triage rules.

## 2. Scope
The system is designed to handle common walk-in complaints, specifically limited to:
- Fever
- Injury
- Chest Pain
- Breathing Difficulty
- Abdominal Pain

## 3. Core Features & Output Requirements
### 3.1 Conversational Triage
- The assistant must ingest plain-language descriptions of patient conditions.
- The assistant must identify missing critical details required to evaluate the triage rules and ask relevant follow-up questions to the patient.

### 3.2 Triage Note Generation
The final output must be a structured triage note that includes:
- **Recommended Urgency Level & Department:** Where the patient should be routed and how quickly.
- **Rule Citation:** The specific rule or reasoning justifying the recommendation.
- **Information Comparison:** What the patient initially reported vs. what was established during follow-ups.
- **Unknowns:** Any information that remains unknown or could not be gathered.

## 4. Strict Constraints
- **NO DIAGNOSIS:** The system **must not diagnose** the patient under any circumstances.
- **EXPLICIT CITATION:** It must explicitly cite the rule behind every single recommendation.
- **NO GUESSING:** It must escalate uncertain or high-risk cases to a human operator instead of guessing.

## 5. Initial Triage Rules (Dataset)
The system will evaluate cases against the following predefined rules:

* **Rule CP-01 (Chest Pain - Critical):** If the patient reports chest pain, especially with radiation (arm/jaw) or accompanied by sweating/nausea, classify as **Urgency: Level 1 (Resuscitation/Immediate)** and route to **Emergency Department**.
* **Rule BD-01 (Breathing Difficulty - Critical):** If the patient reports severe breathing difficulty, inability to speak in full sentences, or bluish lips/face, classify as **Urgency: Level 1 (Resuscitation/Immediate)** and route to **Emergency Department**.
* **Rule FV-01 (Fever - High Risk):** If the patient reports a fever accompanied by a stiff neck, confusion, or a rash that doesn't fade under pressure, classify as **Urgency: Level 2 (Emergent)** and route to **Emergency Department**.
* **Rule AP-01 (Abdominal Pain - High Risk):** If the patient reports sudden, severe abdominal pain, or pain localized to the lower right quadrant, classify as **Urgency: Level 2 (Emergent)** and route to **Emergency Department**.
* **Rule IN-01 (Minor Injury):** If the patient reports minor cuts (bleeding controlled), sprains, or contusions with no loss of consciousness and no severe pain, classify as **Urgency: Level 4/5 (Less Urgent/Non-Urgent)** and route to **Urgent Care / Minor Injuries Unit**.
* **Rule ESC-01 (Escalation):** If the case does not clearly match any of the above rules, if the patient is unresponsive to follow-ups, or if there is any ambiguity/uncertainty, classify as **Requires Human Review** and escalate immediately to a **Human Triage Nurse**.
