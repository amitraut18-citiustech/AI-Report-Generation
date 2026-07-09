# Report Thought: Patient Demographics Summary

**Report key:** patient_demographics

## Source
- **Type:** SSRS (.rdl)
- **File:** Reports/PatientDemographics.rdl
- **Description:** Summarizes active patient demographics by gender and age group, optionally filtered by facility and date range.

## Database Context
- **Data Source:** HealthcareDB
- **Dataset(s):** PatientDemographicsData
- **Fields:**
  | Field | Type | Meaning |
  |-------|------|---------|
  | Gender | System.String | Patient gender |
  | AgeGroup | System.String | Derived age bucket: Pediatric / Adult / Senior |
  | PatientCount | System.Int32 | Number of active patients in this group |
  | FacilityName | System.String | Facility name (when filtered) |
- **Inferred entities/tables:** Patients (primary), Facilities (joined via FacilityId)
- **Relationships:** Patients.FacilityId → Facilities.Id (many-to-one)

## Queries
- **Main Query:**
  ```sql
  SELECT p.Gender,
    CASE
      WHEN DATEDIFF(YEAR, p.DateOfBirth, GETDATE()) < 18 THEN 'Pediatric'
      WHEN DATEDIFF(YEAR, p.DateOfBirth, GETDATE()) BETWEEN 18 AND 64 THEN 'Adult'
      ELSE 'Senior'
    END AS AgeGroup,
    COUNT(*) AS PatientCount
  FROM Patients p
  LEFT JOIN Facilities f ON p.FacilityId = f.Id
  WHERE p.Status = 'Active'
  GROUP BY p.Gender,
    CASE
      WHEN DATEDIFF(YEAR, p.DateOfBirth, GETDATE()) < 18 THEN 'Pediatric'
      WHEN DATEDIFF(YEAR, p.DateOfBirth, GETDATE()) BETWEEN 18 AND 64 THEN 'Adult'
      ELSE 'Senior'
    END
  ```

## Business Logic
- **Age Grouping Formula:**
  - < 18 years → "Pediatric"
  - 18-64 years → "Adult"
  - 65+ years → "Senior"
- **Filter:** Active patients only (Status = 'Active')
- **Grouping:** By Gender, then by AgeGroup

## Conditional Logic
- If PatientCount = 0 for any group → suppress row
- Header shows total active patient count

## Grouping & Sorting
- **Grouping:** By Gender, then by AgeGroup
- **Sorting:** Gender ASC, then AgeGroup in order: Pediatric, Adult, Senior

## Parameters
| Name | Type | Default | User-facing? | Purpose |
|------|------|---------|--------------|---------|
| FacilityId | Integer | null | yes | Optional: filter by facility |
| StartDate | Date | null | yes | Optional: filter by registration date start |
| EndDate | Date | null | yes | Optional: filter by registration date end |

## Layout
- **Title:** Patient Demographics Summary
- **Summary / cards:** Total active patient count
- **Table columns (in order):** Gender, Age Group, Patient Count
- **Header/Footer:** Generated-on timestamp, executed-by user, filters applied strip

## Open Questions
- _None._
