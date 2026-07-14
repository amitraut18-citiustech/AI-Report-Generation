# Patient Clinical Summary Report

## Purpose

A complex, multi-table clinical report that joins Patients, Facilities, Providers,
Transplant Events, Lab Results, Diagnoses, and Medications. Displays a **Facility Summary**
table with per-facility aggregates, followed by a **Clinical Detail** section grouped by
Facility > Patient > Transplant Event/Lab, with calculated clinical metrics (Age, BMI,
risk score, lab out-of-range flags) and conditional formatting.

Migrated from the SSRS report `PatientClinicalSummaryReport.rdl` and the .NET data service
`PatientDataService.GetClinicalFlatRowsAsync`.

## Columns

### Facility Summary Table

| # | Header             | Content                                                          |
|---|--------------------|------------------------------------------------------------------|
| 1 | Facility           | Facility name                                                    |
| 2 | # Patients         | Count of distinct patients at the facility                       |
| 3 | # Events           | Count of distinct transplant events at the facility              |
| 4 | Avg Age            | Average patient age across all rows in the facility (rounded)    |
| 5 | Inpatient Events   | Count of distinct inpatient events at the facility               |
| 6 | Out-of-range Labs  | Count of lab results flagged "OUT" at the facility               |

### Clinical Detail Table

| # | Header     | Content                                            | Format           |
|---|------------|----------------------------------------------------|------------------|
| 1 | Event      | Transplant event identifier                        |                  |
| 2 | Visit Date | Date of the transplant event visit                 | MM/dd/yyyy       |
| 3 | Provider   | Provider full name and specialty                   | "Name (Spec)"    |
| 4 | Donor      | Donor type (Autologous / Allogeneic)               |                  |
| 5 | Setting    | Inpatient or Outpatient                            |                  |
| 6 | Test       | Lab test name, or "-" if no lab                    |                  |
| 7 | Result     | Lab value and unit, or "-" if no lab               | "{val} {unit}"   |
| 8 | Reference  | Lab reference range, or "-" if no lab              | "{low} - {high}" |
| 9 | Flag       | Lab status: "OUT" if out of range, "OK" if in, ""  |                  |

### Group Banners (Clinical Detail)

- **Facility banner:** "Facility: {name} - {city}, {state}" on a light-blue background.
- **Patient banner:** Patient demographics and clinical metrics (Name, MRN, Age, Sex,
  BMI + category, Risk Score, Primary Dx, Active Meds). Background is red (#f8d7da) if
  RiskScore >= 4 (high risk), green (#d1e7dd) otherwise.

## Filters / Parameters

This report has four user-facing filter parameters. The host endpoint must accept these as
**query-string keys**, apply them as data filters before injecting `REPORT_DATA`, and echo
the applied values in `REPORT_DATA.parameters`.

| Parameter | Query-string key | Control type   | Default   | Filters what                                   |
|-----------|------------------|----------------|-----------|-------------------------------------------------|
| FromDate  | `fromDate`       | `<input date>` | 2026-01-01 | TransplantEvents.DateOfVisit >= value           |
| ToDate    | `toDate`         | `<input date>` | 2026-12-31 | TransplantEvents.DateOfVisit <= value           |
| MinAge    | `minAge`         | `<input number>` | 0       | Calculated patient Age >= value                 |
| MaxAge    | `maxAge`         | `<input number>` | 120     | Calculated patient Age <= value                 |

**Not exposed:** The `Status` parameter (All / Active / Inactive) is defined in the RDL
and accepted by the data service, but the controller always passes "All". The filter echo
displays "Patient status: All" as a fixed label.

**Filter form behavior:** On submit, the JS merges control values into the current page's
query string (preserving routing params like `report=`) and reloads. The host re-queries
with the new filter values and re-injects `REPORT_DATA`. The JS never filters rows
client-side.

## Business Rules Implemented (view-level)

### Calculated Fields (computed in JS from raw row data)

These fields are **not** present in `ClinicalFlatRow` / `REPORT_DATA.rows`. The JS
computes them at render time:

| Field        | Computation                                                                 |
|--------------|-----------------------------------------------------------------------------|
| Age          | `today.year - dob.year`, adjusted down by 1 if birthday has not yet occurred this year (calendar-year method) |
| BMI          | `round(weightKg / (heightCm/100)^2, 1)`; 0 if heightCm <= 0               |
| BmiCategory  | BMI=0 -> "N/A"; <18.5 -> "Underweight"; <25 -> "Normal"; <30 -> "Overweight"; >=30 -> "Obese" |
| RiskScore    | Per-patient aggregate: +2 if age>=65 (else +1 if age>=45); +2 if any inpatient event; + count of out-of-range labs |
| LabFlag      | Per-row: "" if labValue is null; "OUT" if labValue < refLow or > refHigh; "OK" otherwise |

### Pre-computed Fields (rendered as-is from rows)

These arrive already computed by the data service and are rendered without transformation:

- `patientName` (FirstName + LastName)
- `providerName` (Provider FirstName + LastName, or "-")
- `specialty` (Provider specialty, or "")
- `primaryDiagnosis` (highest-severity, most-recent diagnosis description, or "-")
- `activeMedCount` (count of active medications)
- `isInpatient` (boolean from TransplantEvents)

### Sorting

Rows are sorted client-side: `facilityName ASC`, then `patientName ASC`, then
`dateOfVisit ASC`, then `labTestName ASC` (nulls sort last).

### Conditional Formatting

- **Patient banner background:** Red (#f8d7da) if RiskScore >= 4; green (#d1e7dd) otherwise.
- **Setting cell:** Yellow (#fff3cd) background if Inpatient.
- **Lab Flag cell:** Red (#b02a37) bold text if "OUT"; green (#0f5132) if "OK".
- **Facility Summary Out-of-range Labs:** Red (#b02a37) bold text if count > 0.
- **Detail row alternating colors:** Odd rows #F2F2F2, even rows white.

### Aggregations (Facility Summary)

- **# Patients:** `CountDistinct(patientId)` per facility.
- **# Events:** `CountDistinct(eventId)` per facility.
- **Avg Age:** `Round(Avg(Age), 0)` across all rows in the facility group.
- **Inpatient Events:** `CountDistinct(eventId)` where `isInpatient` is true, per facility.
- **Out-of-range Labs:** Count of rows where `LabFlag === "OUT"` per facility.

## Data Contract

### `window.REPORT_DATA` Shape

```js
window.REPORT_DATA = {
  parameters: {
    fromDate: "2026-01-01",   // string, YYYY-MM-DD
    toDate:   "2026-12-31",   // string, YYYY-MM-DD
    minAge:   0,              // integer
    maxAge:   120             // integer
  },
  rows: [
    {
      // Facility
      facilityName:  "string",
      facilityCity:  "string",
      facilityState: "string",

      // Patient
      patientId:   0,           // int, used for grouping
      mrn:         "string",
      patientName: "string",    // pre-computed: FirstName + " " + LastName
      gender:      "string",
      dateOfBirth: "ISO-8601",  // e.g. "1960-05-15T00:00:00"
      heightCm:   0.0,         // double
      weightKg:   0.0,         // double
      status:      "string",   // "Active" or "Inactive"

      // Transplant Event
      eventId:             "string",
      donorType:           "string",  // "Autologous" or "Allogeneic"
      dateOfVisit:         "ISO-8601",
      dateOfPreviousVisit: "ISO-8601",
      isInpatient:         false,     // boolean

      // Provider
      providerName: "string",   // pre-computed, or "-"
      specialty:    "string",   // or ""

      // Clinical
      primaryDiagnosis: "string",  // pre-computed, or "-"
      activeMedCount:   0,         // int, pre-computed

      // Lab (nullable; null when event has no labs)
      labTestName: "string|null",
      labValue:    0.0,            // double|null
      labUnit:     "string|null",
      refLow:      0.0,           // double|null
      refHigh:     0.0            // double|null
    }
  ],
  narrative: "",                // LLM-generated summary; may be empty (see Narrative Rendering below)
  meta: {
    generatedAt: "ISO-8601",    // e.g. "2026-07-13T10:00:00Z"
    executedBy:  "string",      // username
    rowCount:    0              // int
  }
};
```

**Rows arrive pre-filtered.** The host applies `fromDate`, `toDate`, `minAge`, `maxAge`
(and the hardcoded `status = "All"`) in `GetClinicalFlatRowsAsync` before serializing rows
into `REPORT_DATA`. The JS never re-implements any of this filtering logic.

### Property Name Mapping (C# -> JSON camelCase)

| C# Property         | JSON Key              |
|----------------------|-----------------------|
| FacilityName         | facilityName          |
| FacilityCity         | facilityCity          |
| FacilityState        | facilityState         |
| PatientId            | patientId             |
| Mrn                  | mrn                   |
| PatientName          | patientName           |
| Gender               | gender                |
| DateOfBirth          | dateOfBirth           |
| HeightCm             | heightCm              |
| WeightKg             | weightKg              |
| Status               | status                |
| EventId              | eventId               |
| DonorType            | donorType             |
| DateOfVisit          | dateOfVisit           |
| DateOfPreviousVisit  | dateOfPreviousVisit   |
| IsInpatient          | isInpatient           |
| ProviderName         | providerName          |
| Specialty            | specialty             |
| PrimaryDiagnosis     | primaryDiagnosis      |
| ActiveMedCount       | activeMedCount        |
| LabTestName          | labTestName           |
| LabValue             | labValue              |
| LabUnit              | labUnit               |
| RefLow               | refLow                |
| RefHigh              | refHigh               |

## Deviations from Source SSRS Report

- **Page numbers** ("Page N of Total") are omitted from the footer. SSRS page numbering
  does not translate to a single-page HTML document.
- **DaysSincePreviousVisit** is defined as an RDL calculated field but is not displayed in
  any column of the original tablix layout, so it is not computed or rendered.
- **Status filter** is not exposed as an interactive control; the filter echo shows
  "Patient status: All" as a fixed label, matching the controller's hardcoded behavior.
- **Avg Age in Facility Summary** uses `Avg(Age)` across all detail rows in the facility
  group (matching the RDL expression), which weights patients by their number of rows
  (lab results). This matches the original SSRS behavior.

## Narrative Rendering

When `narrative` is non-empty, `renderNarrative()` builds a styled card:

- **Header:** Dark navy bar with an SVG info icon and the label "AI Summary" (`.report__narrative-header`)
- **Body:** The narrative text is split into paragraphs (every two sentences grouped) and rendered as `<p>` elements (`.report__narrative-body`)
- **Chart:** If `window.REPORT_DATA.chart` is present (type, title, labels, values), a Chart.js canvas is inserted after the narrative section (charts are disabled by default via the brain's `ENABLE_CHARTS` setting, so this field is normally absent)

The narrative section is hidden when `narrative` is empty.
