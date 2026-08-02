# Build Instructions: `config/target_config.yaml`

## Goal

`toy_target/app.py` currently hardcodes its target settings directly in Python: `MODEL = "claude-sonnet-5"`, `MAX_TOKENS = 1024`, and a hardcoded path to `system_prompt.txt`. That's fine for a standalone toy chatbot, but the adapter layer needs to point at *configurable* targets — swap the model, point at a different system prompt, change token limits — without touching adapter code. This file is that externalized configuration, and `DirectAPIAdapter` (file 3) will read from it instead of hardcoding anything.

This is a data file, not code — but it's still an artifact you're designing deliberately: the schema (what keys exist, what they mean) is the actual "spec" here.

## Prerequisites

None strictly, but conceptually this should be built right after `01_target_base.md` since its contents are dictated by what `DirectAPIAdapter` will need to read in file 3. If you find yourself needing a field that isn't listed below while building file 3, add it here first, then use it.

## Spec

Create the directory `config/` at the project root (it doesn't exist yet) and the file `config/target_config.yaml` inside it.

Minimum required top-level keys, matching what `toy_target/app.py` currently hardcodes so you're externalizing real values, not inventing new ones:

| Key | Type | Value in this project | Meaning |
|---|---|---|---|
| `model` | string | `claude-sonnet-5` | The Anthropic model name the adapter should call. |
| `system_prompt_path` | string | `toy_target/system_prompt.txt` | Path (relative to project root) to the system prompt file the adapter should load and send. |
| `max_tokens` | int | `1024` | Max tokens for the Messages API call. |

Recommended additional keys, since the toy target also depends on a tool definition and you'll want this config to be the single source of truth for "what does this target look like":

| Key | Type | Meaning |
|---|---|---|
| `name` | string | A human-readable label for this target (e.g. `"Aria - FakeCorp Support (toy target)"`), useful later when reports need to say what was tested. |
| `provider` | string | `"anthropic"` for now — leaves room to add other providers later without redesigning the schema. |

Decide for yourself whether `tools` (the `lookup_order` tool definition currently inlined in `toy_target/app.py`) belongs in this YAML file too, or stays as Python since it includes a JSON schema. Either is defensible — if you do move it into YAML, make sure the structure maps cleanly onto the `tools` list shape the Anthropic SDK expects (a list of objects with `name`, `description`, `input_schema`).

## Step-by-step build instructions

1. Create the `config/` directory at the project root.
2. Create `config/target_config.yaml`.
3. Write the required keys (`model`, `system_prompt_path`, `max_tokens`) as flat top-level YAML keys — no nesting needed for a single-target config.
4. Add the recommended `name` and `provider` keys.
5. Double check `system_prompt_path` is written as a path relative to the project root (not relative to `config/`, not absolute) — decide this convention now and document it with a comment in the YAML file itself, since file 3 (`direct_api.py`) will need to resolve this path relative to *something* consistent, and getting the base directory wrong is the most common bug this kind of config introduces.
6. Add a one-line YAML comment (`#`) above the file explaining what it's for — this is a config file another developer (or you, in three weeks) should be able to read cold.

## Edge cases to handle

- YAML is whitespace-sensitive; if you add nested keys later (e.g., for the Playwright adapter's selectors in file 4), get the indentation right — 2 spaces is the conventional YAML style and matches this project's other YAML usage (the attack library YAML files coming in Week 3).
- `max_tokens` must load as an `int`, not a `str` — don't quote it in the YAML.
- Keep this file out of `.gitignore` — unlike `.env`, this config holds no secrets and should be committed so the repo is reproducible.

## Resources

- [PyYAML documentation](https://pyyaml.org/wiki/PyYAMLDocumentation) — specifically `yaml.safe_load()`, which is what file 3 will use to read this.
- [YAML syntax primer](https://yaml.org/spec/1.2.2/) if YAML syntax itself is unfamiliar — flat key-value pairs are all you need here, no anchors or multi-document files.

## Definition of done / self-test

1. In a Python REPL: `import yaml; yaml.safe_load(open("config/target_config.yaml"))`.
2. Confirm the result is a `dict` with the keys you defined, correct types (`max_tokens` should print as an `int`, e.g. `1024`, not `"1024"`).
3. Confirm `system_prompt_path` resolves to a real file: `from pathlib import Path; Path(cfg["system_prompt_path"]).exists()` should be `True` when run from the project root.
4. Move on to `03_direct_api_adapter.md` once this loads cleanly.
