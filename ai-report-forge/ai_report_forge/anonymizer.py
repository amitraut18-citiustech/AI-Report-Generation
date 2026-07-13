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
    "providerFirstName": "Provider",
    "providerLastName": "Provider",
}

# Columns on the Providers table always get the Provider prefix.
_PROVIDER_TABLE_COLUMNS = {"FirstName", "LastName", "NPI"}


def _resolve_prefix(column: str, table: str) -> str:
    """Determine the pseudonym prefix based on column name and source table."""
    col_lower = column.lower()
    for key, prefix in _COLUMN_PREFIX_MAP.items():
        if key.lower() == col_lower:
            return prefix
    if table == "Providers" and column in _PROVIDER_TABLE_COLUMNS:
        return "Provider"
    return "Patient"


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
        if not strategies:
            return AnonymizationResult(anonymized_rows=rows)

        self._counters.clear()
        mapping: dict[str, dict[str, str]] = {}
        anonymized = []

        for row in rows:
            new_row = {}
            for col, value in row.items():
                strategy = strategies.get(col)
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
        result = pattern.sub(original, result)
    return result
