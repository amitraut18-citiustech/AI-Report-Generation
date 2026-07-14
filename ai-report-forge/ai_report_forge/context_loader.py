import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from .config import settings

log = logging.getLogger(__name__)


@dataclass
class ReportEntry:
    report_key: str
    title: str
    thought_content: str
    template_file: str
    fields: list[dict]
    parameters: list[dict]


@dataclass
class SchemaContext:
    raw: dict = field(default_factory=dict)
    tables: list[dict] = field(default_factory=list)


@dataclass
class PhiMarkers:
    raw: dict = field(default_factory=dict)
    columns: list[dict] = field(default_factory=list)

    def strategies_for_table(self, table: str) -> dict[str, str]:
        return {
            c["column"]: c["strategy"]
            for c in self.columns
            if c["table"] == table
        }


@dataclass
class AppContext:
    reports: dict[str, ReportEntry] = field(default_factory=dict)
    schema: SchemaContext = field(default_factory=SchemaContext)
    phi: PhiMarkers = field(default_factory=PhiMarkers)

    def report_summaries_text(self) -> str:
        if not self.reports:
            return "(no reports loaded)"
        parts = []
        for key, entry in self.reports.items():
            field_names = ", ".join(f["Field"] for f in entry.fields if "Field" in f) or "N/A"
            param_info = ", ".join(
                f"{p.get('Name', '?')} ({p.get('Type', '?')})"
                for p in entry.parameters if p.get("User-facing?", "").lower().startswith("yes")
            ) or "none"
            source_line = ""
            for line in entry.thought_content.splitlines():
                if line.strip().startswith("- **Description:**"):
                    source_line = line.split("**Description:**", 1)[1].strip()
                    break
            parts.append(
                f"### {key}\n"
                f"- Title: {entry.title}\n"
                f"- Template: {entry.template_file}\n"
                f"- Description: {source_line or entry.title}\n"
                f"- Fields: {field_names}\n"
                f"- User parameters: {param_info}"
            )
        return "\n\n".join(parts)

    def schema_text(self) -> str:
        if not self.schema.tables:
            return "(no schema loaded)"
        parts = []
        for t in self.schema.tables:
            if not t.get("reportable", True):
                continue
            col_details = []
            nav_details = []
            for c in t.get("columns", []):
                col_details.append(f"  - {c['name']} ({c.get('type', '?')}): {c.get('description', '')}")
                nav = c.get("navigation")
                if nav:
                    display = ", ".join(nav.get("displayFields", []))
                    nav_details.append(
                        f"  - {c['name']} → joins {nav['table']} "
                        f"(nav: {nav.get('navProperty', '?')}, display fields: {display})"
                    )
            section = (
                f"### {t['name']}\n"
                f"{t.get('description', '')}\n"
                f"Filterable fields:\n" + "\n".join(col_details)
            )
            if nav_details:
                section += "\nRelationships (use these for cross-table filters):\n" + "\n".join(nav_details)
            parts.append(section)
        return "\n\n".join(parts)


_KEY_RE = re.compile(r"\*\*Report key:\*\*\s*(\S+)")
_TITLE_RE = re.compile(r"^#\s+Report Thought:\s*(.+)", re.MULTILINE)


def _parse_thought_file(path: Path) -> ReportEntry | None:
    text = path.read_text(encoding="utf-8")

    key_match = _KEY_RE.search(text)
    report_key = key_match.group(1) if key_match else path.stem.replace(".thought", "")

    title_match = _TITLE_RE.search(text)
    title = title_match.group(1).strip() if title_match else report_key

    template_file = f"{report_key}.html"

    fields = _extract_table_rows(text, "Fields")
    parameters = _extract_table_rows(text, "Parameters")

    return ReportEntry(
        report_key=report_key,
        title=title,
        thought_content=text,
        template_file=template_file,
        fields=fields,
        parameters=parameters,
    )


def _extract_table_rows(text: str, section_header: str) -> list[dict]:
    pattern = re.compile(
        rf"\|\s*{section_header}\b.*?\n"
        r"(\|.*\n)*",
        re.IGNORECASE,
    )
    rows = []
    in_section = False
    headers = []
    for line in text.splitlines():
        stripped = line.strip()
        if not in_section:
            if stripped.startswith("|") and section_header.lower() in stripped.lower():
                cells = [c.strip() for c in stripped.split("|")[1:-1]]
                headers = cells
                in_section = True
            continue
        if stripped.startswith("|"):
            if all(c.strip().replace("-", "") == "" for c in stripped.split("|")[1:-1]):
                continue
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            if len(cells) == len(headers):
                rows.append(dict(zip(headers, cells)))
            else:
                rows.append({"raw": stripped})
        else:
            break
    return rows


def load_context() -> AppContext:
    ctx = AppContext()

    thoughts_dir = settings.resolve(settings.report_thoughts_path)
    if thoughts_dir.is_dir():
        for path in sorted(thoughts_dir.glob("*.thought.md")):
            entry = _parse_thought_file(path)
            if entry:
                ctx.reports[entry.report_key] = entry
                log.info("Loaded report thought: %s", entry.report_key)
    else:
        log.warning("ReportThoughts directory not found: %s", thoughts_dir)

    # Schema mapping and PHI markers are safety-critical: without the PHI
    # markers the anonymizer is a no-op and raw PHI would reach the LLMs.
    # Refuse to start rather than degrade silently.
    schema_path = settings.resolve(settings.schema_mapping_path)
    if not schema_path.is_file():
        raise RuntimeError(f"Schema mapping not found: {schema_path}")
    data = json.loads(schema_path.read_text(encoding="utf-8"))
    ctx.schema = SchemaContext(raw=data, tables=data.get("tables", []))
    log.info("Loaded schema mapping: %d tables", len(ctx.schema.tables))

    phi_path = settings.resolve(settings.phi_markers_path)
    if not phi_path.is_file():
        raise RuntimeError(f"PHI markers not found: {phi_path}")
    data = json.loads(phi_path.read_text(encoding="utf-8"))
    columns = data.get("phiColumns", [])
    if not columns:
        raise RuntimeError(f"PHI markers file is empty: {phi_path}")
    ctx.phi = PhiMarkers(raw=data, columns=columns)
    log.info("Loaded PHI markers: %d columns", len(ctx.phi.columns))

    return ctx
