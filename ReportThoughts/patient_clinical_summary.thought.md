# Report Thought: Patient Clinical Summary Report

**Report key:** patient_clinical_summary

## Source
- **Legacy format:** SSRS (.rdl) — **fully authored, NOT skeletal.** The `.rdl` is the primary source of logic (real multi-table SQL dataset, report parameters, calculated fields, a custom VB `<Code>` block, two tablixes with nested grouping, and conditional formatting). A parallel .NET MVC rendering (data service + ViewModel + Razor partial) exists and corroborates the intended runtime shape.
- **Description:** A grouped clinical dashboard that, for a visit-date window and patient-status filter, lists every facility with (a) a Facility Summary aggregate table and (b) a nested Facility → Patient → Transplant Event → Lab Result detail, enriched with calculated columns (Age, BMI + category, risk score, lab out-of-range flags) and risk/inpatient/out-of-range conditional formatting.
- **Source files:**
  | Role | File |
  |------|------|
  | RDL (PRIMARY — full definition) | DotNetApp/PatientReports/Reports/PatientClinicalSummaryReport.rdl |
  | Controller action | Controllers/ReportsController.cs → Index("clinical") and Download("clinical") |
  | Data service | DataServices/PatientDataService.cs → GetClinicalSummaryAsync() |
  | ViewModel | Models/ClinicalSummaryViewModel.cs (FacilitySummary, PatientSummary, EventSummary, LabSummary) |
  | EF entities | Models/Patient.cs, Facility.cs, Provider.cs, Diagnosis.cs, Medication.cs, LabResult.cs, TransplantEvent.cs |
  | DbContext | Data/ApplicationDbContext.cs |
  | Razor view | Views/Reports/_ClinicalSummary.cshtml |

## Database Context
- **Provider:** EF Core (DbContext = ApplicationDbContext). The RDL dataset targets SQL Server directly (`ConnectString: Data Source=(local);Initial Catalog=PatientReports;Integrated Security=SSPI`, `DataProvider=SQL`).
- **Entities/tables used:** Patients (root), Facilities, Providers, TransplantEvents, LabResults (LEFT), plus correlated subqueries into Diagnoses and Medications.
- **Fields (from the RDL dataset `dsClinical` — authoritative for this report; the ViewModel mirrors it):**

  Direct/query columns:
  | Field | .NET type | Direct / derived | Meaning |
  |-------|-----------|------------------|---------|
  | FacilityName | string | direct (Facilities.Name) | Facility name |
  | FacilityCity | string | direct (Facilities.City) | Facility city |
  | FacilityState | string | direct (Facilities.State) | Facility 2-char state |
  | PatientId | int | direct (Patients.Id) | Patient PK (grouping key) |
  | MRN | string | direct (Patients.MRN) | Medical record number |
  | PatientName | string | derived (`p.FirstName + ' ' + p.LastName`) | Patient full name |
  | Gender | string | direct (Patients.Gender) | Sex |
  | DateOfBirth | DateTime | direct (Patients.DateOfBirth) | DOB (feeds Age) |
  | HeightCm | double | direct (Patients.HeightCm) | Height cm (feeds BMI) |
  | WeightKg | double | direct (Patients.WeightKg) | Weight kg (feeds BMI) |
  | Status | string | direct (Patients.Status) | Active/Inactive (filtered) |
  | EventId | string | direct (TransplantEvents.EventId) | Event identifier (grouping key) |
  | TransplantNumber | string | direct (TransplantEvents.TransplantNumber) | Transplant number |
  | DonorType | string | direct (TransplantEvents.DonorType) | Autologous/Allogeneic |
  | DateOfVisit | DateTime | direct (TransplantEvents.DateOfVisit) | Visit date (filtered, sort) |
  | DateOfPreviousVisit | DateTime | direct (TransplantEvents.DateOfPreviousVisit) | Prior visit (feeds DaysSincePreviousVisit) |
  | TransplantDate | DateTime | direct (TransplantEvents.TransplantDate) | Transplant date (selected, not displayed) |
  | InfusionDate | DateTime | direct (TransplantEvents.InfusionDate) | Infusion date (selected, not displayed) |
  | DischargeDate | DateTime? | direct (TransplantEvents.DischargeDate) | Discharge date (selected, not displayed) |
  | IsInpatient | bool | direct (TransplantEvents.IsInpatient) | Inpatient flag |
  | ProviderName | string | derived (`pr.FirstName + ' ' + pr.LastName`) | Attending provider full name |
  | Specialty | string | direct (Providers.Specialty) | Provider specialty |
  | PrimaryDiagnosis | string | derived (correlated subquery, see Business Logic) | Highest-severity, most-recent diagnosis description |
  | ActiveMedCount | int | derived (correlated subquery COUNT) | Count of active medications |
  | LabTestName | string | direct (LabResults.TestName) | Lab test name (nullable via LEFT JOIN) |
  | LabValue | double | direct (LabResults.Value) | Lab result value (nullable) |
  | LabUnit | string | direct (LabResults.Unit) | Lab unit |
  | RefLow | double | direct (LabResults.ReferenceLow) | Reference range low |
  | RefHigh | double | direct (LabResults.ReferenceHigh) | Reference range high |
  | LabTakenDate | DateTime | direct (LabResults.TakenDate) | Lab draw date (selected, not displayed) |

  Calculated report Fields (RDL `<Field><Value>` expressions, evaluated per row):
  | Field | .NET type | Formula (RDL VB expression) | Meaning |
  |-------|-----------|-----------------------------|---------|
  | Age | int | `=Floor(DateDiff(DateInterval.Day, DateOfBirth, Today()) / 365.25)` | Age in whole years (day-diff / 365.25, floored) |
  | BMI | double | `=IIF(HeightCm > 0, Round(WeightKg / ((HeightCm/100)*(HeightCm/100)), 1), 0)` | BMI to 1 decimal; 0 when height missing |
  | DaysSincePreviousVisit | int | `=DateDiff(DateInterval.Day, DateOfPreviousVisit, DateOfVisit)` | Days between prior and current visit (**computed but NOT placed in any RDL cell**; it IS rendered in the .NET Razor) |
  | LabFlag | string | `=IIF(IsNothing(LabValue), "", IIF(LabValue < RefLow Or LabValue > RefHigh, "OUT", "OK"))` | "OUT" if outside reference range, "OK" if in range, "" if no lab |

- **Relationships (from DbContext):**
  - Patient.FacilityId → Facility.Id (many-to-one, `OnDelete=Restrict`).
  - Provider.FacilityId → Facility.Id (many-to-one, `OnDelete=Restrict`).
  - TransplantEvent.PatientId → Patient.Id (many-to-one, `OnDelete=Cascade`).
  - TransplantEvent.ProviderId → Provider.Id (many-to-one, `OnDelete=Restrict`).
  - Diagnosis.PatientId → Patient.Id (many-to-one, `OnDelete=Cascade`).
  - Medication.PatientId → Patient.Id (many-to-one, `OnDelete=Cascade`).
  - LabResult.TransplantEventId → TransplantEvent.Id (many-to-one, `OnDelete=Cascade`).

## Data Access
- **Method (authoritative — RDL dataset `dsClinical`):** a single parameterized SQL statement.
- **Query (plain English):** Start from `Patients p`. INNER JOIN `Facilities f` on `f.Id = p.FacilityId`; INNER JOIN `TransplantEvents te` on `te.PatientId = p.Id`; INNER JOIN `Providers pr` on `pr.Id = te.ProviderId`; **LEFT JOIN** `LabResults lr` on `lr.TransplantEventId = te.Id`. Because of the INNER JOINs, patients with no transplant events (or events with no provider) are excluded; the LEFT JOIN keeps events that have no labs (one row with null lab columns). One row is produced per lab result (or one row per event when the event has no labs). WHERE: `te.DateOfVisit BETWEEN @FromDate AND @ToDate` AND `(@Status = 'All' OR p.Status = @Status)`. ORDER BY `f.Name, p.LastName, te.DateOfVisit, lr.TestName`.
- **Two correlated subqueries per patient row:**
  - `PrimaryDiagnosis = (SELECT TOP 1 d.Description FROM Diagnoses d WHERE d.PatientId = p.Id ORDER BY CASE d.Severity WHEN 'Severe' THEN 3 WHEN 'Moderate' THEN 2 ELSE 1 END DESC, d.DiagnosedDate DESC)` — the description of the patient's most severe, then most recently diagnosed, condition.
  - `ActiveMedCount = (SELECT COUNT(*) FROM Medications m WHERE m.PatientId = p.Id AND m.IsActive = 1)` — number of active medications.
- **Read-only:** Reporting query (SELECT only). The corroborating .NET service uses `AsNoTracking()`.
- **Verbatim SQL (RDL `<CommandText>`):**
  ```sql
  SELECT
      f.Name AS FacilityName, f.City AS FacilityCity, f.State AS FacilityState,
      p.Id AS PatientId, p.MRN, (p.FirstName + ' ' + p.LastName) AS PatientName,
      p.Gender, p.DateOfBirth, p.HeightCm, p.WeightKg, p.Status,
      te.EventId, te.TransplantNumber, te.DonorType, te.DateOfVisit, te.DateOfPreviousVisit,
      te.TransplantDate, te.InfusionDate, te.DischargeDate, te.IsInpatient,
      (pr.FirstName + ' ' + pr.LastName) AS ProviderName, pr.Specialty,
      (SELECT TOP 1 d.Description FROM Diagnoses d WHERE d.PatientId = p.Id
          ORDER BY CASE d.Severity WHEN 'Severe' THEN 3 WHEN 'Moderate' THEN 2 ELSE 1 END DESC, d.DiagnosedDate DESC) AS PrimaryDiagnosis,
      (SELECT COUNT(*) FROM Medications m WHERE m.PatientId = p.Id AND m.IsActive = 1) AS ActiveMedCount,
      lr.TestName AS LabTestName, lr.Value AS LabValue, lr.Unit AS LabUnit,
      lr.ReferenceLow AS RefLow, lr.ReferenceHigh AS RefHigh, lr.TakenDate AS LabTakenDate
  FROM Patients p
      INNER JOIN Facilities f ON f.Id = p.FacilityId
      INNER JOIN TransplantEvents te ON te.PatientId = p.Id
      INNER JOIN Providers pr ON pr.Id = te.ProviderId
      LEFT JOIN LabResults lr ON lr.TransplantEventId = te.Id
  WHERE te.DateOfVisit BETWEEN @FromDate AND @ToDate
      AND (@Status = 'All' OR p.Status = @Status)
  ORDER BY f.Name, p.LastName, te.DateOfVisit, lr.TestName
  ```
- **Corroborating .NET LINQ (GetClinicalSummaryAsync):** loads `Facilities` with `.Include` graph `Patients → TransplantEvents → Provider`, `Patients → TransplantEvents → LabResults`, `Patients → Diagnoses`, `Patients → Medications`, ordered by `Name`; then builds the grouped model in memory (per-patient Age/BMI/BmiCategory/RiskScore, per-facility aggregates). **Note:** the .NET version applies **no date-range or status filter** — it materializes ALL facilities/patients/events — unlike the RDL SQL. The RDL is authoritative for filtering.

## Business Logic
- **Filtering:** rows limited to visits with `DateOfVisit BETWEEN @FromDate AND @ToDate`; patients limited to `@Status` unless `@Status = 'All'`.
- **Custom VB `<Code>` functions** (embedded in the RDL, exact logic):
  - `BmiCategory(bmi As Double) As String`: `0 → "N/A"`; `< 18.5 → "Underweight"`; `< 25 → "Normal"`; `< 30 → "Overweight"`; else `"Obese"`.
  - `RiskScore(age As Integer, inpatient As Boolean, outOfRangeLabs As Integer) As Integer`: start `score = 0`; if `age >= 65` add 2, else if `age >= 45` add 1; if `inpatient` add 2; then `score += outOfRangeLabs`; return score. (A patient is "high risk" at `RiskScore >= 4`.)
- **Facility Summary aggregates** (per facility group `grpFacSummary`, one row per facility):
  - `# Patients = CountDistinct(PatientId)`
  - `# Events = CountDistinct(EventId)`
  - `Avg Age = Round(Avg(Age), 0)`
  - `Inpatient Events = CountDistinct(IIF(IsInpatient, EventId, Nothing))` (distinct events flagged inpatient)
  - `Out-of-range Labs = Sum(IIF(LabFlag = "OUT", 1, 0))` (count of out-of-range lab rows)
- **Patient banner (detail tablix) aggregates** — scoped to `grpPatient` via `First(..., "grpPatient")` and `Sum(..., "grpPatient")`:
  - Displays `First(PatientName)`, `First(MRN)`, `First(Age)`, `First(Gender)`, `First(BMI)` + `Code.BmiCategory(First(BMI))`, `First(PrimaryDiagnosis)`, `First(ActiveMedCount)`.
  - Risk value = `Code.RiskScore(First(Age,"grpPatient"), Sum(IIF(IsInpatient,1,0),"grpPatient") > 0, Sum(IIF(LabFlag="OUT",1,0),"grpPatient"))` — i.e. patient age, whether ANY event was inpatient, and the patient's total out-of-range lab count.
- **Formatting expressions:**
  - Visit date: `=Format(DateOfVisit, "MM/dd/yyyy")`.
  - Provider cell: `=ProviderName & " (" & Specialty & ")"`.
  - Setting cell: `=IIF(IsInpatient, "Inpatient", "Outpatient")`.
  - Test cell: `=IIF(IsNothing(LabTestName), "-", LabTestName)`.
  - Result cell: `=IIF(IsNothing(LabValue), "-", CStr(LabValue) & " " & LabUnit)`.
  - Reference cell: `=IIF(IsNothing(RefLow), "-", CStr(RefLow) & " - " & CStr(RefHigh))`.
  - Facility band: `="Facility:  " & FacilityName & "   -   " & FacilityCity & ", " & FacilityState`.
  - Filter echo (top): `="Filters  -  Visit dates: " & Format(FromDate,"MM/dd/yyyy") & " to " & Format(ToDate,"MM/dd/yyyy") & "     |     Patient status: " & Status`.
  - Footer: `="Generated: " & Format(Globals!ExecutionTime, "MM/dd/yyyy HH:mm") & "     |     Run by: " & rptUser` and `="Page " & Globals!PageNumber & " of " & Globals!TotalPages`.

## Conditional Logic
Four conditional-formatting rules (all from RDL cell `<Style>` expressions):
1. **Facility Summary "Out-of-range Labs" cell (`sOor`):** if `Sum(IIF(LabFlag="OUT",1,0)) > 0` → Color `#b02a37` and FontWeight Bold; else Color Black, Normal.
2. **Patient banner row background (`bPatient`):** `=IIF(RiskScore >= 4, "#f8d7da" (red-subtle), "#d1e7dd" (green-subtle))` where RiskScore is the `Code.RiskScore(...)` call above. (Razor equivalent: `bg-danger-subtle` vs `bg-success-subtle` on `IsHighRisk = RiskScore >= 4`.)
3. **Detail "Setting" cell background (`dSetting`):** `=IIF(IsInpatient, "#fff3cd" (yellow highlight), "Transparent")` — inpatient events highlighted.
4. **Detail "Flag" cell (`dFlag`):** if `LabFlag = "OUT"` → Color `#b02a37`, Bold; else Color `#0f5132` (green), Normal.

## Grouping & Sorting
- **Facility Summary tablix (`FacilitySummary`):** row group `grpFacSummary` on `=Fields!FacilityName.Value`, sorted by FacilityName. One summary row per facility; header row repeats on new page (`RepeatOnNewPage=true`, `KeepWithGroup=After`).
- **Clinical Detail tablix (`ClinicalDetail`) — three-level nested row hierarchy:**
  1. `grpFacility` on `=Fields!FacilityName.Value`, sort by FacilityName. Emits a full-width (`ColSpan=9`) facility band row.
  2. `grpPatient` on `=Fields!PatientId.Value`, sort by PatientName. Emits a full-width (`ColSpan=9`) patient banner row (with risk coloring).
  3. `grpDetail` on `=Fields!EventId.Value` AND `=Fields!LabTestName.Value`, sort by DateOfVisit then LabTestName. Emits the 9-column detail row (event columns + lab columns together, at the per-lab grain).
- **Underlying dataset sort:** `ORDER BY f.Name, p.LastName, te.DateOfVisit, lr.TestName`.
- Detail column headers repeat on new page (`RepeatOnNewPage=true`).

## Parameters
| Name | Type | Default | User-facing? | Purpose |
|------|------|---------|--------------|---------|
| FromDate | DateTime | `=CDate("2026-01-01")` | yes (Prompt "Visit date from") | Filter: visit date lower bound (`te.DateOfVisit >= @FromDate`) |
| ToDate | DateTime | `=CDate("2026-12-31")` | yes (Prompt "Visit date to") | Filter: visit date upper bound (`te.DateOfVisit <= @ToDate`) |
| Status | String | `All` | yes (Prompt "Patient status"; valid values All / Active / Inactive) | Filter: patient status; `All` disables the filter |
| rptUser | String | `system` | no (Hidden, nullable, AllowBlank) | Chrome only — printed in footer "Run by:" |

Parameter layout: a 3-column single-row grid (FromDate, ToDate, Status). `rptUser` is hidden.

## Layout
- **Title:** "Patient Clinical Summary Report" (Segoe UI, 18pt bold, `#1f3864`).
- **Filter echo strip:** italic 9pt gray line echoing FromDate/ToDate/Status (see Business Logic).
- **Section 1 — "Facility Summary" heading + `FacilitySummary` table.** Header row background `#1f3864`, white bold text. Columns (in order):
  1. Facility — `=FacilityName`
  2. # Patients — `CountDistinct(PatientId)` (center)
  3. # Events — `CountDistinct(EventId)` (center)
  4. Avg Age — `Round(Avg(Age),0)` (center)
  5. Inpatient Events — `CountDistinct(IIF(IsInpatient,EventId,Nothing))` (center)
  6. Out-of-range Labs — `Sum(IIF(LabFlag="OUT",1,0))` (center, conditional red/bold)
- **Section 2 — "Clinical Detail by Facility, Patient and Transplant Event" heading + `ClinicalDetail` table.** Structure per facility group:
  - Facility band row (full width, background `#dbe5f1`, text `#1f3864` bold).
  - Per patient: banner row (full width; red/green background by risk) showing Patient, MRN, Age, Sex, BMI (category), Risk score, Primary Dx, Active meds.
  - Per event/lab detail rows with header (background `#2e5496`, white bold), columns in order:
    1. Event — `=EventId`
    2. Visit Date — `=Format(DateOfVisit,"MM/dd/yyyy")`
    3. Provider — `=ProviderName & " (" & Specialty & ")"`
    4. Donor — `=DonorType`
    5. Setting — Inpatient/Outpatient (conditional yellow highlight if inpatient)
    6. Test — LabTestName or "-"
    7. Result — `LabValue + " " + LabUnit` or "-"
    8. Reference — `RefLow " - " RefHigh` or "-"
    9. Flag — LabFlag (conditional red-bold "OUT" / green "OK")
- **Per-column formatting:** dates `MM/dd/yyyy`; numeric aggregates rounded; nulls rendered "-"; conditional colors as listed under Conditional Logic.
- **Header/Footer:** No page header. Page footer (prints on all pages): left = "Generated: {ExecutionTime MM/dd/yyyy HH:mm}  |  Run by: {rptUser}"; right = "Page {PageNumber} of {TotalPages}". Page: Letter (8.5in × 11in), 0.5in margins.
- **.NET Razor differences (corroborating render):** `_ClinicalSummary.cshtml` renders the same two sections but nests labs as a separate sub-table under each event (so event metadata shows once per event, not repeated per lab row), and adds a "Days since previous visit" figure and a "No lab results recorded for this event." empty-state — neither appears in the RDL detail cells.

## Open Questions
- **Filtering divergence (important for the migrator):** the RDL SQL filters by `FromDate`/`ToDate`/`Status`, but the corroborating .NET `GetClinicalSummaryAsync()` applies **no** date/status filter and loads all data. The RDL is authoritative here, so the migrated HTML report should implement the three parameters and the WHERE clause (`DateOfVisit BETWEEN`, `Status = All OR match`). Confirm the parameters should be exposed as interactive filters (with the RDL defaults 2026-01-01 → 2026-12-31, Status=All).
- **Detail grain / event-metadata repetition:** in the RDL, `grpDetail` groups by `EventId + LabTestName`, so event columns (Event, Visit, Provider, Donor, Setting) repeat on every lab row of an event. The Razor version instead shows event metadata once and nests labs beneath. Confirm which presentation the migrated report should follow (RDL flat-repeat vs Razor nested).
- **Age formula divergence:** RDL uses `Floor(DateDiff(Day, DOB, Today())/365.25)`; the .NET service uses a calendar-based age. These can differ by ~1 year near birthdays. RDL is authoritative — confirm the day-count/365.25 method should be reproduced.
- **`DaysSincePreviousVisit`, `TransplantDate`, `InfusionDate`, `DischargeDate`, `LabTakenDate`, `TransplantNumber`** are selected/computed in the RDL dataset but **not placed in any RDL cell** (DaysSincePreviousVisit IS shown in the Razor detail line). Confirm whether the HTML migration should surface DaysSincePreviousVisit (per Razor) or omit it (per RDL layout).
- **Custom `<Code>` VB functions (`BmiCategory`, `RiskScore`) and scoped aggregate references (`First(...,"grpPatient")`, `Sum(...,"grpPatient")`, `CountDistinct`)** are SSRS-runtime constructs. A downstream HTML/JS migrator must re-implement them in JS and correctly reproduce the group-scoping (per-patient vs per-facility) — this is the most error-prone part to reproduce faithfully.
- **`CountDistinct(IIF(IsInpatient, EventId, Nothing))`** relies on SSRS ignoring `Nothing` in distinct counts; the JS equivalent must count distinct EventIds only among inpatient rows. Confirm intent (distinct inpatient events, not row count).
