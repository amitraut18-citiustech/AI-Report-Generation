# Patient Clinical Summary Report

**Report key:** `patient_clinical_summary`
**Source of truth:** `ReportThoughts/patient_clinical_summary.thought.md`
(migrated from SSRS `PatientClinicalSummaryReport.rdl`). Where the RDL and the
corroborating .NET service diverge, **the RDL is authoritative**.

## Purpose

A grouped clinical dashboard that, for a visit-date window and patient-status
filter, lists every facility with:

1. a **Facility Summary** aggregate table, and
2. a nested **Facility → Patient → Transplant Event → Lab Result** detail,

enriched with calculated columns (Age, BMI + category, risk score, lab
out-of-range flags) and risk/inpatient/out-of-range conditional formatting.

The report is **not** a flat table. `window.REPORT_DATA.rows` is the flat joined
result set (one row per lab result, with event/patient/facility metadata
repeated; a row with null lab columns = an event with no labs). All grouping and
aggregation happen client-side in `patient_clinical_summary.js`.

## Parameters / filters

| Name | camelCase key | Default | User-facing | Purpose |
|------|---------------|---------|-------------|---------|
| FromDate | `fromDate` | 2026-01-01 | yes | Visit-date lower bound (`dateOfVisit >= fromDate`) |
| ToDate | `toDate` | 2026-12-31 | yes | Visit-date upper bound (`dateOfVisit <= toDate`) |
| Status | `status` | `All` | yes | Patient status filter; `All` disables it |
| rptUser | `rptUser` | `system` | no (chrome) | Printed in footer "Run by:" |

The read-only "Filters applied" strip mirrors the RDL filter-echo line:
`Filters  -  Visit dates: {from} to {to}     |     Patient status: {status}`.

**Filtering is applied in JS** (`applyRdlFilter`). See *Deviations* — the .NET
service that injects `REPORT_DATA` does **not** filter, so the JS reproduces the
RDL `WHERE te.DateOfVisit BETWEEN @FromDate AND @ToDate AND (@Status='All' OR
p.Status=@Status)`.

## Section 1 — Facility Summary

One row per facility (sorted by facility name). Aggregates computed in JS:

| Column | Rule |
|--------|------|
| Facility | `facilityName` |
| # Patients | count of **distinct** `patientId` in facility |
| # Events | count of **distinct** `eventId` in facility |
| Avg Age | `Round(Avg(Age), 0)` — **row-weighted** average of Age over all facility rows (see *Deviations*) |
| Inpatient Events | count of **distinct** `eventId` among inpatient rows only |
| Out-of-range Labs | count of rows where `LabFlag = "OUT"` |

Conditional formatting: **Out-of-range Labs** cell is **bold red** (`#b02a37`)
when the count is `> 0`.

## Section 2 — Clinical Detail (nested)

Three-level nested hierarchy rendered as full-width band rows interleaved with
9-column detail rows, in one table with a repeating column header:

1. **Facility band row** (`grpFacility`, sorted by facility name) —
   `Facility:  {name}   -   {city}, {state}`, background `#dbe5f1`.
2. **Patient banner row** (`grpPatient`, sorted by patient name) — shows Patient,
   MRN, Age, Sex, BMI (+ category), Primary Dx, Active meds, and Risk. Background
   is **red-subtle** (`#f8d7da`) when high risk, else **green-subtle**
   (`#d1e7dd`).
3. **Detail rows** (`grpDetail` on `eventId + labTestName`, sorted by visit date
   then lab test name). Event metadata repeats on every lab row of an event
   (RDL flat-repeat grain — see *Deviations*).

Detail columns (order and labels match the RDL):

| # | Column | Rule |
|---|--------|------|
| 1 | Event | `eventId` |
| 2 | Visit Date | `dateOfVisit` as `MM/dd/yyyy` (+ days-since-previous-visit sub-note) |
| 3 | Provider | `providerName (specialty)` |
| 4 | Donor | `donorType` |
| 5 | Setting | `Inpatient`/`Outpatient`; yellow highlight (`#fff3cd`) if inpatient |
| 6 | Test | `labTestName` or `-` |
| 7 | Result | `labValue labUnit` or `-` |
| 8 | Reference | `refLow - refHigh` or `-` |
| 9 | Flag | `LabFlag`: `OUT` bold red / `OK` green / blank |

## Calculated fields (JS transforms)

- **Age** = `Floor(DateDiff(Day, dateOfBirth, Today()) / 365.25)` — RDL day-count
  method (authoritative).
- **BMI** = `IIF(heightCm > 0, Round(weightKg / (heightCm/100)^2, 1), 0)`.
- **DaysSincePreviousVisit** = `DateDiff(Day, dateOfPreviousVisit, dateOfVisit)`.
- **LabFlag** = `""` if `labValue` is null; `OUT` if `labValue < refLow` or
  `> refHigh`; else `OK`.

## Custom functions (from the RDL `<Code>` block)

```
bmiCategory(bmi):   0 -> "N/A";  <18.5 -> "Underweight";  <25 -> "Normal";
                    <30 -> "Overweight";  else "Obese"
riskScore(age, inpatient, outOfRangeLabs):
                    score = 0
                    age >= 65 -> +2   else age >= 45 -> +1
                    inpatient -> +2
                    score += outOfRangeLabs
```

**High risk** = `riskScore >= 4`. The patient-scoped risk uses the patient's age,
whether **any** of the patient's events was inpatient, and the patient's **total**
out-of-range lab count — matching the RDL `First(Age,"grpPatient")`,
`Sum(IIF(IsInpatient,1,0),"grpPatient") > 0`,
`Sum(IIF(LabFlag="OUT",1,0),"grpPatient")` scoping.

## Conditional formatting implemented

1. Facility Summary "Out-of-range Labs" > 0 → bold red.
2. Patient banner background red-subtle (high risk) vs green-subtle.
3. Detail "Setting" cell highlighted yellow when inpatient.
4. Detail "Flag" cell red-bold for `OUT`, green for `OK`.

## Data contract (`window.REPORT_DATA`)

```js
window.REPORT_DATA = {
  parameters: { fromDate, toDate, status, rptUser },
  rows: [ /* flat joined rows, keys below */ ],
  narrative: "",
  meta: { generatedAt, executedBy, rowCount }
};
```

Row keys (ViewModel property → camelCase): `facilityName`, `facilityCity`,
`facilityState`, `patientId`, `mrn`, `patientName`, `gender`, `dateOfBirth`,
`heightCm`, `weightKg`, `status`, `eventId`, `transplantNumber`, `donorType`,
`dateOfVisit`, `dateOfPreviousVisit`, `transplantDate`, `infusionDate`,
`dischargeDate`, `isInpatient`, `providerName`, `specialty`, `primaryDiagnosis`,
`activeMedCount`, `labTestName`, `labValue`, `labUnit`, `refLow`, `refHigh`,
`labTakenDate`.

`isInpatient` is accepted as a real boolean, `"Yes"/"No"`, `"true"/"false"`, or
`1/0`. `primaryDiagnosis` and `activeMedCount` are the RDL correlated-subquery
results and are rendered as pre-computed (not recomputed in JS).

The report renders **only** from `REPORT_DATA` — no network calls, no external
assets. If `REPORT_DATA` is missing or no rows survive filtering, a visible empty
state is shown.

## Deviations from source (and ambiguity resolutions)

- **Filtering divergence (RDL vs .NET):** RDL filters by date/status; the .NET
  `GetClinicalSummaryAsync()` loads everything unfiltered. **RDL chosen as
  authoritative** — filtering is reproduced in JS. This is the one place where JS
  intentionally re-runs server-side query logic, because the injecting service
  omits it.
- **Detail grain:** RDL groups detail by `eventId + labTestName`, so event
  metadata repeats per lab row; the Razor view instead nests labs under each
  event. **RDL flat-repeat chosen** (event columns repeat on each lab row).
- **Age formula:** RDL day-count `/365.25` used (not the .NET calendar age); may
  differ by ~1 year near birthdays.
- **DaysSincePreviousVisit:** computed in the RDL dataset but not placed in any
  RDL cell; the Razor view does display it. To honor the RDL 9-column layout
  while surfacing the value (as Razor does), it is rendered as a small sub-note
  beneath the Visit Date rather than as a separate column.
- **Avg Age is row-weighted:** SSRS `Avg(Age)` in the facility group averages Age
  over all facility rows, so patients with more lab rows are weighted more. This
  matches the original report; it is not a distinct-patient average.
- **`CountDistinct(IIF(IsInpatient, EventId, Nothing))`:** reproduced as the count
  of distinct `eventId`s among inpatient rows only (SSRS ignores `Nothing`).
- **Fields selected but never displayed** (`transplantDate`, `infusionDate`,
  `dischargeDate`, `labTakenDate`, `transplantNumber`) are omitted, matching the
  RDL layout.
- **Page footer "Page X of Y":** an SSRS paginated-render concept with no meaning
  in a single scrollable HTML page; the footer shows the row count instead. The
  "Generated / Run by" line is reproduced.
