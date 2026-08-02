"""The schema every attack case in attacks/library/ must follow.

Attack cases are hand-written YAML files describing what prompt(s) to send
to a target and how to judge the result. Before any other part of this tool
touches a case, it must pass validation against the pydantic models below —
that way a typo in a YAML file fails loudly right away, instead of quietly
producing bad data three modules later.

load_attack_library() is the only function later modules (like
engine/runner.py) should use to get attack cases — nothing else in this
project should read the YAML files or call pydantic directly.
"""

from pathlib import Path  # Path lets us work with file and folder locations in a way that works on any OS.
import yaml  # PyYAML is what turns YAML text into plain Python lists/dicts.
from pydantic import BaseModel  # BaseModel is the base class every schema model below inherits from.
from pydantic import ConfigDict  # ConfigDict lets us set model-wide settings, like forbidding unknown fields.
from pydantic import Field  # Field lets us add extra rules to a field, like min/max values or a required pattern.
from pydantic import ValidationError  # ValidationError is what pydantic raises when data doesn't match a schema.
from pydantic import model_validator  # model_validator lets us write custom checks that look at multiple fields at once.
from typing import Literal  # Literal restricts a field to an exact, fixed set of allowed values.


# Category is the fixed list of OWASP LLM Top 10 codes this project actually tests for.
# LLM03/LLM04 are excluded because they need training-data/dependency access this black-box tool can't reach,
# LLM08 is excluded because there's no RAG target to test, and LLM10 is excluded because it's a load test, not a red-team check.
Category = Literal["LLM01", "LLM02", "LLM05", "LLM06", "LLM07", "LLM09"]


class Turn(BaseModel):
    """One scripted user-side prompt in an attack case's sequence."""

    # role must always be "user" — we only ever script the user's side, the target's reply is real, not pre-written.
    role: Literal["user"]

    # content is the literal text sent to the target for this turn.
    content: str

    # extra="forbid" makes pydantic error on any unrecognized key instead of silently ignoring it.
    model_config = ConfigDict(extra="forbid")


class FailureCondition(BaseModel):
    """Describes how an attack case gets judged: which judge module runs, and what it checks."""

    # type picks which judge module (rule-based checks or the LLM judge) will evaluate this case.
    type: Literal["rule_based", "llm_judge"]

    # check is the name of the specific check function to run, e.g. "contains_system_prompt_substring".
    check: str

    # threshold is the cutoff the check compares against; its exact meaning depends on type, so it's optional here.
    threshold: float | None = None

    # extra="forbid" makes pydantic error on any unrecognized key instead of silently ignoring it.
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def require_threshold_for_rule_based(self) -> "FailureCondition":
        """rule_based checks need a real number to compare against, so threshold can't be missing for them."""
        # Only rule_based cases need a threshold right now — llm_judge's grading scale isn't decided yet.
        if self.type == "rule_based" and self.threshold is None:
            # Stop here with a clear message instead of letting a missing threshold silently break the judge later.
            raise ValueError("threshold is required when type is 'rule_based'")
        # Nothing was wrong, so hand back this same object unchanged.
        return self


class SeverityBase(BaseModel):
    """Base exploitability/impact ratings the Week 7 scorer multiplies together."""

    # exploitability is rated 1-5; ge=1 and le=5 stop any out-of-range number from slipping through.
    exploitability: int = Field(ge=1, le=5)

    # impact is rated 1-5, same bounds and same reasoning as exploitability above.
    impact: int = Field(ge=1, le=5)

    # extra="forbid" makes pydantic error on any unrecognized key instead of silently ignoring it.
    model_config = ConfigDict(extra="forbid")


class AttackCase(BaseModel):
    """One full attack case: a prompt sequence, how to judge it, and its base severity."""

    # id uniquely names this case; the pattern forces kebab-case like "sys-prompt-leak-001" so every id looks the same.
    id: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")

    # category is one of the six in-scope OWASP codes this case is testing for.
    category: Category

    # name is a short, human-readable label for this case, shown in reports/logs.
    name: str

    # turns is the scripted list of user prompts; min_length=1 means every case must send at least one prompt.
    turns: list[Turn] = Field(min_length=1)

    # failure_condition says how this case gets judged as a pass or a fail.
    failure_condition: FailureCondition

    # severity_base holds this case's base exploitability/impact scores for the Week 7 severity scorer.
    severity_base: SeverityBase

    # extra="forbid" makes pydantic error on any unrecognized key instead of silently ignoring it.
    model_config = ConfigDict(extra="forbid")


def load_attack_library(library_dir: Path | str = Path("attacks/library")) -> list[AttackCase]:
    """Load, validate, and return every attack case found under library_dir.

    Reads every *.yaml file in library_dir, validates each case inside it
    against AttackCase, and returns one flat, ordered, deduplicated list.
    This is the only function later modules (like engine/runner.py) should
    call to get attack cases.
    """
    # Make sure library_dir is a real Path object, even if the caller passed a plain string.
    library_dir = Path(library_dir)

    # A missing/typo'd directory would otherwise glob to [] and look identical to a real, empty
    # library — fail loudly here so a bad path can't silently masquerade as "0 attack cases, all passed".
    if not library_dir.is_dir():
        raise ValueError(f"attack library directory not found: {library_dir}")

    # This list will collect every validated AttackCase from every file, in order.
    all_cases: list[AttackCase] = []

    # This maps every case id seen so far to the file that defined it, so duplicates across files can be caught
    # and the error can point at both the original file and the one where the collision was found.
    seen_ids: dict[str, str] = {}

    # sorted() makes file load order always the same, instead of depending on the filesystem's own listing order.
    for yaml_path in sorted(library_dir.glob("*.yaml")):
        # Read the whole file as text, then parse that text into plain Python objects.
        # encoding="utf-8" is pinned explicitly so this doesn't depend on the OS's default locale encoding
        # (e.g. cp1252 on Windows), which would mangle or reject non-ASCII characters in attack case content.
        try:
            raw_content = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            # A syntax error here would otherwise raise a raw PyYAML exception with no file name attached.
            raise ValueError(f"{yaml_path.name}: invalid YAML — {e}") from e

        # An empty file parses to None, and this schema requires a top-level list, not a dict or anything else.
        if raw_content is None or not isinstance(raw_content, list):
            # Stop immediately and name the exact file that's wrong, instead of a confusing error deep inside pydantic.
            raise ValueError(
                f"{yaml_path.name}: expected a top-level YAML list of attack cases, got "
                f"{type(raw_content).__name__}"
            )

        # Go through every raw case dict in this file, keeping its position for error messages.
        for index, raw_case in enumerate(raw_content):
            try:
                # Ask pydantic to check this dict against the AttackCase schema and build a real object from it.
                case = AttackCase.model_validate(raw_case)
            except ValidationError as e:
                # Prefer the case's own id in the error label, if it has one and it's readable as a dict.
                if isinstance(raw_case, dict) and "id" in raw_case:
                    case_label = raw_case["id"]
                else:
                    # No usable id, so fall back to describing the case by its position in the file.
                    case_label = f"index {index}"
                # Re-raise with the file name and case label attached, so the error points straight at the problem.
                raise ValueError(f"{yaml_path.name}, case {case_label}: {e}") from e

            # Check whether this case's id already showed up earlier in the library (this file or an earlier one).
            if case.id in seen_ids:
                # Duplicate ids would silently corrupt run-log grouping and mutation lineage later, so fail loudly now.
                # Name both files involved: the one that defined the id first, and the one where the collision
                # was found, so tracking it down doesn't mean grepping the whole library directory by hand.
                raise ValueError(
                    f"{yaml_path.name}: duplicate attack case id '{case.id}' "
                    f"(first defined in {seen_ids[case.id]})"
                )

            # Remember this id and which file defined it, so later cases (in this file or later files) get
            # checked against it too, and any future collision can name this file as the original.
            seen_ids[case.id] = yaml_path.name

            # Add the freshly validated case to the flat list we'll hand back.
            all_cases.append(case)

    # Return every validated case from every file, in one deterministic, flat list.
    return all_cases
