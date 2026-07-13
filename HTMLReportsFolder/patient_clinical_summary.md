# Patient Clinical Summary Report

**Report key:** `patient_clinical_summary`

## Purpose

A grouped clinical dashboard. For a chosen visit-date window and patient age range it
lists each facility with:

1. a **Facility Summary** aggregate table (one row per facility), and
2. a nested **Facility -> Patient -> Transplant Event -> Lab Result** detail,

enriched with calculated columns (Age, BMI + category, risk score, lab out-of-range
flags) and risk / inpatient / out-of-range conditional formatting.

Migrated from the SSRS report `PatientClinicalSummaryReport.rdl`. The RDL is rendered
from **host-fed data** — its SQL dataset never executes at render time. The .NET host
applies the report parameters as data filters and injects the already-filtered result
set as `window.REPORT_DATA`.

## Data contract (`window.REPORT_DATA`)

```js
window.REPORT_DATA = {
  parameters: {
    fromDate: "2026-01-01",   // visit-date lower bound (applied by host)
    toDate:   "2026-12-31",   // visit-date upper bound (applied by host)
    minAge:   0,              // patient age lower bound (applied by host)
    maxAge:   120,            // patient age upper bound (applied by host)
    status:   "All",          // host-fixed today; echoed in the filters strip
    rptUser:  "system"        // chrome only; footer "Run by:"
  },
  rows: [ /* one object per ALREADY-FILTERED ClinicalFlatRow, camelCase keys */ ],
  narrative: "",
  meta: { generatedAt: "2026-07-13T10:00:00Z", executedBy: "jdoe", rowCount: 0 }
};
```

**Rows arrive pre-filtered.** The host (`PatientDataService.GetClinicalFlatRowsAsync`)
applies the visit-date window, age range, and status server-side and hands over the
post-filter rows. The template renders `rows` **as-is** and never re-implements any
WHERE / parameter / age / status filtering in JavaScript.

### Row keys (fed columns, camelCase from `ClinicalFlatRow`)

| Key | Type | Meaning |
|-----|------|---------|
| `facilityName` | string | Facility name (top grouping key) |
| `facilityCity` | string | Facility city |
| `facilityState` | string | Facility 2-char state |
| `patientId` | int | Patient PK (patient grouping key) |
| `mrn` | string | Medical record number (RDL column `MRN`) |
| `patientName` | string | Patient full name (pre-computed) |
| `gender` | string | Sex |
| `dateOfBirth` | ISO date | Feeds Age |
| `heightCm` | number | Feeds BMI |
| `weightKg` | number | Feeds BMI |
| `status` | string | Active / Inactive |
| `eventId` | string | Transplant event id (event grouping key) |
| `donorType` | string | Autologous / Allogeneic |
| `dateOfVisit` | ISO date | Visit date (sort key) |
| `dateOfPreviousVisit` | ISO date | Feeds DaysSincePreviousVisit |
| `isInpatient` | bool | Inpatient flag |
| `providerName` | string | Attending provider (pre-computed, else `-`) |
| `specialty` | string | Provider specialty |
| `primaryDiagnosis` | string | Highest-severity, most-recent diagnosis (pre-computed) |
| `activeMedCount` | int | Count of active medications (pre-computed) |
| `labTestName` | string? | Lab test name (null when event has no labs) |
| `labValue` | number? | Lab result value (null when no labs) |
| `labUnit` | string? | Lab unit (null when no labs) |
| `refLow` | number? | Reference range low (null when no labs) |
| `refHigh` | number? | Reference range high (null when no labs) |

Rows use LEFT-JOIN semantics: an event with labs emits one row per lab; an event with no
labs emits one row with the lab columns null.

## Calculated fields (computed in JS from the fed rows)

These mirror the RDL `<Field>` expressions and are computed at render time (they are not
fed columns):

| Field | Formula | Notes |
|-------|---------|-------|
| Age | `Floor(DateDiff(Day, dateOfBirth, Today) / 365.25)` | RDL display age; used in Avg Age, banner, risk |
| BMI | `heightCm > 0 ? Round(weightKg / (heightCm/100)^2, 1) : 0` | 1 decimal; 0 when height missing |
| DaysSincePreviousVisit | `DateDiff(Day, dateOfPreviousVisit, dateOfVisit)` | Computed but **not rendered** (RDL never placed it in a cell) |
| LabFlag | `labValue == null ? "" : (out of [refLow, refHigh] ? "OUT" : "OK")` | Drives the Flag column + out-of-range counts |
| `bmiCategory(bmi)` | `0->N/A; <18.5 Underweight; <25 Normal; <30 Overweight; else Obese` | RDL `Code.BmiCategory`, display only |
| `riskScore(age, inpatient, oorLabs)` | `age>=65 +2 else age>=45 +1; +2 if inpatient; + oorLabs` | RDL `Code.RiskScore`; high risk = `>= 4` |

## Filters / parameters (interactive)

The report has 4 user-facing filters, rendered as a real `<form data-filter-form>`:

| Control (`name`) | Type | Query-string key the host accepts | How it filters (server-side) |
|------------------|------|-----------------------------------|------------------------------|
| `fromDate` | `<input type="date">` | `fromDate` | Keep row if `DateOfVisit >= fromDate` |
| `toDate` | `<input type="date">` | `toDate` | Keep row if `DateOfVisit <= toDate` |
| `minAge` | `<input type="number">` | `minAge` | Keep row if patient (calendar) `Age >= minAge` |
| `maxAge` | `<input type="number">` | `maxAge` | Keep row if patient (calendar) `Age <= maxAge` |

Round-trip behaviour:

- On load, the JS **populates** each control from `REPORT_DATA.parameters`.
- On submit, the JS **merges** the control values into the current page's query string via
  `URLSearchParams(location.search)` and sets `location.search`, which reloads the page.
  This **preserves the routing `report=` param** (and any others). It does **not** use a
  plain form GET and does **not** filter rows in JS.
- The host endpoint serving the template must accept `fromDate`, `toDate`, `minAge`,
  `maxAge` as query-string values, apply them as data filters, and set
  `REPORT_DATA.parameters` to the applied values.

`status` (default `All`) and `rptUser` are not user-facing form controls: `status` is
currently host-fixed (echoed in the filters strip), `rptUser` is footer chrome.

Age note: the host filters on the **calendar-based** age (today - DOB, adjusted for
birthday); the displayed `Age` uses `Floor(DateDiff(Day, DOB, Today)/365.25)`. The two can
differ by ~1 year near birthdays. The calendar age governs which rows pass the filter
(server-side); the display column shows the `Floor(.../365.25)` value.

## Business rules implemented (view-level)

- **Filters strip echo:** `Filters - Visit dates: {from} to {to} | Age: {min} to {max} | Patient status: {status}` with dates as `MM/dd/yyyy`.
- **Facility Summary** (grouped by `facilityName`, sorted by name):
  - `# Patients` = distinct `patientId`
  - `# Events` = distinct `eventId`
  - `Avg Age` = `Round(Avg(Age), 0)` over the facility's detail rows
  - `Inpatient Events` = distinct `eventId` among inpatient rows
  - `Out-of-range Labs` = count of rows with `LabFlag == "OUT"` (red + bold when > 0)
- **Clinical Detail:** nested `Facility -> Patient -> Event+Lab`.
  - Facility band: `Facility:  {name}   -   {city}, {state}`.
  - Patient banner (sorted by `patientName`): Patient, MRN, Age, Sex, BMI (category),
    Risk, Primary Dx, Active meds. Background red-subtle when `riskScore >= 4`, else
    green-subtle.
  - Detail rows (sorted by `dateOfVisit` then `labTestName`), 9 columns: Event, Visit Date
    (`MM/dd/yyyy`), Provider (`name (specialty)`), Donor, Setting (Inpatient/Outpatient),
    Test (or `-`), Result (`value unit` or `-`), Reference (`low - high` or `-`), Flag.
- **Conditional formatting:**
  - Zebra striping on detail rows.
  - Setting cell highlighted yellow when inpatient.
  - Flag cell red + bold for `OUT`, green for `OK`.
  - Facility Summary out-of-range cell red + bold when > 0.
  - Patient banner red/green by risk.
- **Footer:** `Generated: {generatedAt MM/dd/yyyy HH:mm} | Run by: {executedBy|rptUser}`.
- **Empty state** shown when `rows` is empty.

## Deviations from the original SSRS report

- **DaysSincePreviousVisit** is computed (per the RDL field) but not displayed — the RDL
  never placed it in a cell. (Open question in the thought file; preserved as omitted.)
- **Detail grain:** the per-lab flat repetition of event metadata (Event, Visit, Provider,
  Donor, Setting repeat on each lab row of an event) is reproduced as-is, matching the RDL
  `grpDetail` grouping on `EventId + LabTestName`.
- **Status** remains host-fixed (`All`) and is echoed but not offered as a form control,
  matching the current controller behaviour.
- SSRS page header/footer paging (`Page X of Y`) is not reproduced; a single web footer is
  used instead.
- No network calls, external CSS/JS/fonts/images: fully self-contained and offline-openable.
