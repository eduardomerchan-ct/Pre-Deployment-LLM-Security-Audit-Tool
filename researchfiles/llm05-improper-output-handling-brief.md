# LLM05:2025 — Improper Output Handling

**TL;DR:** Improper Output Handling is the failure to validate or sanitize an LLM's *output* before it's passed to downstream systems (browsers, shells, databases, email clients) — meaning a successful prompt injection or jailbreak becomes a classic web/backend vulnerability (XSS, SQLi, RCE, SSRF) the moment that output is trusted blindly.

## Key findings
- The core distinction: LLM01 (Prompt Injection) is about manipulating what goes *in*; LLM05 is about what happens when the (possibly manipulated) output goes *out* without checks. It's also distinct from LLM09 (Overreliance), which is about trusting the output's *correctness*, not its *safety as a payload*.
- Because output can be steered via crafted input, downstream code that trusts LLM text implicitly is effectively granting users indirect access to whatever that downstream system can do.
- Concrete attack vectors: LLM output rendered as Markdown/HTML/JS in a browser → XSS/CSRF; output dropped into `exec()`/`eval()` or a system shell → RCE; output concatenated into SQL → SQL injection; output used in file paths → path traversal; output used in an SSRF-prone HTTP call or email template → data exfiltration or phishing.
- OWASP's official mitigation stance: treat the model as an untrusted user — apply a zero-trust / OWASP ASVS-style input-validation approach *to the output*, use context-aware output encoding (HTML/SQL/JS), parameterized queries, strict CSPs, and logging/monitoring for anomalous output patterns.
- Real-world shape of the bug: a support chatbot that Markdown-renders LLM replies into HTML is the canonical case — get the model to emit a script tag or `javascript:` URI via prompt injection, and the render step turns it into a live XSS payload with no additional exploit needed.

## How to use this
- This maps directly onto your in-scope category set (LLM01/02/05/06/07/09) — LLM05 attack cases should specifically test what happens *after* a successful LLM01 injection, not duplicate LLM01 cases. Good `AttackCase` shape: prompt the model to emit HTML/JS, shell-like commands, or SQL fragments, then assert your harness checks whether that output would be unsafely consumed downstream (not just whether the model "refused").
- Since your toy target (Aria) is a support chatbot, a realistic LLM05 test is getting it to emit a Markdown/HTML response containing a `<script>` or `<img onerror=...>` payload — mirrors the canonical real-world case above.
- Because your target adapter is direct-API (no browser/DOM rendering layer yet), most LLM05 checks will need to be judged as "did the model produce output that *would* be dangerous if rendered/executed downstream" rather than observing an actual exploit — worth deciding now how your `FailureCondition` schema expresses that distinction.

## Sources
- [LLM05:2025 Improper Output Handling — OWASP Gen AI Security Project](https://genai.owasp.org/llmrisk/llm052025-improper-output-handling/)
- [OWASP Top 10 for LLM Applications 2025 (PDF)](https://owasp.org/www-project-top-10-for-large-language-model-applications/assets/PDF/OWASP-Top-10-for-LLMs-v2025.pdf)
- [LLM05: Improper Output Handling Risks & Mitigations — Indusface](https://www.indusface.com/learning/owasp-llm-improper-output-handling/)
- [LLM Improper Output Handling — A10 Networks glossary](https://www.a10networks.com/glossary/llm-output-validation/)
