"""Parse LifeLabs lab-result PDFs into structured observations.

LifeLabs (like most Canadian labs) lays results out as tables with columns such
as ``Test | Result | Flag | Reference Range | Units`` under section headers
(Hematology, Chemistry, ...). Layouts differ between report types and change
over time, so this parser is intentionally defensive:

  * The full extracted text is always returned (``raw_text``) so nothing is lost
    even when structured extraction is partial.
  * Table rows are mapped to observations on a best-effort basis.
  * If no observations are recognised, the caller should mark the report
    ``needs_review`` and keep the raw document + text for manual/LLM follow-up.

I/O (opening the PDF) is isolated in ``extract_text_and_tables`` so the row
mapping in ``observations_from_tables`` stays a pure function that is unit-tested
without a real PDF. A future LLM fallback can take ``raw_text`` plus the local
clinical model (``settings.llm_model_clinical``) to fill gaps.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from datetime import datetime

# A "table" as returned by pdfplumber: rows of cells, cells may be None.
Cell = str | None
Row = list[Cell]
Table = list[Row]


@dataclass
class ParsedObservation:
    """One analyte/result line within a report (a 'related row')."""

    test_name: str
    value_text: str | None = None
    value_num: float | None = None
    unit: str | None = None
    reference_range: str | None = None
    flag: str | None = None  # "H" | "L" | "A" | "C" | None (normal)
    category: str | None = None  # section header, e.g. "Hematology"


@dataclass
class ParsedLabReport:
    """Everything pulled out of a single results document."""

    raw_text: str
    observations: list[ParsedObservation] = field(default_factory=list)
    lab_name: str | None = "LifeLabs"
    ordering_provider: str | None = None
    collected_at: datetime | None = None
    reported_at: datetime | None = None


class PdfParseError(RuntimeError):
    """Raised when the document cannot be opened/read as a PDF."""


# ---------------------------------------------------------------------------
# I/O boundary
# ---------------------------------------------------------------------------


def extract_text_and_tables(data: bytes) -> tuple[str, list[Table]]:
    """Open a PDF and return (full_text, [tables]). Isolated for testability."""
    try:
        import pdfplumber  # local import: keeps app boot/import light
    except ModuleNotFoundError as exc:  # pragma: no cover - env-dependent
        raise PdfParseError(
            "pdfplumber is required to parse lab PDFs. Install with "
            "`pip install pdfplumber`."
        ) from exc

    texts: list[str] = []
    tables: list[Table] = []
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                texts.append(page.extract_text() or "")
                for table in page.extract_tables() or []:
                    tables.append(table)
    except PdfParseError:
        raise
    except Exception as exc:  # pdfminer raises a variety of errors
        raise PdfParseError(f"could not read PDF: {exc}") from exc

    return "\n".join(texts), tables


def parse_lab_pdf(data: bytes) -> ParsedLabReport:
    """Parse a LifeLabs results PDF into a :class:`ParsedLabReport`."""
    raw_text, tables = extract_text_and_tables(data)
    observations = observations_from_tables(tables)
    meta = metadata_from_text(raw_text)
    return ParsedLabReport(
        raw_text=raw_text,
        observations=observations,
        ordering_provider=meta.get("ordering_provider"),
        collected_at=meta.get("collected_at"),
        reported_at=meta.get("reported_at"),
    )


# ---------------------------------------------------------------------------
# Pure parsing logic (unit-tested directly)
# ---------------------------------------------------------------------------

_HEADER_HINTS = {
    "name": ("test", "analyte", "name", "examination"),
    "result": ("result", "value"),
    "flag": ("flag", "abn"),
    "reference_range": ("reference", "range", "interval"),
    "unit": ("unit", "units"),
}
_FLAG_TOKENS = {
    "H": "H", "HH": "H", "HIGH": "H",
    "L": "L", "LL": "L", "LOW": "L",
    "A": "A", "ABN": "A", "ABNORMAL": "A",
    "C": "C", "CRIT": "C", "CRITICAL": "C",
}
_NUM_RE = re.compile(r"-?\d+(?:[.,]\d+)?")


def _clean(cell: Cell) -> str:
    """Collapse whitespace/newlines inside a cell to a single trimmed string."""
    if cell is None:
        return ""
    return re.sub(r"\s+", " ", str(cell)).strip()


def _parse_float(text: str) -> float | None:
    match = _NUM_RE.search(text.replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _split_value_flag(result: str) -> tuple[str, str | None]:
    """Separate a trailing flag token from a result, e.g. '5.4 (H)' -> ('5.4','H')."""
    if not result:
        return result, None
    stripped = result.strip()
    # Trailing parenthesised or bare flag token.
    m = re.search(r"[\s(]*([A-Za-z]{1,4})\)?\s*$", stripped)
    if m:
        token = m.group(1).upper()
        if token in _FLAG_TOKENS and _NUM_RE.search(stripped[: m.start()]):
            return stripped[: m.start()].strip(), _FLAG_TOKENS[token]
    return stripped, None


def _detect_columns(header: Row) -> dict[str, int] | None:
    """Map logical columns -> index using header hints. None if not a header."""
    cleaned = [_clean(c).lower() for c in header]
    mapping: dict[str, int] = {}
    for key, hints in _HEADER_HINTS.items():
        for idx, cell in enumerate(cleaned):
            if cell and any(h in cell for h in hints):
                mapping.setdefault(key, idx)
                break
    # A real header must at least identify where the test name and result live.
    if "name" in mapping and "result" in mapping:
        return mapping
    return None


def _non_empty(row: Row) -> list[str]:
    return [c for c in (_clean(x) for x in row) if c]


def observations_from_tables(
    tables: list[Table],
    default_category: str | None = None,
) -> list[ParsedObservation]:
    """Map extracted tables to observations. Pure function (no I/O)."""
    observations: list[ParsedObservation] = []

    for table in tables:
        if not table:
            continue
        columns: dict[str, int] | None = None
        category = default_category

        for row in table:
            cells = _non_empty(row)
            if not cells:
                continue

            # A lone cell is a section header (category) like "Hematology".
            if len(cells) == 1:
                header = cells[0]
                if not _NUM_RE.search(header) and len(header) <= 40:
                    category = header
                continue

            # First multi-cell row that looks like a header sets the columns.
            detected = _detect_columns(row)
            if detected is not None:
                columns = detected
                continue

            obs = _row_to_observation(row, columns, category)
            if obs is not None:
                observations.append(obs)

    return observations


def _row_to_observation(
    row: Row,
    columns: dict[str, int] | None,
    category: str | None,
) -> ParsedObservation | None:
    cleaned = [_clean(c) for c in row]

    if columns is not None:
        name = _at(cleaned, columns.get("name"))
        result = _at(cleaned, columns.get("result"))
        unit = _at(cleaned, columns.get("unit")) or None
        ref = _at(cleaned, columns.get("reference_range")) or None
        flag = _at(cleaned, columns.get("flag")) or None
    else:
        # Positional fallback: name, result, [unit], [reference range].
        non_empty = _non_empty(row)
        if len(non_empty) < 2:
            return None
        name, result = non_empty[0], non_empty[1]
        unit = non_empty[2] if len(non_empty) > 2 else None
        ref = non_empty[3] if len(non_empty) > 3 else None
        flag = None

    if not name or not result:
        return None

    value_text, parsed_flag = _split_value_flag(result)
    return ParsedObservation(
        test_name=name,
        value_text=value_text or None,
        value_num=_parse_float(value_text),
        unit=unit,
        reference_range=ref,
        flag=(flag.upper() if flag else None) or parsed_flag,
        category=category,
    )


def _at(cells: list[str], idx: int | None) -> str:
    if idx is None or idx >= len(cells):
        return ""
    return cells[idx]


# ---------------------------------------------------------------------------
# Metadata (best-effort, regex over the full text)
# ---------------------------------------------------------------------------

_DATE_FORMATS = (
    "%Y-%m-%d", "%Y/%m/%d", "%d-%b-%Y", "%d %b %Y", "%b %d, %Y", "%b %d %Y",
    "%d/%m/%Y", "%m/%d/%Y",
)
_DATE_PATTERN = (
    r"(\d{4}[-/]\d{1,2}[-/]\d{1,2}"
    r"|\d{1,2}[-/ ][A-Za-z]{3}[-/ ]\d{4}"
    r"|[A-Za-z]{3}\.?\s+\d{1,2},?\s+\d{4})"
)


def _parse_date(text: str) -> datetime | None:
    candidate = text.strip().replace(".", "")
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(candidate, fmt)
        except ValueError:
            continue
    return None


def _find_date(text: str, labels: tuple[str, ...]) -> datetime | None:
    for label in labels:
        m = re.search(label + r"\s*[:\-]?\s*" + _DATE_PATTERN, text, re.IGNORECASE)
        if m:
            parsed = _parse_date(m.group(1))
            if parsed:
                return parsed
    return None


def metadata_from_text(text: str) -> dict[str, object]:
    meta: dict[str, object] = {}
    collected = _find_date(text, ("collection date", "collected", "date collected", "collection"))
    reported = _find_date(text, ("report date", "reported", "date reported", "released", "result date"))
    if collected:
        meta["collected_at"] = collected
    if reported:
        meta["reported_at"] = reported

    m = re.search(
        r"(?:ordering\s+(?:physician|provider)|physician|practitioner|doctor)"
        r"\s*[:\-]?\s*([A-Z][A-Za-z.,'\- ]{2,60})",
        text,
        re.IGNORECASE,
    )
    if m:
        meta["ordering_provider"] = m.group(1).strip()
    return meta
