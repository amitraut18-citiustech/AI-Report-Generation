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

Business-aware map used to decode NL prompts into report keys + parameters.

```json
{
  "database": "HealthcareDB",
  "generated": "<fill-at-generation>",
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
        { "name": "BloodType",   "type": "NVARCHAR(10)",   "description": "ABO/Rh blood type",      "phi": false },
        { "name": "Gender",      "type": "NVARCHAR(20)",   "description": "Patient gender",         "phi": false },
        { "name": "Status",      "type": "NVARCHAR(20)",   "description": "Active or Inactive",     "phi": false },
        { "name": "FacilityId",  "type": "INT",            "description": "FK to Facilities",       "phi": false }
      ],
      "relationships": [
        { "column": "FacilityId", "references": "Facilities.Id", "type": "many-to-one" }
      ]
    }
  ],
  "_notes": "Optional: list inferences, partial-schema gaps, or tables excluded as non-reportable."
}
```

Field rules:
- `reportable` — `true` for business entities a user would query; `false` for
  system/audit/junction tables.
- `phi` — per-column PHI flag; must agree with `phi-markers.json`.
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
    { "table": "Patients", "column": "SSN",         "strategy": "redact" }
  ]
}
```

`strategy` values:
| strategy | Meaning | Example |
|---|---|---|
| `pseudonymize` | Replace with a stable pseudonym | `John Smith` → `Patient_001` |
| `age_range` | Generalize a date/age to a band | `1985-03-15` → `30-39` |
| `sequential_id` | Replace an identifier with a sequence | `MRN-84729` → `P_001` |
| `redact` | Never transmit; always mask | `SSN` → `[REDACTED]` |
| `region_only` | Coarsen a location | `123 Main St, Austin TX` → `TX` |

Consistency requirement: every column with `phi: true` in `schema-mapping.json` must have
a matching entry here with a strategy.
