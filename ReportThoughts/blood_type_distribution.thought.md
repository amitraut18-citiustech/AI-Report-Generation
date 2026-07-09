# Report Thought: Blood Type Distribution

**Report key:** blood_type_distribution

## Source
- **Type:** SSRS (.rdl)
- **File:** Reports/BloodTypeDistribution.rdl
- **Description:** Shows the distribution of blood types across active patients, optionally filtered by facility.

## Database Context
- **Data Source:** HealthcareDB
- **Dataset(s):** BloodTypeData
- **Fields:**
  | Field | Type | Meaning |
  |-------|------|---------|
  | BloodType | System.String | ABO/Rh blood type (e.g., O+, A-, AB+) |
  | PatientCount | System.Int32 | Number of active patients with this blood type |
  | Percentage | System.Decimal | Percentage of total active patients |
  | FacilityName | System.String | Facility name (when filtered) |
- **Inferred entities/tables:** Patients (primary), Facilities (joined via FacilityId)
- **Relationships:** Patients.FacilityId → Facilities.Id (many-to-one)

## Queries
- **Main Query:**
  ```sql
  SELECT p.BloodType,
         COUNT(*) AS PatientCount,
         CAST(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () AS DECIMAL(5,2)) AS Percentage
  FROM Patients p
  LEFT JOIN Facilities f ON p.FacilityId = f.Id
  WHERE p.Status = 'Active'
  GROUP BY p.BloodType
  ORDER BY PatientCount DESC
  ```

## Business Logic
- **Filter:** Active patients only (Status = 'Active')
- **Grouping:** By BloodType
- **Aggregation:** COUNT(*) per blood type, percentage of total
- **Sorting:** Descending by PatientCount (most common first)

## Conditional Logic
- If PatientCount = 0 for any blood type → suppress row
- If no data at all → show "No active patients found" message

## Grouping & Sorting
- **Grouping:** By BloodType
- **Sorting:** PatientCount DESC (most common blood type first)

## Parameters
| Name | Type | Default | User-facing? | Purpose |
|------|------|---------|--------------|---------|
| FacilityId | Integer | null | yes | Optional: filter by facility |

## Layout
- **Title:** Blood Type Distribution
- **Summary / cards:** Total active patient count
- **Table columns (in order):** Blood Type, Patient Count, Percentage
- **Header/Footer:** Generated-on timestamp, executed-by user, facility filter if applied

## Open Questions
- _None._
