# LLM03: Supply Chain (OWASP Top 10 for LLM Applications, 2025)

**TL;DR:** LLM03 covers risk introduced by third-party components — pre-trained models, datasets, fine-tuning adapters, packages, and (in agentic systems) external tools/plugins — that can be tampered with, outdated, or maliciously poisoned before your application code ever runs; the fix is supply-chain hygiene (provenance checks, SBOMs, patching), not prompt-level defenses.

## Key findings
- **Scope expanded in the 2025 revision**: the 2024 list's separate "Insecure Plugin Design" and "Model Theft" entries were folded in — plugin/tool risk now lives partly under LLM03 and partly under LLM06 (Excessive Agency), and model-theft concerns are now framed as a supply-chain integrity problem.
- **Agentic systems raise the stakes**: when an LLM app can pull in tools, frameworks, or even other agents at runtime, LLM03 becomes tightly coupled with LLM06 (Excessive Agency) and LLM10 (Unbounded Consumption) — OWASP calls these three out as the priority triad for agentic architectures.
- **Concrete attack surface is broader than "bad package"**: named threat patterns include tampered pre-trained models/LoRA adapters carrying backdoors, poisoned training/fine-tuning datasets, vulnerable or outdated dependencies, and license/T&C manipulation that creates compliance exposure.
- **Real incidents, not just theory**: a poisoned PyPI package compromised LiteLLM (a widely used LLM proxy gateway) in March 2026, exposing 40,000+ AI pipelines within 40 minutes; separately, CVE-2026-54499 was a remote-code-execution bug from loading an untrusted Stanza model via unsafe pickle deserialization.
- **Unsafe serialization is a persistent, ecosystem-wide problem**: a 2025 study of Hugging Face found roughly 44.9% of high-download repositories still ship models in pickle format, which executes arbitrary code on load and has no built-in integrity guarantee.
- **OWASP's core mitigations**: maintain a signed Software Bill of Materials (SBOM) for all components; only source models from verifiable providers and check file hashes/code signing; run AI red-teaming against third-party models specifically; keep a patching policy for dependencies and APIs; and monitor/audit collaborative model-development environments for abuse.

## How to use this
- Per your project's plan, LLM03 is explicitly out of scope for the audit tool itself (in-scope categories are LLM01, 02, 05, 06, 07, 09) — this brief is background, not a build target. It's still useful context for the README's "out of scope, and why" section: LLM03 is fundamentally a supply-chain/provenance problem (model files, dependencies, datasets), not something a red-teaming *conversation* against a live target can exercise, which is a clean, defensible reason to exclude it.
- If you want one sentence in the README justifying the cut, the LiteLLM/pickle-deserialization angle is a good citation: LLM03 findings come from auditing what a package manager or model registry serves you, not from prompting the model — a different tool category (SBOM/dependency scanners) than what you're building.
- Worth noting for your own toy target (`toy_target/app.py`): if it ever pulls in a pre-trained model, embedding model, or third-party package beyond the Anthropic API, that dependency is technically an LLM03 surface even though your tool won't test for it — just something to be aware of, not act on.

## Sources
- [OWASP Top 10 for LLM Applications 2025 (PDF)](https://owasp.org/www-project-top-10-for-large-language-model-applications/assets/PDF/OWASP-Top-10-for-LLMs-v2025.pdf)
- [LLM03:2025 Supply Chain — OWASP Gen AI Security Project](https://genai.owasp.org/llmrisk/llm032025-supply-chain/)
- [OWASP Top 10 2025: Addressing Software Supply Chain and LLM Risks — Cycode](https://cycode.com/blog/the-2025-owasp-top-10-addressing-software-supply-chain-and-llm-risks-with-cycode/)
- [LLM03:2025 Supply Chain Risks, Attacks & Prevention — Indusface](https://www.indusface.com/learning/owasp-llm-supply-chain/)
- [LLM Supply Chain Security — OWASP LLM03:2025 — A10 Networks](https://www.a10networks.com/glossary/llm-supply-chain-security/)
- [OWASP LLM03:2025 — Supply Chain Vulnerabilities — Harsh Kahate (Medium)](https://harshkahate.medium.com/owasp-llm03-2025-supply-chain-vulnerabilities-the-threat-that-arrives-before-you-write-a-single-7c1079bf12e4)
