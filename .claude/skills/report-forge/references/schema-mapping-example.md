# Schema Mapping & PHI Marker Artifacts

Two files in `DataSchemaMapping/`, consumed by the Phase 2 Python brain.

> **Source & types.** When the schema comes from EF Core, derive tables from `DbSet<>`s,
> columns/types from entity properties + `OnModelCreating`, and relationships from
> `HasOne/WithMany/HasForeignKey`. Use `type` values that reflect the **actual provider**
> (SQL Server: `NVARCHAR(100)`, `INT`, `DATETIME`, `BIT`; SQLite: `TEXT`, `INTEGER`,
> `TEXT`, `INTEGER`). Set `database` to the real database/provider (e.g.
> `"PatientDB (EF Core + SQLite)"`). The example below uses SQL Server types for
> illustration — substitute the provider's types.

## `schema-mapping.json`

Business-aware map used by the Phase 2 brain to decode NL prompts into structured query
specs with table-qualified filters and joins.

```json
{
  "database": "HealthcareDB",
  "generated": "<fill-at-generation>",
  "allowedOperators": ["equals", "notEquals", "contains", "greaterThan", "greaterThanOrEqual", "lessThan", "lessThanOrEqual"],
  "tables": [
    {
      "name": "Patients",
      "description": "Active and inactive recipients of care",
      "reportable": true,
      "columns": [
        { "name": "Id",          "type": "INT",            "description": "Primary key",            "phi": false },
        { "name": "FirstName",   "type": "NVARCHAR(100)",  "description": "Patient first name",     "phi": true  },
        { "name": "LastName",    "type": "NVARCHAR(100)",  "description": "Patient last name",      "phi": true  },
        { "name": "DateOfBirth", "type": "DATE",           "description": "Patient date of birth",  "phi": true  },
        { "name": "MRN",         "type": "NVARCHAR(20)",   "description": "Medical Record Number",  "phi": true  },
        { "name": "Gender",      "type": "NVARCHAR(20)",   "description": "Patient gender",         "phi": false },
        { "name": "Status",      "type": "NVARCHAR(20)",   "description": "Active or Inactive",     "phi": false },
        {
          "name": "FacilityId",  "type": "INT",            "description": "FK to Facilities",       "phi": false,
          "navigation": {
            "table": "Facilities",
            "foreignKey": "Id",
            "navProperty": "Facility",
            "displayFields": ["Name", "City", "State"]
          }
        }
      ],
      "relationships": [
        { "column": "FacilityId", "references": "Facilities.Id", "type": "many-to-one" }
      ]
    },
    {
      "name": "Facilities",
      "description": "Healthcare facilities / care sites",
      "reportable": true,
      "columns": [
        { "name": "Id",           "type": "INT",            "description": "Primary key",           "phi": false },
        { "name": "Name",         "type": "NVARCHAR(200)",  "description": "Facility display name", "phi": false },
        { "name": "City",         "type": "NVARCHAR(100)",  "description": "Facility city",         "phi": false },
        { "name": "State",        "type": "NVARCHAR(2)",    "description": "State code",            "phi": false }
      ],
      "relationships": []
    }
  ],
  "_notes": "Optional: list inferences, partial-schema gaps, or tables excluded as non-reportable."
}
```

### Key fields

- `allowedOperators` — the fixed set of filter operators the brain may use. Always include
  all seven.
- `reportable` — `true` for business entities a user would query; `false` for
  system/audit/junction tables.
- `phi` — per-column PHI flag; must agree with `phi-markers.json`.
- `navigation` — **required on every FK column**. Tells the brain how to resolve
  cross-table filters. See the `FacilityId` example above.
  - `table` — the related table name (must match a table in this schema)
  - `foreignKey` — the PK column on the related table (usually `"Id"`)
  - `navProperty` — the EF Core navigation property name (e.g. `"Facility"`)
  - `displayFields` — human-readable columns a user would filter on (not the int FK)
- `generated` — ISO-8601 string. Use `"<fill-at-generation>"` if no clock value is
  supplied (agents cannot read the wall clock).

## `phi-markers.json`

Drives the anonymizer that strips PHI before any cloud (Claude) call.

```json
{
  "database": "HealthcareDB",
  "phiColumns": [
    { "table": "Patients", "column": "FirstName",   "strategy": "pseudonymize" },
    { "table": "Patients", "column": "LastName",    "strategy": "pseudonymize" },
    { "table": "Patients", "column": "DateOfBirth", "strategy": "age_range" },
    { "table": "Patients", "column": "MRN",         "strategy": "sequential_id" },
    { "table": "_viewmodel", "column": "PatientName",  "strategy": "pseudonymize" },
    { "table": "_viewmodel", "column": "ProviderName", "strategy": "pseudonymize" },
    { "table": "_viewmodel", "column": "Mrn",          "strategy": "sequential_id" }
  ]
}
```

### `_viewmodel` entries

Report data is often projected into DTOs that concatenate or rename fields (e.g.
`PatientName = FirstName + " " + LastName`, `Mrn` instead of `MRN`). These projected
names won't match the raw table entries. Add `_viewmodel` entries so the anonymizer
catches them regardless of the data shape passing through the Claude fallback path.

### `strategy` values

| strategy | Meaning | Example |
|---|---|---|
| `pseudonymize` | Replace with a stable pseudonym | `John Smith` → `Patient_001` |
| `age_range` | Generalize a date/age to a band | `1985-03-15` → `30-39` |
| `sequential_id` | Replace an identifier with a sequence | `MRN-84729` → `P_001` |
| `redact` | Never transmit; always mask | `SSN` → `[REDACTED]` |
| `region_only` | Coarsen a location | `123 Main St, Austin TX` → `TX` |

Consistency requirement: every column with `phi: true` in `schema-mapping.json` must have
a matching entry here with a strategy. `_viewmodel` entries are additional — they don't
need a corresponding `phi: true` column in the schema (they derive from columns that
already have one).
