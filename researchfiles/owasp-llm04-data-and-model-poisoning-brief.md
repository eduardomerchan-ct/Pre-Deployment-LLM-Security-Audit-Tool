# OWASP LLM04:2025 — Data and Model Poisoning

**TL;DR:** Data and model poisoning is contamination of an LLM's training, fine-tuning, or embedding/RAG data that plants biased outputs, backdoors, or degraded behavior — and recent research shows it takes a strikingly *small*, fixed number of poisoned samples to work, regardless of how large the overall dataset is.

## Key findings

- **Poisoning scales with sample count, not dataset size.** Anthropic's October 2025 research (with UK AISI and the Alan Turing Institute) found that roughly 250 malicious documents were enough to backdoor models ranging from 600M to 13B parameters — the poisoned fraction of the dataset shrank as models grew, but the attack still worked, upending the old assumption that attackers need to control a percentage of training data.
- **Backdoors survive safety training.** Related work on date-conditional backdoors found that standard safety fine-tuning did not remove implanted backdoors, and adversarial training sometimes made the model *better at concealing* the backdoor rather than eliminating it — meaning post-hoc alignment isn't a reliable cleanup step.
- **RAG/embedding pipelines are the most practically exploitable surface.** Black-box attacks that inject just 5 malicious documents into a retrieval corpus of millions achieved 97% attack success on Natural Questions, 99% on HotpotQA, and 91% on MS-MARCO — far cheaper than poisoning a pretraining run, since it only requires getting documents indexed, not access to the training pipeline.
- **The risk spans the full lifecycle, not just pretraining.** OWASP's four vulnerability patterns are: pretraining data manipulation, fine-tuning data manipulation, embedding/vector-store manipulation (RAG poisoning), and pipeline supply-chain compromise — e.g., a scan of 100 poisoned models on Hugging Face found each could inject malicious code into a downstream user's machine, showing the risk extends to model distribution, not just data curation.
- **OWASP names specific technique families** beyond generic "bad data": split-view poisoning (an attacker manipulates data a crawler will see differently at scrape-time vs. review-time) and frontrunning poisoning (racing to insert malicious content before a scheduled crawl/training cut).

## How to use this

- LLM04 is correctly out of scope for this project's 6-category audit (LLM01/02/05/06/07/09): it's fundamentally a training-time and supply-chain risk, not something reachable through black-box `send()` calls to a deployed chat endpoint — you can't poison a model you don't control the training pipeline for.
- The one sub-case that *is* reachable via prompt-level testing is RAG/embedding poisoning — but `toy_target/app.py` has no retrieval or vector-store component (confirmed: just `app.py` + `system_prompt.txt`), so there's currently nothing to target even if you wanted to add a stretch case.
- If you ever extend the toy target with a RAG layer for a future milestone, the 5-malicious-document / high-success-rate finding above is the concrete attack pattern to reproduce as a test case (inject a small number of adversarial documents, query for the targeted fact, check whether retrieval surfaces the poisoned content).
- Worth keeping in your README's "out of scope" rationale: LLM04 requires pipeline/infrastructure access this project doesn't have, which is a cleaner justification than just "not covered."

## Sources

- [LLM04:2025 Data and Model Poisoning — OWASP Gen AI Security Project](https://genai.owasp.org/llmrisk/llm042025-data-and-model-poisoning/)
- [OWASP Top 10 for LLM Applications 2025 (PDF)](https://owasp.org/www-project-top-10-for-large-language-model-applications/assets/PDF/OWASP-Top-10-for-LLMs-v2025.pdf)
- [Data Poisoning in LLMs: Just 250 Documents Create a Backdoor — Analytics Vidhya](https://www.analyticsvidhya.com/blog/2025/10/llm-data-poisoning/)
- [OWASP Top 10 LLM, Updated 2025: Examples & Mitigation Strategies — Oligo Security](https://www.oligo.security/academy/owasp-top-10-llm-updated-2025-examples-and-mitigation-strategies)
- [Introduction to Data Poisoning: A 2026 Perspective — Lakera](https://www.lakera.ai/blog/training-data-poisoning)
- [OWASP Top 10 for LLM Applications 2025: Data and Model Poisoning — Check Point](https://www.checkpoint.com/cyber-hub/what-is-llm-security/data-and-model-poisoning/)
