# Demo Script — AI Report Forge (~3 minutes)

**The pitch (10s):** Legacy SSRS/Crystal reporting means every report change is an IT
ticket. AI Report Forge migrates the reports once with a Claude Code plugin, then lets
business users self-serve with plain-English questions — with PHI provably protected and
every AI interaction disclosed.

**Setup before recording/presenting:** all 4 services running (`docs/quick_start.md`),
`ANTHROPIC_API_KEY` set in `ai-report-forge/.env`, brain freshly restarted (clean Prompt
Log), browser at http://localhost:5282. All prompts below were verified against the live
app on 2026-07-14.

---

## Act 1 — Natural-language reporting, fully local (45s)

1. Land on **AI Reports**. Type: **`Show me patients at Austin General`** → click
   **Ask Local AI**.
2. Point out, top to bottom:
   - grey banner: *answered by the local model — no data left this machine*
   - AI-applied filter badges: the model turned "Austin General" into
     `Facilities.Name contains Austin General` — it knew from the schema map this is a
     facility, not a patient name
   - the table: **3 patients**, not all 8 — filtering happened in the database
   - the **AI Summary** card: a narrative of the filtered results

> "No SQL, no parameter form. The local model decoded the question in ~3 seconds, the
> existing .NET data layer did the querying — the LLM never touches the database."

## Act 2 — Cloud choice and automatic fallback (45s)

3. Type: **`Show female patients at Austin General Hospital`** → click **Ask Claude**.
   - amber banner: *answered directly by the Claude API*; 1 row (Ava Patel)
   - "Cloud is a user choice — and it's always labeled."
4. Type: **`which sheet lists the folks who got cells from a donor other than themselves`**
   → click **Ask Local AI**.
   - amber **Claude (fallback)** banner: the phrasing was too colloquial for the small
     local model — it failed, and the system automatically fell back to Claude, which
     decoded it correctly to `DonorType = Allogeneic` (8 transplant events).
   - *(If the local model happens to decode it — it occasionally does — re-ask once, or
     narrate that the local model handled it and move on.)*

## Act 3 — Security: fail closed (30s)

5. Type: **`show patient with MRN-00003`** → click **Ask Local AI**.
   - the MRN filter badge appears **struck through** (blocked — protected field)
   - the report shows **zero rows** with an explanation instead of dumping the table

> "Probing a protected field never returns more data than an allowed query. The AI's
> filters are re-validated by the .NET layer against a per-table allowlist — the model
> proposes, the application enforces."

## Act 4 — Prompt Log: the PHI proof (45s)

6. Click **Prompt Log** in the navbar. Newest question is expanded; older asks are
   collapsed groups.
   - point at a **routing chain**: `Local LLM ✗ → Claude — fallback ✓` — the fallback
     from Act 2, recorded.
7. Expand the Act-1 group, scroll to its **Summarize** card:
   - **left panel (red): real data — never sent** · **right panel (green): what the LLM
     received** — `Patient_001`, age ranges, `[REDACTED]`

> "This is what was *actually sent* to each model. Names became pseudonyms, dates of birth
> became age ranges, contact info was redacted — and the real names were restored locally
> after the response. The same anonymization applies to the local model and to Claude."

## Act 5 — The migration story + legacy parity (30s)

8. Briefly show the pipeline artifacts (pre-opened tabs/editor):
   `Reports/PatientReport.rdl` → `ReportThoughts/patient.thought.md` (human-reviewed) →
   `HTMLReportsFolder/patient.html`.
   > "This is Phase 1: a Claude Code plugin read the legacy RDL, wrote a reviewable
   > analysis, and generated the HTML report — a developer approves the analysis before
   > any code is generated."
9. Click **Classic Reports (SSRS)** → select Patient Report → Generate.
   > "The original RDL still renders side-by-side for parity — same data layer feeding
   > both. That's the migration: same numbers, new engine, no report server."

---

## Key decisions to name if asked

- **Local-first**: default model runs on-device (qwen2.5:3b via Ollama); cloud is explicit
  or a disclosed fallback.
- **LLM as untrusted advisor**: it proposes query specs; the .NET layer enforces
  allowlists, signs the spec, and fails closed.
- **Human checkpoint at build time**: thought files reviewed before code generation.
- **Honest failures everywhere**: UNKNOWN for off-topic, 502 over fabricated summaries,
  struck-through badges for blocked filters.

## Final artifacts to show as evidence

- Filtered HTML report with AI Summary (Act 1) · Prompt Log before/after panels (Act 4)
- `python -m pytest tests/ -v` → **53 passed**
- Submission docs: `presentation/dod-evidence.md`, `presentation/compliance-note.md`
