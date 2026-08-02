# OWASP LLM02:2025 — Sensitive Information Disclosure

**TL;DR:** LLM02 covers an LLM application leaking PII, credentials, proprietary business data, or model-internal information through its outputs — and it's the risk that jumped the most in the 2025 revision, climbing from #6 in 2023 to #2, reflecting how often it shows up in real incidents versus the other categories.

## Key findings

- **Three distinct leak vectors, not one.** OWASP splits this into (1) PII leakage during normal interaction, (2) proprietary/training-data exposure via inversion attacks — where an attacker reconstructs training inputs from model outputs, as demonstrated by the "Proof Pudding" attack (CVE-2019-20634) against a production email-filtering model — and (3) inadvertent disclosure of confidential business data in generated responses.
- **The Samsung ChatGPT incident is the canonical real-world case, and it's a data-handling failure, not a jailbreak.** In March 2023, three separate Samsung employees pasted proprietary source code, defect-detection code, and a transcribed internal meeting into ChatGPT for help — no attacker was involved. Because inputs could be retained/used for training, this counted as a confidentiality breach and led Samsung to ban employee use of external generative AI tools entirely.
- **Attack scenario 2 (targeted prompt injection) is the version most relevant to adversarial testing:** crafted prompts designed to bypass input filters and coax out sensitive data the model has access to — as opposed to scenario 1, which is accidental exposure with no attacker in the loop at all. A red-teaming tool needs cases for both, since they fail differently (filter bypass vs. missing sanitization).
- **OWASP's mitigation stack is layered, not a single fix:** input/output sanitization (scrub or mask before training and before responding), least-privilege access controls on any data source the model can reach, differential privacy or federated learning for training pipelines, concealing system prompts so internal config can't be fished out, and tokenization/redaction via pattern matching (e.g., regex or NER for SSNs, keys, emails) as a deterministic output-side backstop.
- **Prompt-level restrictions are explicitly called out as weak.** OWASP notes that telling the model "don't repeat sensitive data" in the system prompt is a real mitigation layer but not sufficient on its own — it can be bypassed via prompt injection or clever phrasing, so it should never be the only control.

## How to use this

- For `attacks/library/llm02_sensitive_information_disclosure.yaml` (matching the `llm07_system_prompt_leakage.yaml` naming pattern already in `attacks/library/`): build at least two case families — (a) direct/injected extraction attempts asking the model to repeat back user data, credentials, or business context it was given earlier in the conversation, and (b) indirect extraction via roleplay, summarization, or "debug mode" pretexts that try to get the model to surface data it was told to withhold.
- Seed the toy "Aria" target's conversation/tool context with something plausibly sensitive (e.g., a fake customer PII field or an internal discount code) so `FailureCondition` checks have something real to catch — an LLM02 test against a target with no sensitive data in scope can't meaningfully fail.
- Given OWASP's explicit warning that system-prompt restrictions are bypassable, don't rely solely on "the system prompt says not to leak X" as your severity signal — pair it with an output-side pattern-match check (regex/keyword) for whatever sensitive value you seeded, similar to the redaction mitigation OWASP recommends.

## Sources

- [LLM02:2025 Sensitive Information Disclosure — OWASP Gen AI Security Project](https://genai.owasp.org/llmrisk/llm02-insecure-output-handling/)
- [OWASP Top 10 for LLM Applications 2025 (PDF)](https://owasp.org/www-project-top-10-for-large-language-model-applications/assets/PDF/OWASP-Top-10-for-LLMs-v2025.pdf)
- [LLM02:2025 Sensitive Information Disclosure & Prevention — Indusface](https://www.indusface.com/learning/owasp-llm-sensitive-information-disclosure/)
- [Incident 768: ChatGPT Reportedly Implicated in Samsung Data Leak of Source Code and Meeting Notes](https://incidentdatabase.ai/cite/768/)
- [Lessons learned from ChatGPT's Samsung leak — Cybernews](https://cybernews.com/security/chatgpt-samsung-leak-explained-lessons/)
- [Samsung Bans ChatGPT Among Employees After Sensitive Code Leak — Forbes](https://www.forbes.com/sites/siladityaray/2023/05/02/samsung-bans-chatgpt-and-other-chatbots-for-employees-after-sensitive-code-leak/)
