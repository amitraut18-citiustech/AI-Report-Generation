# Patient Report

## Purpose

A flat listing of all patients with their contact and demographic information, ordered alphabetically by last name. This is a direct migration of the legacy SSRS Patient Report (`PatientReport.rdl`) and its Razor view (`PatientReport.cshtml`).

## Columns

| # | Header Label | Row Key (`camelCase`) | Source Field | Description |
|---|---|---|---|---|
| 1 | First Name | `firstName` | Patients.FirstName | Patient first name |
| 2 | Last Name | `lastName` | Patients.LastName | Patient last name |
| 3 | Gender | `gender` | Patients.Gender | Patient gender |
| 4 | Date of Birth | `dateOfBirth` | Patients.DateOfBirth | Date of birth, formatted as MM/dd/yyyy |
| 5 | Contact Number | `contactNumber` | Patients.ContactNumber | Contact phone number |
| 6 | Email | `email` | Patients.Email | Email address |
| 7 | Phone | `phoneNumber` | Patients.PhoneNumber | Phone number |

## Filters / Parameters

None. This report takes no user-facing filter parameters. All patients are returned by the data service. No filter form is rendered.

## Business Rules Implemented (view-level only)

- **Date formatting:** `dateOfBirth` is formatted as `MM/dd/yyyy` (matching the RDL expression `=Format(Fields!DateOfBirth.Value, "MM/dd/yyyy")`).
- **Alternating row striping:** Odd rows (1-based) get background `#F2F2F2`, even rows get white, matching the original RDL `IIF(RowNumber(Nothing) Mod 2 = 1, ...)` expression.
- **Ordering:** Rows arrive pre-sorted by `lastName` ascending from the host. The JS preserves incoming order.
- **No aggregations or summaries** are displayed (consistent with the original report).

## Data Contract

Rows arrive **pre-filtered** (in this case, all patients with no filter applied). The JS renders `rows` as given and never re-queries or filters.

```js
window.REPORT_DATA = {
  parameters: {},           // no parameters for this report
  rows: [
    {
      "firstName": "string",
      "lastName": "string",
      "gender": "string",
      "dateOfBirth": "ISO-8601 date string",
      "contactNumber": "string",
      "email": "string",
      "phoneNumber": "string"
    }
    // ... one object per patient
  ],
  narrative: "",            // LLM-generated summary; may be empty (see Narrative Rendering below)
  meta: {
    generatedAt: "ISO-8601",
    executedBy: "string",
    rowCount: 0
  }
};
```

### Property name mapping (PascalCase DTO to camelCase row key)

| ViewModel Property | Row Key |
|---|---|
| FirstName | firstName |
| LastName | lastName |
| Gender | gender |
| DateOfBirth | dateOfBirth |
| ContactNumber | contactNumber |
| Email | email |
| PhoneNumber | phoneNumber |

## Narrative Rendering

When `narrative` is non-empty, `renderNarrative()` builds a styled card:

- **Header:** Dark navy bar with an SVG info icon and the label "AI Summary" (`.report__narrative-header`)
- **Body:** The narrative text is split into paragraphs (every two sentences grouped) and rendered as `<p>` elements (`.report__narrative-body`)
- **Chart:** If `window.REPORT_DATA.chart` is present (type, title, labels, values), a Chart.js canvas is inserted after the narrative section

The narrative section is hidden when `narrative` is empty.

## Deviations from Source

- **Date format nuance:** The Razor view used `ToShortDateString()` (locale-dependent, typically `M/d/yyyy` on US systems without zero-padding), while the RDL used `MM/dd/yyyy` (zero-padded). This migration uses `MM/dd/yyyy` (zero-padded), matching the RDL.
- **No page header/footer bands:** The original RDL defined an empty 0.5in page header band with no content. This is omitted since it had no visible elements.
