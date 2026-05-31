"""Noise & sound filter — scrub raw input before it reaches any LLM.

The patient-facing text usually arrives from on-device speech-to-text (Whisper on
the watch / always-on tier). ASR output carries artifacts that are not speech:
non-speech annotations (``[BLANK_AUDIO]``, ``(coughing)``, ``[Music]``), elongated
words (``"noooo"``), filler tokens (``"uh"``, ``"umm"``), stray control characters,
and runaway whitespace. Feeding that verbatim to the model wastes context and
degrades both routing and the downstream anomaly check.

This module does **one deterministic pass, no model calls**: it strips the noise,
normalises the text, and reports whether anything intelligible survived. Every
downstream agent sees the cleaned text; the gate (``backend.agents.anomaly``) uses
the ``is_noise`` flag to short-circuit a turn that was pure noise.

It is intentionally conservative — it only removes things that are unambiguously
non-speech, so it can never turn a real patient utterance into a blocked turn.
"""

from __future__ import annotations

import re
import string
import unicodedata
from dataclasses import dataclass, field

# Whisper / ASR wrap non-speech annotations in square brackets:
#   [BLANK_AUDIO]  [ Silence ]  [Music]  [inaudible]  [noise]
_BRACKET_NOISE_RE = re.compile(r"\[[^\]]*\]")

# Parenthetical sound annotations: (coughing) (sighs) (background noise).
# Only stripped when the WHOLE parenthetical is a known non-speech sound — never
# general parenthetical speech the patient might actually have said.
_SOUND_WORDS = (
    "cough",
    "coughs",
    "coughing",
    "sigh",
    "sighs",
    "sighing",
    "breathing",
    "wheezing",
    "music",
    "silence",
    "noise",
    "static",
    "inaudible",
    "unintelligible",
    "indistinct",
    "background noise",
    "laughs",
    "laughing",
    "crying",
    "sobbing",
    "muffled",
    "beeping",
    "wind",
    "footsteps",
    "clattering",
)
_PAREN_NOISE_RE = re.compile(
    r"\(\s*(?:" + "|".join(re.escape(w) for w in _SOUND_WORDS) + r")\s*\)",
    re.IGNORECASE,
)

# Control / non-printable characters (tab + newline are handled as whitespace).
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# A non-space character repeated 3+ times is an elongation/mash: collapse to 2 so
# meaning survives ("noooo" -> "noo", "!!!" -> "!!") without distorting real words.
# (Whitespace runs are handled separately by `_WS_RE`.)
_ELONGATION_RE = re.compile(r"(\S)\1{2,}")

# Standalone disfluency / filler tokens dropped only when real words remain.
_FILLERS = frozenset(
    {"uh", "uhh", "uhm", "um", "umm", "erm", "err", "hmm", "mm", "mmm", "ah", "eh", "uhhuh", "mhm"}
)

_WORD_RE = re.compile(r"\S+")
_WS_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class FilteredInput:
    """Result of one cleaning pass."""

    text: str  # cleaned text — what the LLM should see
    original: str  # raw input as received
    is_noise: bool  # True when nothing intelligible remained
    removed: list[str] = field(default_factory=list)  # notes for observability


def _strip_filler(text: str) -> tuple[str, bool]:
    """Drop standalone filler words, but only if a real word survives.

    A message that is *entirely* filler (e.g. "hmm") is left untouched — that may
    be a meaningful response, so we let the anomaly gate judge it rather than
    blanking it here.
    """
    words = _WORD_RE.findall(text)
    kept = [w for w in words if w.lower().strip(string.punctuation) not in _FILLERS]
    if kept and len(kept) != len(words):
        return " ".join(kept), True
    return text, False


def clean_input(raw: str | None) -> FilteredInput:
    """Scrub one raw utterance and report whether anything intelligible survived."""
    original = raw or ""
    removed: list[str] = []

    # Unicode-normalise so look-alike/full-width chars don't slip past the filters.
    text = unicodedata.normalize("NFKC", original)

    if _CONTROL_RE.search(text):
        text = _CONTROL_RE.sub(" ", text)
        removed.append("control characters")

    if _BRACKET_NOISE_RE.search(text):
        text = _BRACKET_NOISE_RE.sub(" ", text)
        removed.append("bracketed non-speech markers")

    if _PAREN_NOISE_RE.search(text):
        text = _PAREN_NOISE_RE.sub(" ", text)
        removed.append("sound annotations")

    if _ELONGATION_RE.search(text):
        text = _ELONGATION_RE.sub(r"\1\1", text)
        removed.append("elongated characters")

    text, dropped_filler = _strip_filler(text)
    if dropped_filler:
        removed.append("filler words")

    text = _WS_RE.sub(" ", text).strip()

    # Noise = nothing alphanumeric survived (e.g. input was only "[BLANK_AUDIO]"
    # or stray punctuation). The gate turns this into a gentle "didn't catch that".
    is_noise = not any(ch.isalnum() for ch in text)

    return FilteredInput(text=text, original=original, is_noise=is_noise, removed=removed)
