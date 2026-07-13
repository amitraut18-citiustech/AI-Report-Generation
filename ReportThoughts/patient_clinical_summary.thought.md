# Report Thought: Patient Clinical Summary Report

**Report key:** patient_clinical_summary

## Source
- **Legacy format:** SSRS (.rdl) — **fully authored, NOT skeletal** (real multi-table SQL dataset, 6 report parameters, calculated fields, a custom VB `<Code>` block, two tablixes with nested grouping, and conditional formatting). **IMPORTANT:** the report is rendered with **host-fed data** — the RDL's SQL dataset (its `<CommandText>` and `WHERE`) does **not** execute at render time. The host (`RdlRenderService`) feeds a `DataTable` (from `ClinicalFlatRow` rows) plus report parameters into `LocalReport`, which then only lays out and computes the RDL's expression-level fields/aggregates. All row filtering happens in .NET **before** rendering.
- **Description:** A grouped clinical dashboard that, for a chosen visit-date window and patient age range, lists each facility with (a) a Facility Summary aggregate table and (b) a nested Facility → Patient → Transplant Event → Lab Result detail, enriched with calculated columns (Age, BMI + category, risk score, lab out-of-range flags) and risk/inpatient/out-of-range conditional formatting.
- **Source files:**
  | Role | File |
  |------|------|
  | RDL (layout + expressions; SQL dataset NOT executed) | DotNetApp/PatientReports/Reports/PatientClinicalSummaryReport.rdl |
  | Controller action (RDL path) | Controllers/ReportsController.cs → `RdlView("clinical", fromDate, toDate, minAge, maxAge)` |
  | Controller action (HTML path) | Controllers/ReportsController.cs → `HtmlReport("clinical", fromDate, toDate, minAge, maxAge)` |
  | Data service (AUTHORITATIVE filter + projection) | DataServices/PatientDataService.cs → `GetClinicalFlatRowsAsync(fromDate, toDate, minAge, maxAge, status)` |
  | Row DTO (fed-row contract — AUTHORITATIVE field list) | Models/ClinicalFlatRow.cs |
  | Fed-data renderer (why SQL WHERE never runs) | RdlRenderService/RdlRenderer.cs → `Render("clinical", …)` |
  | EF entities | Models/Patient.cs, Facility.cs, Provider.cs, Diagnosis.cs, Medication.cs, LabResult.cs, TransplantEvent.cs |
  | DbContext | Data/ApplicationDbContext.cs |
  | Alt. nested VM (PDF Download path only) | DataServices/PatientDataService.cs → `GetClinicalSummaryAsync()` / Models/ClinicalSummaryViewModel.cs |

## Database Context
- **Provider:** EF Core (DbContext = `ApplicationDbContext`; app runs on SQLite seed DB). The RDL dataset nominally targets SQL Server (`Data Source=(local);Initial Catalog=PatientReports`), but that connection is **not used at render time** — data is fed in.
- **Entities/tables used (via `GetClinicalFlatRowsAsync`):** `TransplantEvents` (root of the query), `.Include(Provider)`, `.Include(LabResults)`, `.Include(Patient).ThenInclude(Facility)`, `.Include(Patient).ThenInclude(Diagnoses)`, `.Include(Patient).ThenInclude(Medications)`.
- **Fields (from `ClinicalFlatRow` — AUTHORITATIVE fed-row contract):**

  Fed columns (serialized camelCase into `window.REPORT_DATA`; `Mrn` remaps to RDL column `MRN`):
  | Field | .NET type | Direct / derived | Meaning |
  |-------|-----------|------------------|---------|
  | FacilityName | string | direct (Facility.Name) | Facility name (grouping key) |
  | FacilityCity | string | direct (Facility.City) | Facility city |
  | FacilityState | string | direct (Facility.State) | Facility 2-char state |
  | PatientId | int | direct (Patient.Id) | Patient PK (grouping key) |
  | Mrn | string | direct (Patient.MRN) | Medical record number (→ RDL `MRN`) |
  | PatientName | string | derived (`p.FirstName + " " + p.LastName`) | Patient full name |
  | Gender | string | direct (Patient.Gender) | Sex |
  | DateOfBirth | DateTime | direct (Patient.DateOfBirth) | DOB (feeds Age) |
  | HeightCm | double | direct (Patient.HeightCm) | Height cm (feeds BMI) |
  | WeightKg | double | direct (Patient.WeightKg) | Weight kg (feeds BMI) |
  | Status | string | direct (Patient.Status) | Active/Inactive |
  | EventId | string | direct (TransplantEvent.EventId) | Event identifier (grouping key) |
  | DonorType | string | direct (TransplantEvent.DonorType) | Autologous/Allogeneic |
  | DateOfVisit | DateTime | direct (TransplantEvent.DateOfVisit) | Visit date (filtered + sort key) |
  | DateOfPreviousVisit | DateTime | direct (TransplantEvent.DateOfPreviousVisit) | Prior visit (feeds DaysSincePreviousVisit) |
  | IsInpatient | bool | direct (TransplantEvent.IsInpatient) | Inpatient flag |
  | ProviderName | string | derived (`Provider.FirstName + " " + Provider.LastName`, else `"-"`) | Attending provider |
  | Specialty | string | direct (Provider.Specialty, else `""`) | Provider specialty |
  | PrimaryDiagnosis | string | derived (see Data Access) | Highest-severity, most-recent diagnosis description |
  | ActiveMedCount | int | derived (`Medications.Count(m => m.IsActive)`) | Count of active medications |
  | LabTestName | string? | direct (LabResult.TestName; null when event has no labs) | Lab test name |
  | LabValue | double? | direct (LabResult.Value; null when no labs) | Lab result value |
  | LabUnit | string? | direct (LabResult.Unit; null when no labs) | Lab unit |
  | RefLow | double? | direct (LabResult.ReferenceLow; null when no labs) | Reference range low |
  | RefHigh | double? | direct (LabResult.ReferenceHigh; null when no labs) | Reference range high |

  > **Dropped vs. earlier thought file:** `TransplantNumber`, `TransplantDate`, `InfusionDate`, `DischargeDate`, and `LabTakenDate` are **no longer part of the fed row set** — they are absent from `ClinicalFlatRow` and from the current RDL dataset. Do not carry them into the migration.

  Calculated RDL fields (RDL `<Field><Value>` expressions, evaluated per row at render time from the fed columns above):
  | Field | Type | Formula (RDL VB expression) | Meaning |
  |-------|------|-----------------------------|---------|
  | Age | int | `=Floor(DateDiff(DateInterval.Day, DateOfBirth, Today()) / 365.25)` | Age in whole years (for display/aggregates) |
  | BMI | double | `=IIF(HeightCm > 0, Round(WeightKg / ((HeightCm/100)*(HeightCm/100)), 1), 0)` | BMI to 1 decimal; 0 when height missing |
  | DaysSincePreviousVisit | int | `=DateDiff(DateInterval.Day, DateOfPreviousVisit, DateOfVisit)` | Days between prior and current visit (**computed but not placed in any RDL cell**) |
  | LabFlag | string | `=IIF(IsNothing(LabValue), "", IIF(LabValue < RefLow Or LabValue > RefHigh, "OUT", "OK"))` | "OUT" if out of reference range, "OK" if in range, "" if no lab |

- **Relationships (from DbContext):**
  - Patient.FacilityId → Facility.Id (many-to-one, `OnDelete=Restrict`).
  - Provider.FacilityId → Facility.Id (many-to-one, `OnDelete=Restrict`).
  - TransplantEvent.PatientId → Patient.Id (many-to-one, `OnDelete=Cascade`).
  - TransplantEvent.ProviderId → Provider.Id (many-to-one, `OnDelete=Restrict`).
  - Diagnosis.PatientId → Patient.Id (many-to-one, `OnDelete=Cascade`).
  - Medication.PatientId → Patient.Id (many-to-one, `OnDelete=Cascade`).
  - LabResult.TransplantEventId → TransplantEvent.Id (many-to-one, `OnDelete=Cascade`).

## Data Access
- **Method (AUTHORITATIVE):** `PatientDataService.GetClinicalFlatRowsAsync(DateTime? fromDate, DateTime? toDate, int? minAge, int? maxAge, string? status)` — async, `AsNoTracking()`.
- **Query (plain English):** Load all `TransplantEvents` with `Provider`, `LabResults`, and `Patient` (+ that patient's `Facility`, `Diagnoses`, `Medications`) eagerly, into memory. Then, **in C#**, for each event:
  1. Skip if `fromDate` set and `DateOfVisit < fromDate`.
  2. Skip if `toDate` set and `DateOfVisit > toDate`.
  3. Compute `patientAge = CalculateAge(DateOfBirth)` (calendar-based); skip if `minAge` set and `patientAge < minAge`; skip if `maxAge` set and `patientAge > maxAge`.
  4. Skip if `status` set and not `"All"` and `Patient.Status` != status (case-insensitive).
  Then flatten: if the event has any labs, emit **one row per lab** (ordered by `TestName`) with the lab columns filled; otherwise emit **one row** with the lab columns null (LEFT-JOIN semantics).
- **Filtering happens here, not in the RDL.** The RDL SQL `WHERE te.DateOfVisit BETWEEN @FromDate AND @ToDate AND (@Status='All' OR p.Status=@Status)` is dead code at render time. Also note **age filtering is purely a .NET construct** — MinAge/MaxAge are not referenced by the (unused) SQL at all.
- **Projection / derived fields:**
  - `PatientName = p.FirstName + " " + p.LastName`.
  - `ProviderName = e.Provider != null ? Provider.FirstName + " " + Provider.LastName : "-"`; `Specialty = e.Provider?.Specialty ?? ""`.
  - `PrimaryDiagnosis(p)`: from the patient's diagnoses, order by severity rank (`Severe`=3, `Moderate`=2, else 1) descending, then `DiagnosedDate` descending, take first `Description`; `"-"` if none.
  - `ActiveMedCount = p.Medications.Count(m => m.IsActive)`.
- **Read-only:** yes (`AsNoTracking()`).
- **Original filter logic (verbatim, for reference):**
  ```csharp
  if (fromDate.HasValue && e.DateOfVisit < fromDate.Value) continue;
  if (toDate.HasValue && e.DateOfVisit > toDate.Value) continue;
  var patientAge = CalculateAge(p.DateOfBirth);
  if (minAge.HasValue && patientAge < minAge.Value) continue;
  if (maxAge.HasValue && patientAge > maxAge.Value) continue;
  if (!string.IsNullOrEmpty(status) && status != "All" &&
      !string.Equals(p.Status, status, StringComparison.OrdinalIgnoreCase)) continue;
  ```
- **Controller wiring (both RDL and HTML paths):** parse `fromDate`→default `2026-01-01`, `toDate`→default `2026-12-31`, `minAge`→default `0`, `maxAge`→default `120`; call `GetClinicalFlatRowsAsync(from, to, minA, maxA, "All")`; echo the resolved values back as report parameters (`FromDate`, `ToDate`, `MinAge`, `MaxAge`, `Status="All"`, `rptUser=User.Identity.Name ?? "system"`).
- **RDL SQL (reference only — NOT executed):**
  ```sql
  SELECT f.Name AS FacilityName, f.City AS FacilityCity, f.State AS FacilityState,
      p.Id AS PatientId, p.MRN, (p.FirstName + ' ' + p.LastName) AS PatientName,
      p.Gender, p.DateOfBirth, p.HeightCm, p.WeightKg, p.Status,
      te.EventId, te.DonorType, te.DateOfVisit, te.DateOfPreviousVisit, te.IsInpatient,
      (pr.FirstName + ' ' + pr.LastName) AS ProviderName, pr.Specialty,
      (SELECT TOP 1 d.Description FROM Diagnoses d WHERE d.PatientId = p.Id
          ORDER BY CASE d.Severity WHEN 'Severe' THEN 3 WHEN 'Moderate' THEN 2 ELSE 1 END DESC, d.DiagnosedDate DESC) AS PrimaryDiagnosis,
      (SELECT COUNT(*) FROM Medications m WHERE m.PatientId = p.Id AND m.IsActive = 1) AS ActiveMedCount,
      lr.TestName AS LabTestName, lr.Value AS LabValue, lr.Unit AS LabUnit,
      lr.ReferenceLow AS RefLow, lr.ReferenceHigh AS RefHigh
  FROM Patients p
      INNER JOIN Facilities f ON f.Id = p.FacilityId
      INNER JOIN TransplantEvents te ON te.PatientId = p.Id
      INNER JOIN Providers pr ON pr.Id = te.ProviderId
      LEFT JOIN LabResults lr ON lr.TransplantEventId = te.Id
  WHERE te.DateOfVisit BETWEEN @FromDate AND @ToDate
      AND (@Status = 'All' OR p.Status = @Status)
  ORDER BY f.Name, p.LastName, te.DateOfVisit, lr.TestName
  ```

## Business Logic
- **Filtering (applied in .NET before render — see Data Access):** visit-date window (`DateOfVisit` between FromDate and ToDate inclusive), patient age range (`Age` between MinAge and MaxAge inclusive), and patient status (currently always `"All"` = no status filter).
- **Custom VB `<Code>` functions** (embedded in the RDL; must be reproduced in JS):
  - `BmiCategory(bmi As Double) As String`: `0 → "N/A"`; `< 18.5 → "Underweight"`; `< 25 → "Normal"`; `< 30 → "Overweight"`; else `"Obese"`.
  - `RiskScore(age As Integer, inpatient As Boolean, outOfRangeLabs As Integer) As Integer`: start `score=0`; if `age>=65` +2, else if `age>=45` +1; if `inpatient` +2; then `score += outOfRangeLabs`. ("High risk" = `RiskScore >= 4`.)
- **Facility Summary aggregates** (per facility group `grpFacSummary`, one row per facility):
  - `# Patients = CountDistinct(PatientId)`
  - `# Events = CountDistinct(EventId)`
  - `Avg Age = Round(Avg(Age), 0)`
  - `Inpatient Events = CountDistinct(IIF(IsInpatient, EventId, Nothing))` (distinct events flagged inpatient)
  - `Out-of-range Labs = Sum(IIF(LabFlag = "OUT", 1, 0))`
- **Patient banner aggregates** — scoped to `grpPatient` via `First(…,"grpPatient")` / `Sum(…,"grpPatient")`:
  - Shows `First(PatientName)`, `First(MRN)`, `First(Age)`, `First(Gender)`, `First(BMI)` + `Code.BmiCategory(First(BMI))`, `First(PrimaryDiagnosis)`, `First(ActiveMedCount)`.
  - Risk value = `Code.RiskScore(First(Age,"grpPatient"), Sum(IIF(IsInpatient,1,0),"grpPatient") > 0, Sum(IIF(LabFlag="OUT",1,0),"grpPatient"))` — patient age, whether ANY event was inpatient, and the patient's total out-of-range lab count.
- **Formatting expressions:**
  - Visit date: `=Format(DateOfVisit, "MM/dd/yyyy")`.
  - Provider cell: `=ProviderName & " (" & Specialty & ")"`.
  - Setting cell: `=IIF(IsInpatient, "Inpatient", "Outpatient")`.
  - Test cell: `=IIF(IsNothing(LabTestName), "-", LabTestName)`.
  - Result cell: `=IIF(IsNothing(LabValue), "-", CStr(LabValue) & " " & LabUnit)`.
  - Reference cell: `=IIF(IsNothing(RefLow), "-", CStr(RefLow) & " - " & CStr(RefHigh))`.
  - Facility band: `="Facility:  " & FacilityName & "   -   " & FacilityCity & ", " & FacilityState`.
  - **Filter echo (top), now includes the age line:** `="Filters  -  Visit dates: " & Format(FromDate,"MM/dd/yyyy") & " to " & Format(ToDate,"MM/dd/yyyy") & "     |     Age: " & MinAge & " to " & MaxAge & "     |     Patient status: " & Status`.
  - Footer: `="Generated: " & Format(Globals!ExecutionTime, "MM/dd/yyyy HH:mm") & "     |     Run by: " & rptUser` and `="Page " & Globals!PageNumber & " of " & Globals!TotalPages`.

## Conditional Logic
Conditional-formatting rules (from RDL cell `<Style>` expressions):
1. **Zebra striping (all detail cells):** background `=IIF(RowNumber("dsClinical") Mod 2 = 1, "#F2F2F2", "White")`.
2. **Facility Summary "Out-of-range Labs" cell (`sOor`):** if `Sum(IIF(LabFlag="OUT",1,0)) > 0` → Color `#b02a37`, FontWeight Bold; else Black, Normal.
3. **Patient banner background (`bPatient`):** `=IIF(RiskScore >= 4, "#f8d7da" (red-subtle), "#d1e7dd" (green-subtle))`, where RiskScore is the `Code.RiskScore(...)` call above.
4. **Detail "Setting" cell background (`dSetting`):** `=IIF(IsInpatient, "#fff3cd", <zebra color>)` — inpatient events highlighted yellow, otherwise the row's zebra color.
5. **Detail "Flag" cell (`dFlag`):** if `LabFlag = "OUT"` → Color `#b02a37`, Bold; else Color `#0f5132` (green), Normal.

## Grouping & Sorting
- **Facility Summary tablix (`FacilitySummary`):** row group `grpFacSummary` on `=FacilityName`, sorted by FacilityName. One row per facility; header repeats on new page.
- **Clinical Detail tablix (`ClinicalDetail`) — three-level nested row hierarchy:**
  1. `grpFacility` on `=FacilityName`, sort by FacilityName → full-width (`ColSpan=9`) facility band row.
  2. `grpPatient` on `=PatientId`, sort by PatientName → full-width (`ColSpan=9`) patient banner row (risk-colored).
  3. `grpDetail` on `=EventId` + `=LabTestName`, sort by DateOfVisit then LabTestName → the 9-column detail row (one per lab, or one per event with no labs).
- **Fed-row order:** rows arrive already flattened; within an event the labs are ordered by `TestName` in the data service. The RDL then re-sorts per its group/sort expressions.
- Detail column headers repeat on new page (`RepeatOnNewPage=true`).

## Parameters
The RDL declares **6** parameters. Four are the **user filters**; `Status` is currently fixed by the host; `rptUser` is chrome. Filtering is applied by the host (`GetClinicalFlatRowsAsync`) against the fed data — the RDL's SQL `WHERE` does not run.

| Name | Type | Control | Default | Filters what (how) |
|------|------|---------|---------|--------------------|
| FromDate | DateTime | date | 2026-01-01 | Visit-date lower bound — keep row if `DateOfVisit >= FromDate` |
| ToDate | DateTime | date | 2026-12-31 | Visit-date upper bound — keep row if `DateOfVisit <= ToDate` |
| MinAge | Integer | number | 0 | Patient age lower bound — keep row if patient `Age >= MinAge` |
| MaxAge | Integer | number | 120 | Patient age upper bound — keep row if patient `Age <= MaxAge` |

- **Status** (String; RDL valid values All/Active/Inactive; default `All`): **currently NOT user-facing** — the controller hard-codes `"All"` when calling the data service, so no status filtering occurs today. `All` = no filter; a specific value would keep only patients whose `Status` matches (case-insensitive). Wired for future use.
- **rptUser** (String, Hidden, nullable): **chrome only** — printed in the footer "Run by:". Set to the current user (`User.Identity.Name`) or `"system"`. Not a filter.

> Note on age: MinAge/MaxAge filter on the **calendar-based** `CalculateAge(DateOfBirth)` computed in .NET (today − DOB, adjusted for birthday). The RDL's display `Age` field uses `Floor(DateDiff(Day, DOB, Today)/365.25)`; the two can differ by ~1 year near birthdays. The .NET calendar age governs which rows pass the filter.

Parameter layout: a single-row **6-column** grid (FromDate, ToDate, Status, rptUser, MinAge, MaxAge); Status, rptUser, MinAge, MaxAge are marked `Hidden` in the RDL grid (the host supplies their values).

## Layout
- **Title:** "Patient Clinical Summary Report" (Segoe UI, 16pt bold, `#1f3864`).
- **Filter echo strip:** italic 9pt gray line echoing Visit dates, Age range, and Patient status (see Business Logic).
- **Summary / cards:** "Facility Summary" section — one aggregate row per facility. Table columns (header row bg `#212529`, white bold):
  1. Facility — `=FacilityName`
  2. # Patients — `CountDistinct(PatientId)` (center)
  3. # Events — `CountDistinct(EventId)` (center)
  4. Avg Age — `Round(Avg(Age),0)` (center)
  5. Inpatient Events — `CountDistinct(IIF(IsInpatient,EventId,Nothing))` (center)
  6. Out-of-range Labs — `Sum(IIF(LabFlag="OUT",1,0))` (center; conditional red/bold)
- **Detail section:** "Clinical Detail by Facility, Patient and Transplant Event". Per facility group:
  - Facility band row (full width, bg `#dbe5f1`, text `#1f3864` bold).
  - Per patient: banner row (full width; red/green background by risk) showing Patient, MRN, Age, Sex, BMI (category), Risk score, Primary Dx, Active meds.
  - Detail rows under a header (bg `#212529`, white bold), columns in order:
    1. Event — `=EventId`
    2. Visit Date — `=Format(DateOfVisit,"MM/dd/yyyy")`
    3. Provider — `=ProviderName & " (" & Specialty & ")"`
    4. Donor — `=DonorType`
    5. Setting — Inpatient/Outpatient (conditional yellow highlight if inpatient)
    6. Test — LabTestName or "-"
    7. Result — `LabValue + " " + LabUnit` or "-"
    8. Reference — `RefLow " - " RefHigh` or "-"
    9. Flag — LabFlag (conditional red-bold "OUT" / green "OK")
- **Per-column formatting:** dates `MM/dd/yyyy`; numeric aggregates rounded; nulls rendered "-"; zebra striping + conditional colors as under Conditional Logic.
- **Header/Footer:** No page header. Page footer on all pages: left = "Generated: {ExecutionTime MM/dd/yyyy HH:mm}  |  Run by: {rptUser}"; right = "Page {PageNumber} of {TotalPages}". Page: Letter (9.5in × 11in per RDL page size), 0.5in margins.

## Open Questions
- **Detail grain / event-metadata repetition:** `grpDetail` groups by `EventId + LabTestName`, so event columns (Event, Visit, Provider, Donor, Setting) repeat on every lab row of an event. Confirm the migrated HTML should reproduce this flat per-lab repetition (vs. showing event metadata once with labs nested).
- **Age method for the filter vs. display:** filtering uses the .NET calendar age; the RDL display `Age` uses `Floor(DateDiff/365.25)`. Confirm both behaviors should be preserved as-is (they can differ by ~1 year near birthdays).
- **Status parameter:** declared with valid values All/Active/Inactive but currently hard-coded to `"All"` by the controller (not user-facing). Confirm it should remain fixed, or be exposed as a fifth user filter in the migrated report.
- **`DaysSincePreviousVisit`** is computed as an RDL field but not placed in any RDL cell. Confirm it should be omitted from the migrated layout (it is not surfaced anywhere in the current RDL).
- **SSRS-runtime constructs** (`Code.BmiCategory`/`Code.RiskScore`, scoped `First(…,"grpPatient")`/`Sum(…,"grpPatient")`, `CountDistinct`, and `CountDistinct(IIF(IsInpatient, EventId, Nothing))` which counts distinct EventIds only among inpatient rows) must be faithfully re-implemented in JS with correct per-patient vs. per-facility scoping — the most error-prone part of the migration.
