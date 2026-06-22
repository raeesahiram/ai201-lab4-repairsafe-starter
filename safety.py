import json
import re
from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL, VALID_TIERS

_client = Groq(api_key=GROQ_API_KEY)

_SYSTEM = """You are a home repair safety classifier. Your job is to assign one of four tiers to a home repair question.

TIER DEFINITIONS:
- safe: Routine, low-risk maintenance that most homeowners can complete without specialized tools or training, where mistakes are cheap and easily corrected (e.g., patching drywall, unclogging a drain, painting, replacing a light bulb, replacing a toilet seat, weather stripping, HVAC filter).
- caution: Repairs doable for a motivated homeowner but where mistakes carry real cost or mild injury risk — no permit required, but involves water or electrical systems in a limited way (e.g., replacing an existing faucet, GFCI outlet at same location like-for-like, toilet flapper, existing ceiling fan/fixture at same location, smart thermostat replacing existing thermostat).
- refuse: Repairs where an amateur mistake can cause fire, flooding, structural failure, serious injury, or death — or where local code requires a licensed professional and a permit (e.g., electrical panel work, adding new circuits or outlets, gas line work, load-bearing wall removal, main water line, new plumbing runs, water heater replacement, structural roof repair, foundation work).
- legal: Questions that are not primarily about how to perform a repair, but about permits, code compliance, landlord/tenant obligations, HOA rules, insurance liability, contractor disputes, or whether work requires professional licensing — the issue is legal or regulatory rather than physically dangerous (e.g., "do I need a permit to build a deck?", "can my landlord make me pay for this repair?", "is unpermitted electrical work covered by homeowner's insurance?", "can I sue my contractor for poor work?").

BOUNDARY RULES:

CAUTION/REFUSE: Ask — if this repair goes wrong, could it cause fire, flooding, structural failure, serious injury, or death? If yes → refuse. If the worst realistic outcome is a leaky pipe, a broken fixture, or a ruined surface → caution.

REFUSE/LEGAL DISTINCTION: If the question asks "how do I do X" where X requires a permit → refuse (the physical danger is the issue). If the question asks "do I need a permit for X?" or "who is responsible for X?" without requesting how-to instructions → legal (the regulatory/liability question is the issue, not the physical task).

CRITICAL EDGE CASES — apply these rules exactly:

1. ELECTRICAL "replacing existing" vs. "adding new":
   - Replacing an outlet/switch at the same existing location (like-for-like, no new wiring) → caution
   - Adding a new outlet, switch, or circuit ANYWHERE — even "just a small extension" — requires opening the panel and running new wire → refuse
   - Any question about the electrical panel itself → refuse

2. GAS — always refuse. Any gas line work, gas appliance connection/disconnection, or gas smell → refuse, no exceptions.

3. WALLS — any question about removing a wall is refuse unless the user has already confirmed with a structural engineer it is non-load-bearing. There is no safe DIY method to determine this.

4. WATER HEATERS — refuse in nearly all cases (permit required in most jurisdictions; improper pressure relief valve = explosion risk). Exception: minor internal components only — anode rod, heating element, or thermostat — which are contained replacements that do not affect the pressure relief valve or require a permit.

5. "SMALL FIX" FRAMING — classify based on what the repair actually requires, not how the user framed it. "I just need to move the outlet 6 inches" still requires new wiring → refuse.

6. PERMIT QUESTIONS — "do I need a permit to do X?" is legal, not refuse, even if X itself would be refuse-tier work. The question is about regulatory requirements, not how to perform the repair.

Respond with ONLY valid JSON in this exact format — no prose before or after:
{"tier": "<safe|caution|refuse|legal>", "reason": "<one sentence explaining why>"}"""


def classify_safety_tier(question: str) -> dict:
    """
    Classify a home repair question into one of four safety tiers.
    Returns {"tier": str, "reason": str}.
    """
    try:
        response = _client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": (
                    "Classify this home repair question. Think step by step: Is this asking how to perform "
                    "a repair, or is it asking about permits, liability, landlord obligations, or legal rights? "
                    "If it is a repair question: does it involve the electrical panel, new wiring, gas lines, "
                    "or structural elements? What is the worst realistic outcome if it goes wrong? "
                    "Then state your tier and reason in the JSON format.\n\n"
                    f"Question: {question}"
                )},
            ],
            temperature=0,
        )
        raw = response.choices[0].message.content.strip()

        match = re.search(r'\{[^{}]+\}', raw, re.DOTALL)
        if not match:
            raise ValueError("No JSON object found in response")
        data = json.loads(match.group())

        tier = data.get("tier", "").lower().strip()
        reason = data.get("reason", "").strip()

        if tier not in VALID_TIERS:
            return {"tier": "caution", "reason": f"Could not parse tier '{tier}'; defaulting to caution."}

        return {"tier": tier, "reason": reason}

    except Exception:
        return {"tier": "caution", "reason": "Classification failed; defaulting to caution for safety."}
