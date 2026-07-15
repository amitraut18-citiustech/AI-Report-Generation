# Safety & Compliance Note — AI Report Forge

**Scope:** responsible-AI safeguards, PHI/PII handling, human-in-the-loop checkpoints, and
known risks for the AI-Driven Reporting submission. Full technical detail:
`docs/architecture.md` §5–6.

## 1. No real PHI anywhere

- The database is a **synthetic dataset** auto-seeded on startup (8 fictional patients,
  3 facilities, 5 providers). No real patient data exists in the repo, the demo, or the
  evidence pack.
- The system is nonetheless **built as if the data were real** — every safeguard below is
  active in the demo.

## 2. PHI protection pipeline (defense in depth)

Data rows never reach any LLM in the clear — local or cloud:

1. **Anonymization before every summarization call** — per-column strategies from
   `DataSchemaMapping/phi-markers.json`: names → `Patient_001`/`Provider_001` pseudonyms,
   dates of birth → age ranges, contact fields/MRN → `[REDACTED]`, locations → state only.
2. **Question scrubbing** — known PHI values in the user's question are replaced with
   pseudonyms before summarization prompts are built.
3. **Local re-mapping** — real names are restored only after the LLM response returns; the
   pseudonym↔value mapping never leaves the server process.
4. **Deny-by-default safety net** — columns that *look* like identifiers (`*name`, `email`,
   `phone`, `mrn`, `ssn`, `dob`, …) are anonymized even if missing from the marker file;
   unknown strategies redact; column matching is case-insensitive.
5. **Fail-hard startup** — the brain refuses to boot if the schema mapping or PHI markers
   are missing or empty. No silent unprotected mode.

**Verifiable live:** the app's **Prompt Log** page shows, for every ask, the original
question/rows side-by-side with the anonymized payload the model actually received.

**Documented exception:** the *decode* step (question → filters) sends the question text
as-is to the chosen model — filter values such as patient names must be extracted from it,
and no rows exist yet to build a scrub mapping. **No database rows ever accompany a
decode**, and every cloud decode is disclosed in the UI (see §4).

## 3. Guardrails against misuse and model error

| Guardrail | Mechanism |
|---|---|
| LLM output treated as untrusted | The brain only *proposes* query specs; it has no database access. The .NET layer independently re-validates every filter |
| Filter allowlist | Only whitelisted columns per table are filterable; PHI contact fields (Email, MRN, phone, NPI) are blocked |
| **Fail-closed on blocked filters** | Probing a protected field (e.g. "show patient with MRN-00003") returns **zero rows + an explanation** — never a broader result than asked for |
| Tamper-proof query spec | The spec travels through the browser signed + encrypted (ASP.NET Data Protection); crafted/altered specs are rejected |
| Off-topic questions fail closed | Unmappable questions return UNKNOWN with a message — no fabricated report |
| Honest failures | If both LLMs fail, the API returns an error (HTTP 502), never an invented summary; Claude API errors surface their real cause |
| Prompt-injection hardening | LLM prompts mark the question and data as untrusted content to be summarized, not instructions to follow |
| Deterministic decode corrections | Known small-model errors (inverted gender filters, city/facility confusion, hallucinated filters) are fixed or dropped post-decode |
| Read-only by construction | The system can only render reports; there is no write path from any LLM output to the database |

## 4. Human oversight & transparency

- **Build time:** every migrated report passes a **developer review checkpoint** — the
  thought file (business-logic analysis) is approved by a human *before* any code is
  generated.
- **Runtime — model choice:** the user explicitly picks **Ask Local AI** (on-device) or
  **Ask Claude** (cloud) per question.
- **Runtime — provenance:** every answer carries a banner naming the model that produced
  it — *Local LLM*, *Claude*, or *Claude (fallback)*. Cloud usage is never silent, including
  automatic fallback.
- **Runtime — auditability:** the Prompt Log shows the routing chain per question
  (e.g. `Local LLM ✗ → Claude — fallback ✓`) and the exact anonymized payloads sent.
- **Applied-filter disclosure:** every filter the AI derived is shown as a badge; skipped
  (blocked) filters are shown struck-through.

## 5. Known risks & mitigations

| Risk | Mitigation / current state |
|---|---|
| Question text reaches the cloud on Ask Claude / fallback | Inherent to decoding (see §2 exception). Disclosed in UI; rows never sent; users can stay fully local with Ask Local AI |
| Small local model misdecodes a question | Deterministic guardrails + confidence threshold + automatic Claude fallback + filter badges let the user see exactly what was applied |
| LLM narrative inaccuracies | Statistics are computed programmatically and injected into the prompt; the narrative is labeled as AI-generated |
| No authentication / audit logging | Deliberate PoC scope reduction — called out, not hidden. Productionization would reuse the host app's auth (see SRS FR-2.4) |
| Question visible in URL query string | Known PoC limitation, documented in the runbook's security section |
| Prompt Log holds question/row samples in memory | Bounded (50 entries), process-local, never persisted, cleared on restart; intended as a demo/transparency surface, not an audit trail |

## 6. Licensing

All third-party components are permissively licensed (MIT/Apache/BSD): FastAPI, Uvicorn,
Pydantic, PDFsharp/MigraDoc (MIT), Chart.js (vendored locally, MIT), Bootstrap, EF Core.
No revenue-gated or copyleft-restricted dependencies.
