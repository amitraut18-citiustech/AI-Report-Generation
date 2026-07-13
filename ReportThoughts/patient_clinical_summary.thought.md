# Report Thought: Patient Clinical Summary Report

**Report key:** patient_clinical_summary

## Source
- **Legacy format:** SSRS (.rdl) -- **rich**: real dataset with SQL query, calculated fields, embedded VB.NET Code functions (BmiCategory, RiskScore), grouped tablixes with aggregates, six report parameters, and conditional formatting.
- **Description:** A complex, multi-table clinical report that joins Patients, Facilities, Providers, TransplantEvents, LabResults, Diagnoses, and Medications. Shows a facility-level summary table with aggregates, then a grouped detail section (Facility > Patient > Event > Lab) with calculated clinical metrics (Age, BMI, risk score, lab out-of-range flags).
- **Source files:**
  | Role | File |
  |------|------|
  | Report wiring (name -> data -> output) | `Controllers/ReportsController.cs` -- routes `"clinical"` to `GetClinicalFlatRowsAsync`, serves as `patient_clinical_summary` template |
  | Data access (query + projection) | `DataServices/PatientDataService.cs` -- method `GetClinicalFlatRowsAsync` |
  | Data access (hierarchical, PDF only) | `DataServices/PatientDataService.cs` -- method `GetClinicalSummaryAsync` (not used by HTML path) |
  | Row shape (view model / DTO) | `Models/ClinicalFlatRow.cs` -- flat denormalized row, one per lab result (null lab fields when event has no labs) |
  | Hierarchical view model (PDF only) | `Models/ClinicalSummaryViewModel.cs` -- `FacilitySummary > PatientSummary > EventSummary > LabSummary` |
  | Data model / schema (EF entities) | `Models/Patient.cs`, `Models/TransplantEvent.cs`, `Models/Facility.cs`, `Models/Provider.cs`, `Models/Diagnosis.cs`, `Models/Medication.cs`, `Models/LabResult.cs` |
  | DbContext | `Data/ApplicationDbContext.cs` |
  | Legacy RDL (rich) | `Reports/PatientClinicalSummaryReport.rdl` |

## Database Context
- **Provider / data source:** EF Core + SQLite (`db/PatientDB.db`, recreated and seeded on startup).
- **Entities/tables used:** Facilities, Patients, TransplantEvents, Providers, LabResults, Diagnoses, Medications.
- **Fields (from the row shape `ClinicalFlatRow` -- authoritative):**
  | Field | Type | Direct / derived | Meaning |
  |-------|------|------------------|---------|
  | FacilityName | string | direct (Facilities.Name) | Name of the patient's facility |
  | FacilityCity | string | direct (Facilities.City) | Facility city |
  | FacilityState | string | direct (Facilities.State) | Facility state abbreviation |
  | PatientId | int | direct (Patients.Id) | Patient primary key (used for grouping) |
  | Mrn | string | direct (Patients.MRN) | Medical Record Number |
  | PatientName | string | derived (`FirstName + " " + LastName`) | Full patient name |
  | Gender | string | direct (Patients.Gender) | Patient gender |
  | DateOfBirth | DateTime | direct (Patients.DateOfBirth) | Patient date of birth |
  | HeightCm | double | direct (Patients.HeightCm) | Patient height in centimeters |
  | WeightKg | double | direct (Patients.WeightKg) | Patient weight in kilograms |
  | Status | string | direct (Patients.Status) | Patient status: "Active" or "Inactive" |
  | EventId | string | direct (TransplantEvents.EventId) | Transplant event identifier |
  | DonorType | string | direct (TransplantEvents.DonorType) | "Autologous" or "Allogeneic" |
  | DateOfVisit | DateTime | direct (TransplantEvents.DateOfVisit) | Visit date for this transplant event |
  | DateOfPreviousVisit | DateTime | direct (TransplantEvents.DateOfPreviousVisit) | Previous visit date |
  | IsInpatient | bool | direct (TransplantEvents.IsInpatient) | Whether the event was an inpatient visit |
  | ProviderName | string | derived (`Provider.FirstName + " " + Provider.LastName`, or `"-"` if null) | Attending provider's full name |
  | Specialty | string | direct (Providers.Specialty, or `""` if null) | Provider medical specialty |
  | PrimaryDiagnosis | string | derived (see Business Logic) | Description of the patient's highest-severity, most-recent diagnosis |
  | ActiveMedCount | int | derived (`Count of Medications where IsActive == true`) | Number of active medications for the patient |
  | LabTestName | string? | direct (LabResults.TestName), nullable | Lab test name (null when event has no labs) |
  | LabValue | double? | direct (LabResults.Value), nullable | Lab result numeric value |
  | LabUnit | string? | direct (LabResults.Unit), nullable | Lab result unit (e.g. "g/dL") |
  | RefLow | double? | direct (LabResults.ReferenceLow), nullable | Lab reference range lower bound |
  | RefHigh | double? | direct (LabResults.ReferenceHigh), nullable | Lab reference range upper bound |

  **Fields NOT in ClinicalFlatRow but computed at render time (defined in the RDL as calculated fields / Code functions):**
  | Computed field | Type | Computation | Where computed |
  |----------------|------|-------------|----------------|
  | Age | int | Years from DateOfBirth to today: `Floor((today - DateOfBirth).Days / 365.25)` | RDL calculated field; also in data service `CalculateAge` for filtering |
  | BMI | double | `WeightKg / (HeightCm / 100)^2`, rounded to 1 decimal; 0 if HeightCm is 0 | RDL calculated field; also in `GetClinicalSummaryAsync` |
  | BmiCategory | string | BMI=0 -> "N/A"; <18.5 -> "Underweight"; <25 -> "Normal"; <30 -> "Overweight"; else -> "Obese" | RDL Code function `BmiCategory`; also in data service static method |
  | RiskScore | int | Start at 0; +2 if age >= 65, +1 if age >= 45; +2 if any inpatient event; + count of out-of-range labs | RDL Code function `RiskScore`; also in data service static method |
  | DaysSincePreviousVisit | int | `(DateOfVisit - DateOfPreviousVisit).Days` | RDL calculated field |
  | LabFlag | string | If LabValue is null -> ""; if LabValue < RefLow or LabValue > RefHigh -> "OUT"; else -> "OK" | RDL calculated field |

- **Relationships:**
  - Patients.FacilityId -> Facilities.Id (many-to-one; Restrict delete)
  - TransplantEvents.PatientId -> Patients.Id (many-to-one; Cascade delete)
  - TransplantEvents.ProviderId -> Providers.Id (many-to-one; Restrict delete)
  - Providers.FacilityId -> Facilities.Id (many-to-one; Restrict delete)
  - LabResults.TransplantEventId -> TransplantEvents.Id (many-to-one; Cascade delete)
  - Diagnoses.PatientId -> Patients.Id (many-to-one; Cascade delete)
  - Medications.PatientId -> Patients.Id (many-to-one; Cascade delete)

## Data Access
- **Method:** `PatientDataService.GetClinicalFlatRowsAsync(DateTime? fromDate, DateTime? toDate, int? minAge, int? maxAge, string? status)`
- **Query (plain English):**
  1. Load all TransplantEvents from the database with eager loading of: Provider, LabResults, Patient (with Patient.Facility, Patient.Diagnoses, Patient.Medications).
  2. Iterate each event in memory. For each event, apply filters in order:
     - If `fromDate` is provided and event's DateOfVisit < fromDate, skip.
     - If `toDate` is provided and event's DateOfVisit > toDate, skip.
     - Calculate patient's age. If `minAge` is provided and age < minAge, skip.
     - If `maxAge` is provided and age > maxAge, skip.
     - If `status` is provided, is not empty, and is not "All", and does not match the patient's Status (case-insensitive), skip.
  3. For each surviving event: compute PrimaryDiagnosis, ActiveMedCount, ProviderName, Specialty.
  4. If the event has lab results, emit one row per lab result (ordered by TestName), populating lab fields.
  5. If the event has no lab results, emit one row with null lab fields (LEFT JOIN semantics).
  6. No explicit ordering on the emitted rows (the iteration order depends on database default; the RDL orders by FacilityName, PatientName, DateOfVisit, LabTestName).
- **Projection / derived fields:**
  - `PatientName = Patient.FirstName + " " + Patient.LastName`
  - `ProviderName = Provider.FirstName + " " + Provider.LastName` (or `"-"` if Provider is null)
  - `Specialty = Provider.Specialty` (or `""` if Provider is null)
  - `PrimaryDiagnosis = PrimaryDiagnosis(patient)` -- selects the single diagnosis with the highest severity rank (Severe=3 > Moderate=2 > other=1), breaking ties by most recent DiagnosedDate; returns its Description, or `"-"` if no diagnoses exist.
  - `ActiveMedCount = patient.Medications.Count(m => m.IsActive)` -- count of medications where IsActive is true.
- **Read-only:** Yes.
- **Original query (verbatim, for reference):**
  ```csharp
  var events = await _context.TransplantEvents
      .AsNoTracking()
      .Include(e => e.Provider)
      .Include(e => e.LabResults)
      .Include(e => e.Patient).ThenInclude(p => p.Facility)
      .Include(e => e.Patient).ThenInclude(p => p.Diagnoses)
      .Include(e => e.Patient).ThenInclude(p => p.Medications)
      .ToListAsync();

  // Then in-memory filtering and projection per event, producing ClinicalFlatRow list.
  // One row per lab result; one row with null lab fields if event has no labs.
  ```

## Business Logic

### Derived fields (computed in the data service projection)
- **PatientName:** `Patient.FirstName + " " + Patient.LastName`
- **ProviderName:** `Provider.FirstName + " " + Provider.LastName`; falls back to `"-"` if Provider is null.
- **PrimaryDiagnosis:** The description of the patient's single most critical diagnosis. Selection logic: order all patient diagnoses by severity rank descending (Severe=3 > Moderate=2 > other=1), then by DiagnosedDate descending; take the first. Returns `"-"` if the patient has no diagnoses.
- **ActiveMedCount:** Count of the patient's medications where `IsActive == true`.

### Calculated fields (computed at render time, defined in the RDL)
These fields are NOT in ClinicalFlatRow. The JS template must compute them from the raw fields present in the row shape:
- **Age:** `Floor((today - DateOfBirth).TotalDays / 365.25)` -- integer years. Note: the data service uses a slightly different algorithm for filter purposes (`today.Year - dob.Year`, adjusted if birthday hasn't occurred yet), which is numerically equivalent in nearly all cases.
- **BMI:** `Round(WeightKg / (HeightCm / 100)^2, 1)` if HeightCm > 0; otherwise 0.
- **BmiCategory:** Categorical label from BMI value:
  - BMI = 0 -> "N/A"
  - BMI < 18.5 -> "Underweight"
  - BMI < 25 -> "Normal"
  - BMI < 30 -> "Overweight"
  - BMI >= 30 -> "Obese"
- **RiskScore:** Integer score computed per patient (not per row). Inputs: patient age, whether the patient has ANY inpatient event, and the total count of out-of-range lab results across all the patient's events.
  - Start at 0.
  - If age >= 65, add 2; else if age >= 45, add 1.
  - If the patient has at least one inpatient event, add 2.
  - Add the count of out-of-range lab results.
  - Result: a non-negative integer. The RDL uses >= 4 as "high risk" threshold.
- **DaysSincePreviousVisit:** `(DateOfVisit - DateOfPreviousVisit).Days` -- integer days between the event's visit date and its previous visit date.
- **LabFlag:** Per-row lab status flag:
  - If LabValue is null (no lab) -> empty string `""`.
  - If LabValue < RefLow or LabValue > RefHigh -> `"OUT"`.
  - Otherwise -> `"OK"`.

### Filters (applied in data service code before feeding rows)
- Visit date range: `fromDate <= DateOfVisit <= toDate` (inclusive).
- Age range: `minAge <= Age <= maxAge` (inclusive).
- Patient status: exact match on Patient.Status (case-insensitive); "All" or null/empty = no status filter.
- All filtering happens in `GetClinicalFlatRowsAsync` in memory after loading all events.

### Aggregations (in the RDL Facility Summary tablix, computed per facility group)
- **# Patients:** `CountDistinct(PatientId)` -- distinct patient count within the facility.
- **# Events:** `CountDistinct(EventId)` -- distinct event count within the facility.
- **Avg Age:** `Round(Avg(Age), 0)` -- average patient age, rounded to integer.
- **Inpatient Events:** `CountDistinct(IIF(IsInpatient, EventId, Nothing))` -- count of distinct events where IsInpatient is true.
- **Out-of-range Labs:** `Sum(IIF(LabFlag = "OUT", 1, 0))` -- total count of lab results flagged "OUT" within the facility.

### Legacy RDL expressions (decoded)
- **Filter echo textbox:** Concatenates parameter values into a readable string: "Filters - Visit dates: {FromDate MM/dd/yyyy} to {ToDate MM/dd/yyyy} | Age: {MinAge} to {MaxAge} | Patient status: {Status}".
- **Facility group banner:** `"Facility: " + FacilityName + " - " + FacilityCity + ", " + FacilityState`.
- **Patient group banner:** A long concatenation: "Patient: {PatientName} MRN: {MRN} Age: {Age} Sex: {Gender} BMI: {BMI} ({BmiCategory}) Risk: {RiskScore} Primary Dx: {PrimaryDiagnosis} Active meds: {ActiveMedCount}". Uses `First()` scoped to `grpPatient` for patient-level fields, and `Sum(IIF(...))` scoped to `grpPatient` for derived per-patient aggregates.
- **Provider display:** `ProviderName + " (" + Specialty + ")"`.
- **Setting display:** `IIF(IsInpatient, "Inpatient", "Outpatient")`.
- **Lab Test display:** `IIF(IsNothing(LabTestName), "-", LabTestName)`.
- **Lab Result display:** `IIF(IsNothing(LabValue), "-", CStr(LabValue) + " " + LabUnit)`.
- **Lab Reference display:** `IIF(IsNothing(RefLow), "-", CStr(RefLow) + " - " + CStr(RefHigh))`.
- **Footer left:** `"Generated: " + Format(Globals!ExecutionTime, "MM/dd/yyyy HH:mm") + " | Run by: " + Parameters!rptUser.Value`.
- **Footer right:** `"Page " + Globals!PageNumber + " of " + Globals!TotalPages`.

## Conditional Logic
- **Patient banner background color:** Red (`#f8d7da`) if RiskScore >= 4 (high risk); green (`#d1e7dd`) otherwise. The `PatientSummary.IsHighRisk` property also uses the >= 4 threshold.
- **Setting cell background:** Yellow (`#fff3cd`) if IsInpatient is true; otherwise alternating row color.
- **LabFlag cell text color/weight:** Red (`#b02a37`) bold if LabFlag = "OUT"; green (`#0f5132`) normal weight if "OK".
- **Facility Summary "Out-of-range Labs" cell:** Red (`#b02a37`) bold text if count > 0; black normal weight otherwise.
- **Detail row alternating colors:** Odd rows `#F2F2F2`, even rows White (based on `RowNumber("dsClinical") Mod 2`).

## Grouping & Sorting

### Facility Summary tablix
- **Grouping:** `grpFacSummary` on `FacilityName`.
- **Sorting:** By `FacilityName` ascending.

### Clinical Detail tablix (three-level nesting)
- **Level 1 -- Facility group (`grpFacility`):** Grouped by `FacilityName`, sorted by `FacilityName` ascending. Renders a full-width blue banner row with facility name, city, and state.
- **Level 2 -- Patient group (`grpPatient`):** Grouped by `PatientId`, sorted by `PatientName` ascending. Renders a full-width banner row with patient demographics and clinical metrics; background color conditional on risk score.
- **Level 3 -- Detail group (`grpDetail`):** Grouped by `EventId` + `LabTestName`, sorted by `DateOfVisit` ascending then `LabTestName` ascending. Renders the nine-column detail row.

### Data service ordering
- `GetClinicalFlatRowsAsync` does not apply an explicit `ORDER BY`; the event iteration follows database default order. Lab results within each event are ordered by `TestName` ascending.
- The RDL's SQL has `ORDER BY f.Name, p.LastName, te.DateOfVisit, lr.TestName` (not executed at runtime since data is fed, but documents the intended order).
- The JS template should sort rows by FacilityName, then PatientName, then DateOfVisit, then LabTestName to match the RDL's intended display order.

## Parameters

### User-facing filter parameters
| Name | Type | Control | Default | Filters what (how) |
|------|------|---------|---------|--------------------|
| FromDate | DateTime | date | 2026-01-01 | `TransplantEvents.DateOfVisit >= value` (applied in `GetClinicalFlatRowsAsync`) |
| ToDate | DateTime | date | 2026-12-31 | `TransplantEvents.DateOfVisit <= value` (applied in `GetClinicalFlatRowsAsync`) |
| MinAge | Integer | number | 0 | calculated patient `Age >= value` (applied in `GetClinicalFlatRowsAsync`) |
| MaxAge | Integer | number | 120 | calculated patient `Age <= value` (applied in `GetClinicalFlatRowsAsync`) |

### Parameters defined in RDL but not exposed as user filters in the HTML path
| Name | Type | Control | Default | Notes |
|------|------|---------|---------|--------------------|
| Status | String | select (All, Active, Inactive) | All | The RDL defines this with valid values and the data method accepts it, but the controller always passes `"All"`. Not exposed as a query-string parameter in either the HTML or RDL rendering path. |

### Chrome parameters (display only)
| Name | Type | Default | Used for |
|------|------|---------|----------|
| rptUser | String | "system" | Footer text: "Run by: {rptUser}". Set from `User.Identity.Name` in the RDL path. |

### Query-string keys accepted by the HTML endpoint
`fromDate`, `toDate`, `minAge`, `maxAge` (per `_CONTEXT.md` and the `HtmlReport` action signature).

## Layout

### Title
"Patient Clinical Summary Report" -- 16pt bold, dark navy (`#1f3864`), Segoe UI.

### Filter echo
Italic 9pt gray (`#595959`) text: "Filters - Visit dates: {FromDate MM/dd/yyyy} to {ToDate MM/dd/yyyy} | Age: {MinAge} to {MaxAge} | Patient status: {Status}".

### Facility Summary section
- **Section heading:** "Facility Summary" -- 12pt bold, dark navy.
- **Table columns (in order):**
  | # | Header | Width | Alignment | Content |
  |---|--------|-------|-----------|---------|
  | 1 | Facility | 2.4in | Left | FacilityName |
  | 2 | # Patients | 1.0in | Center | CountDistinct(PatientId) per facility |
  | 3 | # Events | 1.0in | Center | CountDistinct(EventId) per facility |
  | 4 | Avg Age | 1.0in | Center | Round(Avg(Age), 0) per facility |
  | 5 | Inpatient Events | 1.5in | Center | CountDistinct of EventId where IsInpatient per facility |
  | 6 | Out-of-range Labs | 1.6in | Center | Sum of LabFlag="OUT" rows per facility; **red bold if > 0** |
- **Header row style:** White text on dark background (`#212529`), solid light grey borders.

### Clinical Detail section
- **Section heading:** "Clinical Detail by Facility, Patient and Transplant Event" -- 12pt bold, dark navy.
- **Facility group banner:** Full-width (9 columns), light blue background (`#dbe5f1`), bold dark navy text: "Facility: {FacilityName} - {FacilityCity}, {FacilityState}".
- **Patient group banner:** Full-width (9 columns), background conditional on risk score (red `#f8d7da` if RiskScore >= 4, green `#d1e7dd` otherwise), bold text with patient demographics and clinical metrics.
- **Detail table columns (in order):**
  | # | Header | Width | Content | Formatting |
  |---|--------|-------|---------|------------|
  | 1 | Event | 0.9in | EventId | |
  | 2 | Visit Date | 0.9in | DateOfVisit | `MM/dd/yyyy` |
  | 3 | Provider | 1.4in | `ProviderName (Specialty)` | |
  | 4 | Donor | 0.9in | DonorType | |
  | 5 | Setting | 0.8in | `"Inpatient"` or `"Outpatient"` from IsInpatient bool | Yellow background (`#fff3cd`) if Inpatient |
  | 6 | Test | 1.1in | LabTestName, or `"-"` if null | |
  | 7 | Result | 0.9in | `"{LabValue} {LabUnit}"`, or `"-"` if null | |
  | 8 | Reference | 1.0in | `"{RefLow} - {RefHigh}"`, or `"-"` if null | |
  | 9 | Flag | 0.6in | LabFlag | Center-aligned; red (`#b02a37`) bold if "OUT", green (`#0f5132`) normal if "OK" |
- **Detail row style:** Header row is white text on dark (`#212529`). Data rows alternate `#F2F2F2` / White.

### Footer
- **Left:** "Generated: {execution time MM/dd/yyyy HH:mm} | Run by: {rptUser}" -- 8pt gray, Segoe UI.
- **Right:** "Page {N} of {Total}" -- 8pt gray, Segoe UI, right-aligned.

### Page dimensions
- Page: 9.5in x 11in (letter landscape-ish with margins); margins: 0.5in all sides; body width: 8.5in.

## Resolved Questions
1. **Sort order → JS sorts client-side.** Intended order: FacilityName ASC → PatientName ASC → DateOfVisit ASC → LabTestName ASC. Matches the RDL's SQL ORDER BY (which never executes at runtime).
2. **Status filter → not exposed.** The controller hardcodes `"All"` and the accepted filter keys are `fromDate, toDate, minAge, maxAge` only. Status filtering can be added post-PoC.
3. **RiskScore → per-patient aggregation in JS.** The JS must group rows by PatientId, check if any event has `isInpatient == true` (+2), count labs where `labValue < refLow || labValue > refHigh`, add age-based score (`age >= 65` → +2, `age >= 45` → +1). This is computed once per patient group, then applied to the patient banner row.
4. **Age calculation → calendar-year method.** Use `today.year - dob.year`, adjusted if birthday hasn't occurred yet. Matches the C# `CalculateAge` used for filter decisions — ensures consistency between what passes the age filter and what the report displays.
