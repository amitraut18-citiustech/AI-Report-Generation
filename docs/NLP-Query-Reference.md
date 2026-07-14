# NLP Query Reference

## How It Works

Type a natural-language question into the query box on the **AI Reports** page and choose a model:

- **Ask Local AI** — the Python brain decodes the question with Ollama (`qwen2.5:3b` by default). If the local model fails or is too uncertain, the brain automatically retries on the Claude API when a key is configured.
- **Ask Claude** — the question is decoded directly by the Claude API.

The brain determines which report to show and what filters to apply. The .NET app then executes the query against the SQLite database, renders the matching HTML report template, and adds an AI-generated narrative summary. A banner above the report always shows which model answered (*Local LLM*, *Claude*, or *Claude (fallback)*).

The expected results below were validated with the local model; Claude generally decodes the same or better.

---

## Available Reports

| Report Key | Route Value | Description |
|---|---|---|
| `patient` | `patient` | Flat listing of all patients with demographics and contact info |
| `transplant_event` | `transplant` | Transplant events with patient names, visit dates, donor type, inpatient status |
| `patient_clinical_summary` | `clinical` | Multi-table clinical report with facility summary, lab results, risk scores |

---

## Supported Operators

| Operator | Meaning | Applies to | SQL Equivalent |
|---|---|---|---|
| `equals` | Exact match (case-insensitive for strings) | All types | `= value` |
| `notEquals` | Not equal | All types | `!= value` |
| `contains` | Substring match | Strings only | `LIKE '%value%'` |
| `greaterThan` | Strictly greater | Numbers, dates | `> value` |
| `greaterThanOrEqual` | Greater or equal | Numbers, dates | `>= value` |
| `lessThan` | Strictly less | Numbers, dates | `< value` |
| `lessThanOrEqual` | Less or equal | Numbers, dates | `<= value` |

Multiple filters in one query are combined with **AND**. OR logic is not supported.

---

## Patient Report Queries

### No filters (all patients)

| Query | Expected Rows |
|---|---|
| Show me all patients | 8 |
| List all patients | 8 |
| Patient report | 8 |

### Filter by first name

| Query | Filter Applied | Expected Rows |
|---|---|---|
| Show me patients named Ethan | FirstName = "Ethan" | 1 (Ethan Brooks) |
| Show patients named Ava | FirstName = "Ava" | 1 (Ava Patel) |
| Show patients named Mia | FirstName = "Mia" | 1 (Mia Thompson) |

### Filter by last name

| Query | Filter Applied | Expected Rows |
|---|---|---|
| Show patients with last name Garcia | LastName = "Garcia" | 1 (Noah Garcia) |
| Show patients with last name Patel | LastName = "Patel" | 1 (Ava Patel) |
| List patients named Thompson | LastName = "Thompson" | 1 (Mia Thompson) |

### Filter by full name

| Query | Filter Applied | Expected Rows |
|---|---|---|
| Show patient Ava Patel | FirstName = "Ava" AND LastName = "Patel" | 1 |
| Show patient Noah Garcia | FirstName = "Noah" AND LastName = "Garcia" | 1 |

### Filter by gender

| Query | Filter Applied | Expected Rows |
|---|---|---|
| List all female patients | Gender = "Female" | 4 (Ava, Mia, Olivia, Sophia) |
| Show me male patients | Gender = "Male" | 4 (Noah, Liam, Ethan, Lucas) |

### Filter by status

| Query | Filter Applied | Expected Rows |
|---|---|---|
| Show me inactive patients | Status = "Inactive" | 2 (Liam Walker, Sophia Chen) |
| Show active patients | Status = "Active" | 6 |

### Filter by date of birth

| Query | Filter Applied | Expected Rows |
|---|---|---|
| List patients born before 1970 | DateOfBirth < "1970-01-01" | 2 (Noah 1957, Olivia 1965) |
| Show patients born after 1990 | DateOfBirth > "1990-01-01" | 3 (Liam 1994, Lucas 2000, Sophia 1990) |

### Filter by facility (cross-table)

| Query | Filter Applied | Expected Rows |
|---|---|---|
| Show patients at Austin General Hospital | Facilities.Name = "Austin General Hospital" | 3 (Ava, Noah, Lucas) |
| Show patients at Dallas Transplant Clinic | Facilities.Name = "Dallas Transplant Clinic" | 3 (Mia, Liam, Sophia) |
| Show patients at Houston Medical Center | Facilities.Name = "Houston Medical Center" | 2 (Ethan, Olivia) |
| Show patients from Dallas | Facilities.City = "Dallas" | 3 |
| Show patients from Houston | Facilities.City = "Houston" | 2 |

### Combined filters (AND)

| Query | Filters Applied | Expected Rows |
|---|---|---|
| Show me male patients from Dallas | Gender = "Male" AND Facilities.City = "Dallas" | 1 (Liam Walker) |
| Show female patients at Austin General Hospital | Gender = "Female" AND Facilities.Name = "Austin General Hospital" | 1 (Ava Patel) |
| Show active male patients | Gender = "Male" AND Status = "Active" | 3 (Noah, Ethan, Lucas) |

---

## Transplant Event Report Queries

### No filters (all events)

| Query | Expected Rows |
|---|---|
| Show all transplant events | 12 |
| List all transplants | 12 |

### Filter by inpatient/outpatient

| Query | Filter Applied | Expected Rows |
|---|---|---|
| Show inpatient transplant events | IsInpatient = "true" | 8 |
| Show outpatient transplant events | IsInpatient = "false" | 4 (EVT-1002, EVT-2003, EVT-4004, EVT-6007) |

### Filter by donor type

| Query | Filter Applied | Expected Rows |
|---|---|---|
| Show autologous transplant events | DonorType = "Autologous" | 3 (EVT-1001, EVT-4004, EVT-6006) |
| Show allogeneic transplant events | DonorType = "Allogeneic" | 8 |

### Filter by date range

| Query | Filters Applied | Expected Rows |
|---|---|---|
| Show transplant events in January 2026 | DateOfVisit >= "2026-01-01" AND DateOfVisit <= "2026-01-31" | 3 (EVT-1001, EVT-6007, EVT-3003) |
| Show transplant events between January and March 2026 | DateOfVisit >= "2026-01-01" AND DateOfVisit <= "2026-03-31" | 5 |
| Show transplant events after March 2026 | DateOfVisit > "2026-03-31" | 3 (EVT-5005, EVT-3004, EVT-7008) |
| Show transplant events before 2026 | DateOfVisit < "2026-01-01" | 3 (EVT-6006, EVT-2003, EVT-8009) |

### Filter by patient name (cross-table)

| Query | Filters Applied | Expected Rows |
|---|---|---|
| Show transplant events for patient Ava Patel | Patients.FirstName = "Ava" AND Patients.LastName = "Patel" | 2 (EVT-1001, EVT-1002) |
| Show Mia Thompson transplant history | Patients.FirstName = "Mia" AND Patients.LastName = "Thompson" | 2 (EVT-3003, EVT-3004) |
| Show transplant events for Noah | Patients.FirstName = "Noah" | 2 (EVT-2002, EVT-2003) |

### Combined filters

| Query | Filters Applied | Expected Rows |
|---|---|---|
| Show outpatient transplant events with allogeneic donors | IsInpatient = "false" AND DonorType = "Allogeneic" | 3 (EVT-1002, EVT-2003, EVT-6007) |
| Show inpatient transplant events in 2026 | IsInpatient = "true" AND DateOfVisit >= "2026-01-01" | 5 |

---

## Clinical Summary Queries

The clinical report is built from denormalized flat rows, so brain-decoded filters are applied **in memory** (`ReportQueryService.FilterClinicalRows`) on top of the default parameters (date range 2026-01-01 to 2026-12-31, age 0-120, status "All"). Supported filter targets: gender, status, patient/provider name, facility name/city/state, donor type, inpatient flag, visit dates, lab test name/value.

| Query | Filters Applied | Result |
|---|---|---|
| Show clinical summary | none | All rows within default date/age range |
| show clinical details of female patients from Austin General Hospital | Gender = "Female" AND Facilities.Name = "Austin General Hospital" | Only Ava Patel's rows |
| clinical summary for patients in Dallas | Facilities.City = "Dallas" | Dallas Transplant Clinic rows only |
| clinical report for male patients | Gender = "Male" | Male patients' rows only |
| clinical summary of allogeneic transplants | DonorType = "Allogeneic" | Allogeneic event rows only |

Note: `FirstName`/`LastName` filters match as substrings of the combined `PatientName`/`ProviderName` columns. Age filters work only if the model decodes them as a `DateOfBirth` range.

---

## Queries That Return No Matching Report

These queries are correctly rejected with `report = "UNKNOWN"`:

| Query | Result |
|---|---|
| What is the weather today | UNKNOWN (confidence 0.0) |
| Tell me a joke | UNKNOWN |
| How do I reset my password | UNKNOWN |

---

## Seed Data Reference

### Patients (8 total)

| First Name | Last Name | Gender | DOB | Status | Facility |
|---|---|---|---|---|---|
| Ava | Patel | Female | 1988-04-12 | Active | Austin General Hospital |
| Noah | Garcia | Male | 1957-09-23 | Active | Austin General Hospital |
| Mia | Thompson | Female | 1972-01-30 | Active | Dallas Transplant Clinic |
| Liam | Walker | Male | 1994-11-05 | Inactive | Dallas Transplant Clinic |
| Ethan | Brooks | Male | 1980-03-14 | Active | Houston Medical Center |
| Olivia | Martinez | Female | 1965-07-22 | Active | Houston Medical Center |
| Lucas | Kim | Male | 2000-01-09 | Active | Austin General Hospital |
| Sophia | Chen | Female | 1990-05-30 | Inactive | Dallas Transplant Clinic |

### Facilities (3 total)

| Name | City | State | Type |
|---|---|---|---|
| Austin General Hospital | Austin | TX | Hospital |
| Dallas Transplant Clinic | Dallas | TX | Clinic |
| Houston Medical Center | Houston | TX | Hospital |

### Providers (5 total)

| Name | Specialty | Facility |
|---|---|---|
| Sarah Reed | Hematology | Austin General Hospital |
| Omar Khan | Oncology | Austin General Hospital |
| Linda Nguyen | Nephrology | Dallas Transplant Clinic |
| James Carter | Cardiology | Houston Medical Center |
| Priya Sharma | Immunology | Houston Medical Center |

### Transplant Events (12 total)

| Event ID | Patient | Visit Date | Donor Type | Inpatient |
|---|---|---|---|---|
| EVT-1001 | Ava Patel | 2026-01-15 | Autologous | Yes |
| EVT-1002 | Ava Patel | 2026-03-10 | Allogeneic | No |
| EVT-2002 | Noah Garcia | 2026-02-05 | Allogeneic | Yes |
| EVT-2003 | Noah Garcia | 2025-11-30 | Allogeneic | No |
| EVT-3003 | Mia Thompson | 2026-01-28 | Allogeneic | Yes |
| EVT-3004 | Mia Thompson | 2026-05-05 | Allogeneic | Yes |
| EVT-4004 | Liam Walker | 2026-02-18 | Autologous | No |
| EVT-5005 | Ethan Brooks | 2026-04-05 | Allogeneic | Yes |
| EVT-6006 | Olivia Martinez | 2025-10-12 | Autologous | Yes |
| EVT-6007 | Olivia Martinez | 2026-01-20 | Allogeneic | No |
| EVT-7008 | Lucas Kim | 2026-06-15 | Allogeneic | Yes |
| EVT-8009 | Sophia Chen | 2025-12-22 | Living Donor | Yes |

---

## Robustness Guardrails

Because the local 3B model occasionally decodes filters incorrectly, the brain applies deterministic corrections after parsing (`prompt_decoder._sanitize_filters`). These apply to the **local model's output only** — Claude's decodes are used as-is:

1. **Gender inversion fix** — "women"/"men" sometimes decodes as `Gender notEquals ...`. If the question contains no exclusion word (exclude, except, not, non, without), `notEquals` on Gender is flipped to `equals`.
2. **City-in-Name fix** — a single-word `Facilities.Name` value with no facility keyword (hospital, clinic, center, medical) is moved to `Facilities.City` (e.g. "patients in Dallas").

The decoder prompt also includes explicit gender-synonym, location, and date-direction ("after" = greaterThan, "before" = lessThan) rules. An end-to-end battery of 24 NLP questions passes 23/24; the one deviation is a SQL-injection-style string being safely rejected as UNKNOWN.

---

## Current Limitations

1. **No OR logic** — all filters are AND'd. "Show patients from Austin or Houston" will not work correctly.
2. **No startsWith / endsWith** — only full substring match (`contains`) is available.
3. **No aggregations** — questions like "average age by facility" or "top 5 by lab value" are not supported.
4. **Facility filter on transplant events** — the LLM sometimes misroutes facility filters through `Providers.FacilityId` instead of the correct 2-hop path `TransplantEvents → Patient → Facility`. This can cause the facility filter to be silently dropped.
5. **Model non-determinism** — the `qwen2.5:3b` model may occasionally produce slightly different filter structures for the same query. Results listed above are the most common outcomes. Using **Ask Claude** typically resolves misdecodes.
6. **Narrative accuracy** — the AI summary may contain minor factual errors (e.g., wrong gender counts) due to the small model's limited reasoning capacity. Verified statistics are computed programmatically and injected into the prompt to reduce this.
7. **Filterable fields are allowlisted** — filters on PHI contact fields (Email, PhoneNumber, MRN, NPI) are deliberately blocked and will be skipped.
8. **No charts** — charts are disabled by default (`ENABLE_CHARTS=false` in the brain's `.env`); the AI summary is text-only.
