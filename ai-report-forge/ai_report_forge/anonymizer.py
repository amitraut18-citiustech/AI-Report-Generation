import logging
import re as _re
from dataclasses import dataclass, field
from datetime import date, datetime

from .context_loader import PhiMarkers

log = logging.getLogger(__name__)

# Maps column names (case-insensitive lookup) to pseudonym prefixes so that
# patient names and provider names produce distinguishable tokens.
_COLUMN_PREFIX_MAP: dict[str, str] = {
    "providername": "Provider",
    "providerfirstname": "Provider",
    "providerlastname": "Provider",
}

# Columns on the Providers table always get the Provider prefix (compared
# case-insensitively).
_PROVIDER_TABLE_COLUMNS = {"firstname", "lastname", "npi"}

# Safety net: columns that look like direct identifiers are anonymized even
# when no explicit strategy is configured for them. The .NET client sends
# camelCase keys and viewmodels grow new columns over time, so relying only on
# phi-markers.json being complete is not safe for cloud LLM calls.
# Matches whole column names only, so e.g. "facilityName" is NOT caught.
_FALLBACK_PSEUDONYMIZE_RE = _re.compile(
    r"^(first|last|patient|provider|full)name$", _re.IGNORECASE
)
_FALLBACK_REDACT_RE = _re.compile(
    r"^(email(address)?|phone(number)?|contact(number)?|mrn|npi|ssn|address(line\d*)?)$",
    _re.IGNORECASE,
)
_FALLBACK_AGE_RANGE_RE = _re.compile(
    r"^(dateofbirth|dob|birthdate)$", _re.IGNORECASE
)


def _resolve_prefix(column: str, table: str) -> str:
    """Determine the pseudonym prefix based on column name and source table."""
    col_lower = column.lower()
    prefix = _COLUMN_PREFIX_MAP.get(col_lower)
    if prefix:
        return prefix
    if table == "Providers" and col_lower in _PROVIDER_TABLE_COLUMNS:
        return "Provider"
    return "Patient"


def _fallback_strategy(column: str) -> str | None:
    if _FALLBACK_PSEUDONYMIZE_RE.match(column):
        return "pseudonymize"
    if _FALLBACK_REDACT_RE.match(column):
        return "redact"
    if _FALLBACK_AGE_RANGE_RE.match(column):
        return "age_range"
    return None


@dataclass
class AnonymizationResult:
    anonymized_rows: list[dict]
    mapping: dict[str, dict[str, str]] = field(default_factory=dict)


class Anonymizer:
    def __init__(self, phi_markers: PhiMarkers):
        self._phi = phi_markers
        self._counters: dict[str, int] = {}

    def anonymize(self, rows: list[dict], table: str) -> AnonymizationResult:
        strategies = self._phi.strategies_for_table(table)
        vm_strategies = self._phi.strategies_for_table("_viewmodel")
        strategies = {**strategies, **vm_strategies}
        # Case-insensitive lookup: the .NET client serializes row keys in
        # camelCase while phi-markers.json uses PascalCase.
        strategies_ci = {col.lower(): strat for col, strat in strategies.items()}

        self._counters.clear()
        mapping: dict[str, dict[str, str]] = {}
        anonymized = []

        for row in rows:
            new_row = {}
            for col, value in row.items():
                strategy = strategies_ci.get(col.lower()) or _fallback_strategy(col)
                if strategy and value is not None:
                    anon_value = self._apply_strategy(
                        strategy, col, value, mapping, table
                    )
                    new_row[col] = anon_value
                else:
                    new_row[col] = value
            anonymized.append(new_row)

        return AnonymizationResult(anonymized_rows=anonymized, mapping=mapping)

    def _apply_strategy(
        self, strategy: str, column: str, value, mapping: dict, table: str = ""
    ) -> str:
        if strategy == "pseudonymize":
            return self._pseudonymize(column, value, mapping, table)
        elif strategy == "age_range":
            return self._to_age_range(value)
        elif strategy == "sequential_id":
            return self._sequential_id(column, value, mapping)
        elif strategy == "redact":
            return "[REDACTED]"
        elif strategy == "region_only":
            return self._region_only(value)
        else:
            log.warning("Unknown PHI strategy '%s' for column '%s', redacting", strategy, column)
            return "[REDACTED]"

    def _pseudonymize(
        self, column: str, value, mapping: dict, table: str = ""
    ) -> str:
        str_val = str(value)
        prefix = _resolve_prefix(column, table)
        key = f"pseudo:{prefix}:{column}"
        if key not in mapping:
            mapping[key] = {}
        if str_val in mapping[key]:
            return mapping[key][str_val]

        counter_key = f"pseudo_{prefix}"
        self._counters.setdefault(counter_key, 0)
        self._counters[counter_key] += 1
        pseudonym = f"{prefix}_{self._counters[counter_key]:03d}"
        mapping[key][str_val] = pseudonym
        return pseudonym

    def _to_age_range(self, value) -> str:
        try:
            if isinstance(value, str):
                dob = datetime.fromisoformat(value).date()
            elif isinstance(value, datetime):
                dob = value.date()
            elif isinstance(value, date):
                dob = value
            else:
                return "[REDACTED]"

            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            decade_start = (age // 10) * 10
            return f"{decade_start}-{decade_start + 9}"
        except (ValueError, TypeError):
            return "[REDACTED]"

    def _sequential_id(self, column: str, value, mapping: dict) -> str:
        str_val = str(value)
        key = f"seq:{column}"
        if key not in mapping:
            mapping[key] = {}
        if str_val in mapping[key]:
            return mapping[key][str_val]

        self._counters.setdefault(f"seq_{column}", 0)
        self._counters[f"seq_{column}"] += 1
        seq = f"P_{self._counters[f'seq_{column}']:03d}"
        mapping[key][str_val] = seq
        return seq

    def _region_only(self, value) -> str:
        str_val = str(value).strip()
        if len(str_val) == 2 and str_val.isalpha():
            return str_val.upper()
        parts = [p.strip() for p in str_val.replace(",", " ").split()]
        for part in reversed(parts):
            if len(part) == 2 and part.isalpha():
                return part.upper()
        return "[REGION]"


def remap_narrative(narrative: str, mapping: dict) -> str:
    """Replace pseudonym tokens in a narrative with original values.

    Uses word-boundary-aware matching on both sides to avoid partial
    replacements (e.g. 'XPatient_001' or 'Patient_001points').
    """
    replacements: list[tuple[str, str]] = []
    for _strategy_key, value_map in mapping.items():
        for original, pseudonym in value_map.items():
            replacements.append((pseudonym, original))

    # Sort longest first to avoid partial matches (e.g. Provider_010 before Provider_01).
    replacements.sort(key=lambda pair: len(pair[0]), reverse=True)

    result = narrative
    for pseudonym, original in replacements:
        pattern = _re.compile(r"(?<![_\w])" + _re.escape(pseudonym) + r"(?![_\w])")
        # Callable replacement so backslashes/group refs in the original
        # value are inserted literally instead of being interpreted by re.sub.
        result = pattern.sub(lambda _m, o=original: o, result)
    return result


def scrub_text(text: str, mapping: dict) -> str:
    """Replace known PHI values appearing in free text with their pseudonyms.

    Used to sanitize the user's question before it is embedded in an LLM
    prompt (e.g. "show me John Smith's visits" -> "show me Patient_001
    Patient_002's visits"). Only values already present in the anonymization
    mapping are replaced; matching is case-insensitive and word-bounded.
    Values shorter than 3 characters are skipped to avoid mangling the text.
    """
    replacements: list[tuple[str, str]] = []
    for _strategy_key, value_map in mapping.items():
        for original, pseudonym in value_map.items():
            if len(str(original)) >= 3:
                replacements.append((str(original), pseudonym))

    replacements.sort(key=lambda pair: len(pair[0]), reverse=True)

    result = text
    for original, pseudonym in replacements:
        pattern = _re.compile(
            r"(?<![\w])" + _re.escape(original) + r"(?![\w])", _re.IGNORECASE
        )
        result = pattern.sub(lambda _m, p=pseudonym: p, result)
    return result
