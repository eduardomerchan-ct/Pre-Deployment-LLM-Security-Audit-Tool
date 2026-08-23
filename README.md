 Pre-Deployment LLM Security Audit Tool

A red-teaming tool I'm building to automatically test LLM-powered apps for the kinds of security issues described in the **OWASP Top 10 for LLM Applications (2025)** ,before those apps go anywhere near production. It sends a library of attack prompts at a target chatbot, judges whether the target fell for them, scores how bad each finding is, and (eventually) writes a pentest-style report.

🚧 **Status: work in progress.** This is a solo learning project, not a finished product — see [Build Status](#build-status) below for exactly what's real right now and what's still on paper. I'd rather show honest progress than pretend it's done.

## Why I'm building this

I'm a student trying to actually understand LLM red-teaming instead of just reading about it — the kind of thing you can talk through confidently in an interview because you built it, hit real bugs in it, and fixed them yourself. Rather than run someone else's scanner against a chatbot, I wanted to build the scanner: design the attack schema, write the attack cases myself (inspired by known technique classes, not copy-pasted from any public tool), wire up the judging logic, and see where my own assumptions broke.

So this repo is as much a study log as it is a tool. Some of that shows up directly in the code — comments explaining *why* a line exists, tickets in [`tickets/`](tickets/) written against my own bugs, research briefs in [`researchfiles/`](researchfiles/) for each OWASP category I read up on before building against it.

## ⚠️ Authorization & ethics

**Only ever point this at a system you own or have explicit written permission to test.** Prompt injection, jailbreaking, and system-prompt extraction techniques are genuinely useful for defensive testing and genuinely harmful when run against something you don't have permission to touch.

That's why this project ships its own target: `toy_target/` is a small fake "customer support" chatbot (**Aria**, for a made-up company called **FakeCorp**) built from scratch specifically to be attacked. It has a persona to break, a planted internal policy to bypass, a fake secret to try to extract, and one fake tool to misuse — a safe, fully-owned sandbox with no real users or real data behind it.

## Scope: what this tests (and what it doesn't)

This is a **black-box, prompt-level** tool — it only ever talks to a target through its normal chat interface, the same way an actual user or attacker would. That naturally rules some OWASP categories out. Of the 10, **6 are in scope**:

| Code | Category | In scope? | Why |
|---|---|---|---|
| LLM01 | Prompt Injection | ✅ | Direct override, roleplay/persona jailbreaks, indirect injection via pasted "documents" |
| LLM02 | Sensitive Information Disclosure | ✅ | Extracting the planted fake secret through direct asks and social-engineering framing |
| LLM05 | Improper Output Handling | ✅ | Getting the target to emit raw HTML/script-like content a naive frontend might render unsafely |
| LLM06 | Excessive Agency | ✅ | Misusing the `lookup_order` tool or bypassing the refund-approval policy |
| LLM07 | System Prompt Leakage | ✅ | Direct requests, translation tricks, "repeat the text above" style extraction |
| LLM09 | Misinformation | ✅ | Leading questions designed to produce a confidently-stated fabricated answer |
| LLM03 | Supply Chain | ❌ | Needs access to training data / dependency chains a black-box prompt tool can't reach |
| LLM04 | Data & Model Poisoning | ❌ | Same reason — out of reach without training-time access |
| LLM08 | Vector/Embedding Weaknesses | ❌ | No RAG pipeline in this project to attack |
| LLM10 | Unbounded Consumption | ❌ | That's a load/cost test, not a red-team prompt test — different tool entirely |

## Architecture

```
toy_target/     the authorized target — Aria, a fake FakeCorp support chatbot
targets/        TargetAdapter interface + a DirectAPIAdapter that talks to it via the Anthropic API
attacks/        pydantic schema for attack cases + the hand-written YAML attack library
engine/         (planned) runs the library against a target, logs every prompt/response
judge/          (planned) rule-based checks + an LLM-as-judge for the cases that need real judgment
scoring/        (planned) exploitability × impact severity scoring
report/         (planned) turns a completed run into a Markdown pentest-style report
```

The idea is a straight pipeline: **attack library → execution engine → judge → severity scorer → report**, with every module written against a small, boring interface so pieces can be swapped or extended later (e.g. a Playwright adapter for a real web chat UI instead of `DirectAPIAdapter`, targeting an API directly).

**Provider:** everything runs on the Anthropic API — `claude-sonnet-5` as the target/attacker-facing model, and (once the judge layer exists) `claude-haiku-4-5` for cheap, fast judge and mutation calls.

## Build status

I'm tracking this against a 9-week plan (see [`plan`](plan)). Here's what's actually working today versus what's still just a folder:

- [x] **Toy target** — `toy_target/app.py`, a working chatbot with a planted policy, a planted secret, and a `lookup_order` tool
- [x] **Target adapter layer** — `TargetAdapter` ABC, `DirectAPIAdapter`, config-driven via `config/target_config.yaml`, verified against the live API
- [x] **Attack case schema** — `attacks/schema.py` (pydantic v2), with a loader that fails loudly on bad YAML instead of silently producing garbage
- [ ] **Attack library** — in progress; LLM01 and LLM07 have cases so far, LLM02/05/06/09 still need to be written
- [ ] **Execution engine** (`engine/runner.py`) — not started
- [ ] **Rule-based judge** (`judge/rules.py`) — not started
- [ ] **LLM-as-judge** (`judge/llm_judge.py`) — not started
- [ ] **Severity scoring** (`scoring/severity.py`) — not started
- [ ] **Report generator** (`report/generate.py`) — not started
- [ ] **Mutation loop** (`engine/mutate.py`) — the actual differentiator, planned last
- [ ] **Sample report + real audit run** — planned once everything above exists

Bugs I've already found and written up as tickets (mostly from a code-review pass on the schema loader) live in [`tickets/`](tickets/) — I'm keeping them instead of quietly fixing and deleting, since "here's a bug I found in my own code and how I fixed it" is a more honest artifact than pretending it was clean the first time.

## Quickstart

This runs the pieces that exist today (the toy target + the adapter layer). The engine/judge/report pipeline isn't wired up yet.

```bash
git clone https://github.com/eduardomerchan-ct/Pre-Deployment-LLM-Security-Audit-Tool.git
cd Pre-Deployment-LLM-Security-Audit-Tool

python -m venv .venv
.venv\Scripts\activate        # on Windows
# source .venv/bin/activate   # on macOS/Linux

pip install -r requirements.txt

cp .env.example .env          # then add your own ANTHROPIC_API_KEY
```

Talk to the toy target directly:

```bash
python -m toy_target.app
```

Or exercise it through the adapter the rest of the tool will actually use:

```python
from targets.direct_api import DirectAPIAdapter

adapter = DirectAPIAdapter()
response = adapter.send("hello")
print(response.text)
```

Load and validate the attack library:

```python
from attacks.schema import load_attack_library

cases = load_attack_library()
print(f"{len(cases)} attack cases loaded")
```

## What I'm learning

Concretely, this project has forced me to actually deal with: designing a schema that fails loudly instead of silently (pydantic's `extra="forbid"` + a loader that names the exact bad file), the difference between a tool's *advertised* input schema and what actually gets validated at runtime, why lazy client initialization matters for import-time side effects, and reading the OWASP LLM Top 10 closely enough to write my own attack cases instead of borrowing someone else's.

## Resources I used

- [OWASP Top 10 for LLM Applications (2025)](https://genai.owasp.org/) — read closely for each in-scope category before writing cases against it
- [Promptfoo](https://github.com/promptfoo/promptfoo) and [DeepTeam](https://github.com/confident-ai/deepteam) — studied as structural references for how a mature red-teaming tool organizes categories and rubrics (not copied from — used to sanity-check I'd covered the bases)
- [Anthropic API docs](https://docs.claude.com/) — Messages API and tool-use patterns

## License

No license file yet — planned for the final polish pass once the tool is functionally complete.
