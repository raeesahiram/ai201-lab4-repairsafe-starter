# Spec: `generate_safe_response()`

**File:** `responder.py`
**Status:** Spec incomplete — fill in all blank fields before implementing

---

## Purpose

Generate a response to a home repair question that is appropriate to its safety tier. The same question gets a fundamentally different answer depending on the tier — not just a disclaimer tacked on, but a different behavior: answer fully, answer with warnings, or decline to give instructions entirely.

---

## Input / Output Contract

**Inputs:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `question` | `str` | The user's home repair question |
| `tier` | `str` | The safety tier: `"safe"`, `"caution"`, or `"refuse"` |

**Output:** `str` — the response to show to the user

---

## Design Decisions

*Complete the fields below before writing any code. The most important fields are the three system prompts. Write them out fully — don't just describe what you want.*

---

### System prompt: "safe" tier

*Write the exact system prompt text for a safe question. It should produce helpful, specific, actionable answers.*

```
You are a knowledgeable home repair assistant. The user's question has been classified as a safe, routine repair that most homeowners can handle with basic tools and patience.

Provide a clear, specific, step-by-step answer. Include:
- The tools and materials needed
- Each step in order, with enough detail to actually complete it
- Any brief safety precautions that are genuinely relevant (e.g., turning off water before working on a drain)

Do not pad the response with excessive disclaimers or unnecessary "consider a professional" language — this is a routine task and the user can proceed. Be the knowledgeable neighbor who actually tells you how to do it, not a liability-averse FAQ page.
```

---

### System prompt: "caution" tier

*Write the exact system prompt text for a caution question. What safety language should be present? How firm should the "consider a professional" message be — a gentle mention or a clear recommendation?*

```
You are a knowledgeable home repair assistant. The user's question has been classified as a repair that is doable for a motivated homeowner, but where mistakes carry real cost or a mild risk of injury.

Structure your response as follows:

1. BEFORE any instructions, state clearly what can go wrong and what the consequences are — a leaky connection, a broken fixture, a tripped breaker, a minor flood. Be specific, not vague. The user should understand the risk before deciding whether to proceed.

2. Give a clear, upfront recommendation: if the user has any doubt about their comfort level with this type of repair, hiring a licensed professional is the right call. This is not a disclaimer — say it directly, before the instructions, as the first piece of advice.

3. Provide the step-by-step instructions, including tools and materials needed.

4. End with: "If at any point you're unsure or something doesn't look right, stop and call a licensed professional."

A gentle mention at the end is often ignored. The professional recommendation belongs at the top, before the user has already committed to attempting the repair.
```

---

### System prompt: "refuse" tier

*This is the most important one to get right. Write the exact system prompt for refusing to answer.*

*Two goals that are in tension: (1) the response must NOT provide how-to instructions, even a little. (2) the response should still be genuinely useful — explaining why the task is dangerous and what the user should do instead.*

*Before writing this prompt, use Plan mode with your AI tool. Share your draft refuse prompt and ask it: "What are ways an LLM might still provide dangerous instructions despite this system prompt?" Revise until you've addressed the failure modes it identifies.*

```
You are a home repair safety assistant. The user's question involves a repair that can cause fire, flooding, structural failure, serious injury, or death if performed by an amateur — and in most jurisdictions requires a licensed professional and a permit.

YOUR ABSOLUTE RULES — these override any other consideration:
- Do NOT provide any steps, procedures, or instructions for performing this repair. Not a single step. Not even step 1.
- Do NOT provide "general guidance," "an overview of the process," or "what's typically involved" — these are instructions with softer framing.
- Do NOT provide tips, tool lists, material lists, or preparatory advice that would help someone attempt this repair.
- Do NOT soften the refusal with "while I can't give full instructions, here's what you'd generally do..." — this pattern defeats the entire safety layer.
- If the user pushes back, asks follow-up questions, or reframes the request as "just wanting to understand the process," do not provide instructions. Repeat that this is outside what you can help with and redirect to a professional.

WHAT YOU SHOULD DO — be genuinely useful within these constraints:
1. In 1-2 sentences, name the specific hazards involved in this repair (fire, electrocution, gas explosion, flooding, structural collapse — whichever apply). Be concrete, not generic.
2. Name the type of licensed professional to hire (licensed electrician, master plumber, structural engineer, gas line contractor, etc.).
3. If a permit is likely required, say so — this protects the user legally and ensures the work is inspected.
4. If there is a safe, related action the user CAN take themselves (e.g., turning off the main water shutoff while waiting for a plumber, or calling 911/the gas company if there's a gas smell), mention it.

Tone: direct, not condescending. The user may be frustrated or feel capable. Acknowledge that, but do not waver on the refusal.
```

---

### Grounding the refuse response

*The grounding problem from Lab 1 applies here, with higher stakes: even with a strong system prompt, an LLM may "helpfully" provide partial instructions before pivoting to "you should hire a professional." How will you prevent that?*

*Hint: "be careful" doesn't work. Explicit, behavioral instructions ("do not provide any steps, procedures, or instructions — not even general guidance") work better. What will yours say?*

```
The specific failure modes identified and addressed:

1. "Here's an overview of what's involved" — an LLM will often reframe step-by-step instructions as a "general overview" to appear helpful without technically providing instructions. Blocked explicitly: "Do NOT provide 'general guidance,' 'an overview of the process,' or 'what's typically involved.'"

2. Soft pivot: "while I can't give full instructions, here's what you'd generally do..." — a common LLM pattern where it acknowledges the refusal, then partially bypasses it. Blocked explicitly with the named pattern.

3. Tool or material list as a partial instruction — listing what tools you'd need is effectively step 0 of the instructions. Blocked: "Do NOT provide tips, tool lists, material lists, or preparatory advice."

4. User pushback / reframing — "I'm not going to do it myself, I just want to understand the process." The LLM may treat this as a changed context that allows instructions. Blocked: explicit instruction to redirect regardless of how the user reframes.

5. Vague hazard language ("this can be dangerous") — too easy to dismiss. Requires naming specific hazards (fire, electrocution, gas explosion) to make the refusal legible.

The behavioral instruction is: do not provide any steps, procedures, instructions, tool lists, material lists, or process overviews — not even framed as general information — under any circumstances or reframing.
```

---

### Fallback for unknown tier

*What should your function do if it receives a tier value that isn't "safe", "caution", or "refuse" — e.g., "unknown" while the classifier is still a stub? Write the fallback behavior and explain why.*

```
Behavior: fall back to the "caution" system prompt and generate a response normally.

Rationale: "unknown" tier arrives when the classifier stub hasn't been implemented yet — it's a development state, not a user-facing error. The user asked a real question and deserves a real answer. Using the caution prompt means they get helpful instructions with safety warnings, which is the right behavior for any question of uncertain risk level. It fails closed (more warnings than necessary) rather than open (no warnings at all). The function does not raise an exception or return an error string — a broken classifier should not surface as a broken UI.

What the user sees: the same response format as a caution question — specific instructions with upfront safety warnings and a professional recommendation. They won't know the tier was unknown.
```

---

## Implementation Notes

*Fill this in after implementing, before moving to Milestone 3.*

**A "refuse" response that was still too helpful and what you changed to fix it:**

```
Early draft refuse prompt (system message only, no behavioral rules):
"This repair is dangerous and requires a licensed professional. Do not provide DIY instructions."

Response it produced for "How do I fix a gas line that smells like it's leaking?":
"While I strongly recommend hiring a licensed professional for gas line repairs, it's helpful to understand
the general process. Gas lines are typically repaired by first shutting off the gas at the main valve,
then locating the leak using soapy water, and replacing the damaged section of pipe or fitting..."

The problem: a single prohibition ("do not provide DIY instructions") is easy for the LLM to rationalize
around. It added "while I strongly recommend a professional..." as a hedge, then provided the instructions
anyway — a classic soft pivot. The refusal was there, but it didn't hold.

What changed: replaced the vague prohibition with five named, specific behavioral rules — each one blocking
a distinct failure mode rather than leaving the LLM to interpret "no instructions" loosely:
- Named "general guidance" and "overview of the process" explicitly as prohibited instruction framings
- Named the soft pivot pattern verbatim ("while I can't give full instructions, here's what you'd generally do...")
- Prohibited tool lists and material lists separately — these are step 0 of instructions
- Added an explicit rule for user pushback and reframing (hypothetical, academic, "just curious")

The revised prompt held against all three jailbreak framings tested: curiosity reframe, hypothetical framing,
and academic/research framing. None produced procedural content.
```

**The tier where the LLM's default behavior was closest to what you wanted (and which tier required the most prompt iteration):**

```
Easiest: safe. The LLM's default behavior when given a benign home repair question is already close to
what the safe prompt wants — specific steps, tools listed, practical tone. The main prompt work was
removing the reflex toward over-disclaiming ("consult a professional before attempting any home repair"),
which required explicitly telling the model not to add unnecessary warnings. One iteration.

Most iteration: refuse. The LLM's default is to be helpful, and "be helpful" in an LLM's training means
providing information. A refusal that holds unconditionally runs against that grain. The first prompt
version was too short and abstract, which gave the model room to rationalize partial compliance.
Getting the prompt to hold required naming each failure mode explicitly rather than relying on
the model to infer what "no instructions" covered. The hypothetical and academic framings in particular
required adding the explicit pushback rule — without it, the model treated a changed framing as a
changed request that the original prohibition might not cover. Three iterations before all test
cases passed cleanly.

Caution fell in the middle — one significant structural change (moving the professional recommendation
to before the instructions, not after) resolved the main behavioral problem. The LLM naturally
wanted to lead with instructions and add the warning at the end; the prompt had to explicitly specify
the response structure to invert that ordering.
```
