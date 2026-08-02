# LLM01: Prompt Injection (OWASP Top 10 for LLM Applications, 2025)

**TL;DR:** Prompt injection is #1 on the OWASP LLM Top 10 because LLMs process instructions and untrusted data through the same channel, so crafted input can hijack model behavior; there is no full fix, only defense-in-depth (least privilege, filtering, human approval on risky actions, adversarial testing).

## Key findings
- **Root cause is architectural, not a bug**: LLMs don't structurally separate "instructions" from "data" — both arrive as plain text in the same context window, so a model can't reliably tell a legitimate system instruction apart from an attacker's text pretending to be one.
- **Two main attack surfaces**: *Direct* injection is the attacker typing malicious instructions straight into the prompt/chat (e.g., "ignore all previous instructions..."). *Indirect* injection is more dangerous — instructions are hidden in external content (emails, web pages, documents, tool outputs) that the LLM later ingests and obeys without the attacker ever touching the interface directly.
- **Real-world proof it's not theoretical**: EchoLeak (CVE-2025-32711) was a zero-click indirect prompt injection against Microsoft 365 Copilot — a single crafted email caused Copilot to exfiltrate internal files to an attacker server with no user interaction, by chaining bypasses of Microsoft's prompt-injection classifier, link redaction, and content security policy.
- **RAG and fine-tuning don't solve it**: OWASP explicitly notes that neither retrieval-augmented generation nor fine-tuning meaningfully mitigates LLM01 — both still feed untrusted text into the same instruction-following channel.
- **OWASP's recommended defense-in-depth stack**: least-privilege tool/agent permissions, input/output filtering, segregating external content so it can't be interpreted as instructions, constraining behavior via system prompts with defined output formats, human-in-the-loop approval for high-risk actions, and ongoing adversarial (red-team) testing.
- **The realistic goal is risk reduction, not elimination**: current industry framing (Sysdig, Radware) treats every defense as a mitigation layer — the objective is lowering injection success rate, shrinking blast radius when one succeeds, and detecting/responding fast, not achieving zero successful injections.

## How to use this
- For your attack library (`attacks/library/*.yaml`), model both direct injection (malicious user turns) and indirect injection (malicious content embedded in tool outputs/RAG documents the toy target might ingest) as distinct `Category: LLM01` cases — they exercise different trust boundaries.
- Since RAG/fine-tuning aren't real mitigations, don't let your scoring rubric treat "uses RAG" as a mitigating factor for LLM01 findings.
- Use EchoLeak's attack chain (classifier bypass → content-boundary bypass → auto-triggered exfiltration) as a template for a multi-stage indirect injection test case if you want a more advanced scenario beyond single-turn direct injection.
- When writing severity/failure conditions, consider scoring on blast radius and detectability, not just "was the injection followed" — that matches how the field currently frames success.

## Sources
- [OWASP Top 10 for LLM Applications 2025 (PDF)](https://owasp.org/www-project-top-10-for-large-language-model-applications/assets/PDF/OWASP-Top-10-for-LLMs-v2025.pdf)
- [OWASP LLM Top 10 — Promptfoo](https://www.promptfoo.dev/docs/red-team/owasp-llm-top-10/)
- [OWASP Top 10 for LLM Applications: Risks & Mitigations — Mend.io](https://www.mend.io/blog/2025-owasp-top-10-for-llm-applications-a-quick-guide/)
- [The Comprehensive Guide to Prompt Injection Attacks in 2026 — Sysdig](https://www.sysdig.com/learn-cloud-native/prompt-injection)
- [Prompt Injection in 2026: Impact, Attack Types and Defenses — Radware](https://www.radware.com/cyberpedia/prompt-injection/)
- [EchoLeak: The First Real-World Zero-Click Prompt Injection Exploit — arXiv](https://arxiv.org/pdf/2509.10540)
- [Threat Intelligence Report: EchoLeak (CVE-2025-32711)](https://lemley.io/posts/echoleak/)
