import logging
from dataclasses import dataclass, field
from datetime import date, datetime

from .context_loader import PhiMarkers

log = logging.getLogger(__name__)


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
                    anon_value = self._apply_strategy(strategy, col, value, mapping)
                    new_row[col] = anon_value
                else:
                    new_row[col] = value
            anonymized.append(new_row)

        return AnonymizationResult(anonymized_rows=anonymized, mapping=mapping)

    def _apply_strategy(
        self, strategy: str, column: str, value, mapping: dict
    ) -> str:
        if strategy == "pseudonymize":
            return self._pseudonymize(column, value, mapping)
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

    def _pseudonymize(self, column: str, value, mapping: dict) -> str:
        str_val = str(value)
        key = f"pseudo:{column}"
        if key not in mapping:
            mapping[key] = {}
        if str_val in mapping[key]:
            return mapping[key][str_val]

        self._counters.setdefault(column, 0)
        self._counters[column] += 1
        pseudonym = f"Patient_{self._counters[column]:03d}"
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
    result = narrative
    for _strategy_key, value_map in mapping.items():
        for original, pseudonym in value_map.items():
            result = result.replace(pseudonym, original)
    return result
