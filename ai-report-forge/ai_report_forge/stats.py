"""Deterministic statistics computed over the full (anonymized) result set.

Small local LLMs miscount rows, so instead of asking the model to count, we
compute the numbers in Python and hand them to the model as verified facts.
The narrative and chart must be built from these numbers, never from the
model's own counting.
"""
from collections import Counter

# A column is treated as categorical when it has few distinct values and is
# not effectively unique per row.
MAX_CATEGORIES = 8

# Columns that are identifiers/pseudonyms rather than analyzable categories.
_SKIP_TOKENS = ("id", "mrn", "npi", "email", "phone", "contact")


def compute_stats(rows: list[dict]) -> str:
    """Return a plain-text block of verified statistics for the LLM prompt."""
    if not rows:
        return "Total rows: 0"

    lines = [f"Total rows: {len(rows)}"]

    for col in rows[0].keys():
        col_lower = col.lower()
        if any(tok in col_lower for tok in _SKIP_TOKENS):
            continue

        values = [r.get(col) for r in rows]

        # Date-like columns: report the range.
        if "date" in col_lower:
            dates = sorted(str(v) for v in values if v is not None)
            if dates:
                lines.append(f"{col}: earliest {dates[0][:10]}, latest {dates[-1][:10]}")
            continue

        # Categorical breakdowns for low-cardinality string/bool columns.
        strvals = [str(v) for v in values if v is not None and isinstance(v, (str, bool))]
        if not strvals:
            continue
        counts = Counter(strvals)
        if len(counts) > MAX_CATEGORIES or len(counts) == len(rows) > 1:
            continue
        if counts.get("[REDACTED]", 0) == len(strvals):
            continue
        breakdown = ", ".join(f"{val}: {n}" for val, n in counts.most_common())
        lines.append(f"{col} breakdown: {breakdown}")

    return "\n".join(lines)
