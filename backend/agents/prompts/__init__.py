"""Central prompt registry for the six specialist agents.

Why this exists: prompts used to be inline strings duplicated across the agent
files (the patient block lived in six places). Now each agent's prompt text lives
in its own module here, the shared patient/persona block lives once in `_base.py`,
and agents read their prompt via `get_prompt(name)` instead of hardcoding a string.

How to use:
- Edit prompt wording          -> the per-agent file (e.g. `safety.py`).
- Edit the patient context     -> `_base.py` (built from the DB profile at runtime).
- Switch which version is live -> `active.toml` (no Python changes).
- A/B a new prompt version     -> add `"v2": ...` to that agent's VERSIONS dict,
                                  then set its line in `active.toml` to "v2".
"""
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

from backend.agents.prompts import (
    behavior,
    caregiver_liaison,
    companion,
    health,
    reminder,
    safety,
)
from backend.agents.prompts._base import build_patient_context, with_context

# name -> {version -> prompt text}
PROMPTS: dict[str, dict[str, str]] = {
    "safety": safety.VERSIONS,
    "health": health.VERSIONS,
    "reminder": reminder.VERSIONS,
    "companion": companion.VERSIONS,
    "behavior": behavior.VERSIONS,
    "caregiver": caregiver_liaison.VERSIONS,
}

_ACTIVE_TOML = Path(__file__).with_name("active.toml")


def _load_active() -> dict[str, str]:
    """Read the active prompt version per agent from `active.toml`.

    Editing that file is the supported way to switch versions — no code change.
    If the file is missing or malformed, every agent falls back to "v1".
    """
    if not _ACTIVE_TOML.exists():
        return {name: "v1" for name in PROMPTS}
    try:
        data = tomllib.loads(_ACTIVE_TOML.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        print(f"[prompts] active.toml is malformed ({exc}); using v1.", file=sys.stderr)
        return {name: "v1" for name in PROMPTS}
    chosen = data.get("active", {})
    return {name: chosen.get(name, "v1") for name in PROMPTS}


# The active prompt version per agent, loaded from active.toml at import time.
ACTIVE: dict[str, str] = _load_active()


def get_prompt(name: str) -> str:
    """Return the active system prompt for an agent by name.

    Raises KeyError with a clear message if the agent or version is missing,
    so a typo fails loudly at startup rather than sending an empty prompt.
    """
    try:
        versions = PROMPTS[name]
    except KeyError:
        raise KeyError(
            f"No prompts registered for agent {name!r}. Known: {sorted(PROMPTS)}"
        ) from None
    version = ACTIVE.get(name, "v1")
    try:
        return versions[version]
    except KeyError:
        raise KeyError(
            f"Agent {name!r} has no prompt version {version!r}. "
            f"Available: {sorted(versions)}"
        ) from None


__all__ = ["PROMPTS", "ACTIVE", "build_patient_context", "with_context", "get_prompt"]
