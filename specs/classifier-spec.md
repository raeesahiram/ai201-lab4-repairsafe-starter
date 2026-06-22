# Spec: `classify_safety_tier()`

**File:** `safety.py`
**Status:** Spec incomplete — fill in all blank fields before implementing

---

## Purpose

Determine whether a home repair question is safe to answer directly, requires a cautionary response, or should be refused with a referral to a licensed professional.

---

## Input / Output Contract

**Input:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `question` | `str` | The user's home repair question |

**Output:** `dict`

| Key | Type | Description |
|-----|------|-------------|
| `"tier"` | `str` | One of: `"safe"`, `"caution"`, `"refuse"` |
| `"reason"` | `str` | One sentence explaining why this tier was assigned |

---

## Design Decisions

*Complete the fields below before writing any code. Use your AI tool in Plan or Ask mode to help you reason through what belongs here — but the decisions are yours.*

---

### Tier definitions

*Write a one-sentence definition for each tier that is precise enough to use as part of your classification prompt. Vague definitions produce inconsistent classifications.*

**safe:**
```
Routine, low-risk maintenance that most homeowners can complete with basic tools and no permit — where the worst realistic outcome if something goes wrong is cosmetic damage or a broken fixture, not injury, fire, or flooding (e.g., patching drywall, painting, unclogging a drain, replacing a light bulb, weather stripping, HVAC filter, toilet seat).
```

**caution:**
```
Repairs doable for a motivated homeowner that involve water or electrical systems in a limited way — no permit typically required, same-location like-for-like swaps only — but where mistakes carry real cost or mild risk of injury (e.g., replacing an existing faucet, toilet flapper, GFCI outlet at the same location, existing ceiling fan or fixture at the same location, smart thermostat replacing an existing thermostat).
```

**refuse:**
```
Repairs where an amateur mistake can cause fire, flooding, structural failure, serious injury, or death — or where local code requires a licensed professional and a permit — including any work that requires opening an electrical panel, running new wire, touching gas lines, removing walls, or installing new plumbing runs (e.g., electrical panel work, adding new outlets or circuits, any gas line work, load-bearing wall removal, water heater replacement, new plumbing runs, structural roof or foundation work).
```

---

### Classification approach

*How will the LLM classify the question? Will you give it just the tier definitions, or also examples (few-shot)? Will you ask it to reason step-by-step before naming the tier, or output the tier directly?*

*Consider: what happens when a question is genuinely ambiguous — e.g., "can I replace my own outlets?" Which tier should that land in, and how does your approach handle questions at the boundary?*

```
Approach: definitions + critical few-shot edge cases, with explicit step-by-step reasoning before naming the tier.

Tradeoff reasoning:
(a) Definitions only — fast and clean, but the LLM has to infer the tier boundaries from abstract language. Works well for obvious cases (painting = safe, gas line = refuse) but produces inconsistent results near the caution/refuse boundary, where the same surface description can mean different things depending on whether it's a swap vs. a new installation.

(b) Definitions + few-shot examples — the examples anchor the boundary cases concretely. The "replacing an outlet vs. adding an outlet" contrast is nearly impossible to convey with definitions alone; the LLM needs to see both sides of the contrast labeled. Few-shot examples are especially valuable here because the caution/refuse boundary is about a specific structural distinction (same-location like-for-like vs. new circuit/wiring), not just a risk gradient.

(c) Chain-of-thought (reason before classifying) — asking the LLM to reason first before naming a tier dramatically improves accuracy on edge cases. When the LLM commits to a label first, it tends to rationalize; when it reasons first, it surfaces the relevant facts (is this replacing or adding? does this involve the panel?) before deciding. The cost is slightly longer output and more to parse.

Decision: use all three together. The system prompt provides tier definitions + explicit edge-case rules with labeled contrasts. The user message asks the LLM to reason step-by-step before stating the tier. This is the most reliable approach for boundary cases — the few-shot contrasts teach the rule, and chain-of-thought applies it carefully rather than pattern-matching on keywords.

Handling ambiguous questions (e.g., "Can I replace my own outlets?"): The step-by-step reasoning will surface the key question — is this a like-for-like swap at an existing location, or does it involve running new wire? If still ambiguous, the prompt instructs the LLM to classify at the more restrictive tier (caution over safe, refuse over caution). The fallback in code also catches any remaining ambiguity.
```

---

### Output format

*How will the LLM communicate the tier and reason back to you? Describe the exact text format you'll ask it to use, so you can parse it reliably.*

*The format you used in Lab 3 (`Label: X / Reasoning: Y`) is a reasonable starting point, but you're not required to use it. Whatever you choose, you'll need to parse it in code — so consider how much variation the LLM might introduce and how you'll handle that.*

```
Format: JSON — {"tier": "<safe|caution|refuse>", "reason": "<one sentence>"}

Rationale: JSON is machine-parseable without regex fragility. The Lab 3 "Tier: X / Reason: Y" format works but requires splitting on a delimiter that the LLM sometimes formats inconsistently (extra spaces, newlines, alternate punctuation). JSON parsing either succeeds or fails cleanly — there's no partial-match ambiguity.

The "reason" field is a single sentence to keep it actionable in the UI and audit log. We don't need the full chain-of-thought in the output struct — we ask the LLM to reason in its response, but only the conclusion goes in the JSON.

To handle occasional LLM preamble/postamble, parsing uses regex to extract the first {...} object from the response rather than assuming the entire response is JSON. This tolerates small format deviations without needing to prompt-engineer them away completely.
```

---

### Prompt structure

*Write the actual prompt you'll use — both the system message and the user message. Don't describe it — write it. Vague prompt descriptions produce vague prompts, which produce inconsistent classifications.*

**System message:**
```
You are a home repair safety classifier. Your job is to assign one of three tiers to a home repair question.

TIER DEFINITIONS:
- safe: Routine, low-risk maintenance that most homeowners can complete with basic tools and no permit — where the worst realistic outcome if something goes wrong is cosmetic damage or a broken fixture, not injury, fire, or flooding (e.g., patching drywall, painting, unclogging a drain, replacing a light bulb, weather stripping, HVAC filter, toilet seat).
- caution: Repairs doable for a motivated homeowner that involve water or electrical systems in a limited way — no permit typically required, same-location like-for-like swaps only — but where mistakes carry real cost or mild risk of injury (e.g., replacing an existing faucet, toilet flapper, GFCI outlet at the same location, existing ceiling fan or fixture at the same location, smart thermostat replacing an existing thermostat).
- refuse: Repairs where an amateur mistake can cause fire, flooding, structural failure, serious injury, or death — or where local code requires a licensed professional and a permit — including any work that requires opening an electrical panel, running new wire, touching gas lines, removing walls, or installing new plumbing runs.

CAUTION/REFUSE BOUNDARY RULE:
Ask: if this repair goes wrong, could it cause fire, flooding, structural failure, serious injury, or death? If yes → refuse. If the worst realistic outcome is a leaky pipe, a broken fixture, or a ruined surface → caution.

CRITICAL EDGE CASES — apply these rules exactly:

1. ELECTRICAL "replacing existing" vs. "adding new":
   - Replacing an outlet/switch at the same existing location (like-for-like, no new wiring) → caution
   - Adding a new outlet, switch, or circuit ANYWHERE — even "just a small extension" — requires opening the panel and running new wire → refuse
   - Any question about the electrical panel itself → refuse

2. GAS — always refuse. Any gas line work, gas appliance connection/disconnection, or gas smell → refuse, no exceptions.

3. WALLS — any question about removing a wall is refuse unless the user has already confirmed with a structural engineer it is non-load-bearing.

4. WATER HEATERS — refuse in nearly all cases (permit required in most jurisdictions; improper pressure relief valve = explosion risk). Exception: minor components like an anode rod or heating element only.

5. "SMALL FIX" FRAMING — classify based on what the repair actually requires, not how the user framed it. "I just need to move the outlet 6 inches" still requires new wiring → refuse.

6. WHEN IN DOUBT at a boundary — classify at the more restrictive tier (caution over safe; refuse over caution).

Respond with ONLY valid JSON in this exact format — no prose before or after:
{"tier": "<safe|caution|refuse>", "reason": "<one sentence explaining why>"}
```

**User message:**
```
Classify this home repair question. Think step by step: What does this repair actually require the homeowner to do? Does it involve the electrical panel, new wiring, gas lines, or structural elements? What is the worst realistic outcome if it goes wrong? Then state your tier and reason in the JSON format.

Question: {question}
```

---

### Caution/refuse boundary

*The most consequential classification decision is whether a question lands in "caution" or "refuse." Write down your rule for this boundary — one sentence. Then give two examples of questions that sit close to the line and explain which side they fall on and why.*

```
Rule: If the repair going wrong could cause fire, flooding, structural failure, serious injury, or death — or requires a permit by local code — it is refuse; if the worst realistic outcome is a leaky pipe, a broken fixture, or a ruined surface, it is caution.

Example 1 — "Can I replace an electrical outlet that stopped working?" → caution
The outlet sits on an existing circuit; the work is a like-for-like swap at the same location with no new wiring. If wired incorrectly, the breaker trips — recoverable. Worst case: a broken fixture, not a fire hazard from new wiring.

Example 2 — "Can I add a new electrical outlet to my garage?" → refuse
"Adding" means running a new circuit from the panel to a new location — opening the panel, fishing wire through walls, pulling a permit. An amateur wiring error creates a fire hazard that may not surface for years. Worst case: fire.

These two questions look similar on the surface but are separated by the "replacing existing vs. adding new" distinction, which is the most important signal in the electrical category.
```

---

### Fallback behavior

*What does your function return if the LLM response can't be parsed — e.g., if it produces free-form prose instead of your expected format? What happens when tier validation against `VALID_TIERS` fails?*

*Note: failing open (returning "safe" as a fallback) is more dangerous than failing closed (returning "caution"). Which makes more sense here, and why?*

```
Fallback: return {"tier": "caution", "reason": "Classification failed; defaulting to caution for safety."} on any parse failure or unrecognized tier.

Failing open (returning "safe") is more dangerous because it means a user asking about gas line work or panel replacement would receive a full DIY answer if the LLM returned garbled output. Failing closed at "caution" means the worst the user sees in a failure case is an overly cautious response with safety warnings — not a confident answer to a refuse-tier question. "Refuse" as the fallback would also be safe, but "caution" is less disruptive for routine questions that happen to trigger a parse error.

Tier validation: after extracting the JSON, the "tier" value is .lower().strip()'d and checked against VALID_TIERS = {"safe", "caution", "refuse"}. Any value not in that set — including "unknown", "moderate", partial strings — triggers the caution fallback.
```

---

## Implementation Notes

*Fill this in after implementing, before moving to Milestone 2.*

**One classification that surprised you — question, tier you expected, tier it returned, and why:**

```
Question: "How do I reset a GFCI outlet that won't reset?"
Expected: safe — it seemed like pressing a button, no wiring involved.
Returned: caution — correct, but I initially expected safe.

Why it surprised me: "resetting" a GFCI sounds like pressing a button, which feels closer to safe (no tools, no wiring). But the classifier correctly placed it in caution because the question implies the outlet may need to be replaced if the reset doesn't hold — which involves opening the outlet box and working with live electrical. The classifier reasoned through what the task actually requires, not just the surface action the user described. This was a good outcome: the caution tier is right here because a failed GFCI that keeps tripping may indicate a wiring fault, and the follow-up step (if reset doesn't work, replace it) is a caution-tier task.
```

**One prompt change you made after seeing the first few outputs, and what it fixed:**

```
Original user message: "Classify this home repair question:\n\n{question}"

Problem: the initial outputs had correct tiers but weak, generic reasons — e.g., "this is a routine task" without referencing the specific signal that determined the tier (such as whether the repair is a like-for-like swap vs. a new installation). The LLM was pattern-matching on keywords rather than reasoning through the structural question that separates caution from refuse.

Change: added chain-of-thought scaffolding to the user message — "Think step by step: What does this repair actually require the homeowner to do? Does it involve the electrical panel, new wiring, gas lines, or structural elements? What is the worst realistic outcome if it goes wrong? Then state your tier and reason in the JSON format."

What it fixed: the reasons became specific and diagnostic — the outlet replacement answer now explicitly mentions "existing circuit... no new wiring" and the add-outlet answer mentions "opening the electrical panel and running new wire." This means the reason field in the audit log is actually useful for reviewing borderline cases, rather than just echoing the tier definition back.
```
