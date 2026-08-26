"""Drives the attack library against a TargetAdapter and writes a JSONL run log.

Takes the list[AttackCase] from attacks.schema.load_attack_library(), runs
each case's turn sequence through a TargetAdapter, and writes one JSON
record per case to a timestamped file under runs/. judge/rules.py and
judge/llm_judge.py (Weeks 5-6) are the next things to read that log's
output.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from attacks.schema import AttackCase, load_attack_library
from targets.base import TargetAdapter

# Do not import targets.direct_api at module level -- that import requires
# ANTHROPIC_API_KEY to be set (DirectAPIAdapter.__init__ reads it eagerly).
# Keeping it out of the top-level imports lets this module be imported by
# tests/other modules without a live key configured. See the __main__ block
# below for the one place it's imported.


def run_case(adapter: TargetAdapter, case: AttackCase) -> dict:
    """Run one attack case's full turn sequence against adapter.

    Always returns a JSON-serializable record dict -- never raises. A
    failure partway through the case's turns is caught here and reported
    as status="error" with whatever turns completed before the failure
    preserved, so one bad case can never take down run_library()'s loop.
    """
    turns_log: list[dict] = []
    history = None

    try:
        for turn in case.turns:
            # Retry ownership: adapter.send() already retries once
            # internally (targets/direct_api.py's _call_with_retry). This
            # module only catches and records failures -- it never retries
            # on its own.
            response = adapter.send(turn.content, history=history)
            turns_log.append(
                {
                    "turn_index": len(turns_log),
                    "prompt": turn.content,
                    "response_text": response.text,
                    "latency_ms": response.latency_ms,
                    "timestamp": response.timestamp.isoformat(),
                }
            )
            # response.raw is only ever used in-memory to thread into the
            # next turn's history= argument -- it must never reach the
            # record dict below (it's not JSON-serializable).
            history = response.raw
        status = "ok"
        error = None
    except Exception as e:
        status = "error"
        error = f"{type(e).__name__}: {e}"
        # turns_log is left as-is here on purpose -- whatever turns
        # completed before the exception stay in the transcript.

    if turns_log:
        final_response_text = turns_log[-1]["response_text"]
        total_latency_ms = sum(t["latency_ms"] for t in turns_log)
    else:
        final_response_text = None
        total_latency_ms = None

    return {
        "id": case.id,
        "category": case.category,
        "name": case.name,
        "status": status,
        "error": error,
        "turns": turns_log,
        "final_response_text": final_response_text,
        "total_latency_ms": total_latency_ms,
    }


def run_library(
    adapter: TargetAdapter,
    cases: list[AttackCase] | None = None,
    output_dir: Path | str = "runs",
) -> Path:
    """Run every case in cases (default: the full loaded library) against
    adapter, writing one JSON line per case to a new timestamped file
    under output_dir. Returns the path to that file.
    """
    if cases is None:
        cases = load_attack_library()

    # Anchor against this file's own location -- not the process's current
    # working directory -- same rule targets/direct_api.py follows for
    # config_path, so run_library() always writes to the project's real
    # runs/ directory regardless of where the caller was invoked from.
    project_root = Path(__file__).resolve().parent.parent
    output_dir = Path(output_dir)
    resolved_output_dir = output_dir if output_dir.is_absolute() else project_root / output_dir
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    # Generated once, up front, independent of any individual case's
    # timestamp -- so the file gets a name even if the very first case's
    # very first API call fails outright.
    run_timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = resolved_output_dir / f"run_{run_timestamp}.jsonl"

    n = len(cases)
    ok_count = 0
    error_count = 0

    # encoding="utf-8" explicitly -- don't rely on the platform default
    # (cp1252 on Windows), since several attack prompts contain non-ASCII
    # punctuation. Opened once and written to incrementally so a crash
    # partway through a long run doesn't lose every already-completed case.
    with open(log_path, "w", encoding="utf-8") as f:
        for i, case in enumerate(cases, start=1):
            print(f"[{i}/{n}] {case.id} ({case.category})...", end=" ", flush=True)
            record = run_case(adapter, case)
            print(record["status"])
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()
            if record["status"] == "ok":
                ok_count += 1
            else:
                error_count += 1

    print(f"\nDone: {ok_count} ok, {error_count} error out of {n} cases. Log: {log_path}")

    return log_path


if __name__ == "__main__":
    from targets.direct_api import DirectAPIAdapter

    adapter = DirectAPIAdapter()
    log_path = run_library(adapter)
    print(f"\nRun complete: {log_path}")
