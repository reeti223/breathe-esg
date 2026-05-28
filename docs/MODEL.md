# Data Model — Breathe ESG Ingestion Platform

## Design Philosophy

The model is built around one question auditors always ask: *"Where did this number come from, and did anyone touch it?"* Every design decision traces back to answering that question completely.

Four principles drove the schema:
1. **Multi-tenancy** — client data must never leak between tenants, at the query level, not just the application level
2. **Source-of-truth tracking** — every EmissionRecord must know exactly which file, upload job, and row it came from
3. **Unit normalization** — raw values are preserved, normalized values are calculated; analysts can always verify the math
4. **Immutable audit trail** — every status change is logged with before/after state so auditors can reconstruct the full history

---

## Entities

### Tenant
One row per client company. All data-bearing tables foreign-key to Tenant. API views filter by `request.user.tenant` at query time — no view ever returns cross-tenant rows.

```
Tenant
  id          UUID PK
  name        CharField
  slug        SlugField (unique, used in URLs)
  created_at  DateTimeField
```

Why UUID not integer? Tenant IDs appear in URLs and API responses. Sequential integers let clients enumerate other tenants. UUIDs don't.

---

### DataSource
Tracks every ingest job. If an analyst asks "where did row 47 come from", DataSource has the answer: which file, which format, who uploaded it, when, how many rows came out.

```
DataSource
  id           UUID PK
  tenant       FK → Tenant
  source_type  CharField  [SAP | UTILITY | TRAVEL]
  filename     CharField
  uploaded_by  FK → User
  uploaded_at  DateTimeField
  status       CharField  [PENDING | PROCESSED | FAILED]
  row_count    IntegerField (nullable — null until processing completes)
  error_log    TextField (nullable — populated on failure)
```

`status` on DataSource is about the ingest job itself. `status` on EmissionRecord is about analyst review. These are different things and should not be conflated.

---

### EmissionRecord
The core normalized record. One row = one activity event. A fuel purchase. A meter reading period. A flight segment. A hotel night.

```
EmissionRecord
  id                  UUID PK
  tenant              FK → Tenant
  source              FK → DataSource
  source_type         CharField  [SAP | UTILITY | TRAVEL]
  category            CharField  (e.g. "Diesel", "Electricity", "Flight - Economy")
  scope               IntegerField  [1 | 2 | 3]
  activity_date       DateField
  quantity            DecimalField  (original as-ingested value)
  unit                CharField     (original as-ingested unit)
  quantity_normalized DecimalField  (converted to base unit)
  unit_normalized     CharField     [kWh | L | kg | km | nights]
  co2e_kg             DecimalField  (calculated at ingest, never recalculated after)
  emission_factor     DecimalField  (the factor used — stored so future factor changes don't alter historical records)
  emission_factor_src CharField     (e.g. "DEFRA 2023", "CEA India Grid 2023")
  location            CharField (nullable)
  vendor              CharField (nullable)
  description         TextField (nullable)
  raw_data            JSONField     (verbatim original row, never modified)
  status              CharField  [PENDING | APPROVED | FLAGGED | REJECTED]
  flag_reason         CharField (nullable — populated by auto-flag logic or analyst)
  is_edited           BooleanField  default False
  edit_note           TextField (nullable)
  reviewed_by         FK → User (nullable)
  reviewed_at         DateTimeField (nullable)
  created_at          DateTimeField
```

**Key design decisions:**

`quantity` vs `quantity_normalized` — raw values are preserved exactly as ingested. Normalization is a separate calculated field. If our normalization logic has a bug, we can recalculate from `quantity` without re-ingesting the file.

`raw_data` JSONField — stores the original row verbatim before any transformation. This is the ground truth. If an analyst disputes a value, we can show them exactly what came out of the source system.

`co2e_kg` is calculated once at ingest and frozen. `emission_factor` and `emission_factor_src` are stored alongside it. If DEFRA updates their factors next year, historical records don't change — which is correct behaviour for an audit trail. Auditors want to know what factor was used at the time, not what the current factor is.

`status` drives the review workflow:
```
PENDING → APPROVED   (analyst signs off)
PENDING → FLAGGED    (analyst or auto-flag marks for investigation)
PENDING → REJECTED   (analyst rejects the row)
FLAGGED → APPROVED   (flagged issue resolved)
FLAGGED → REJECTED   (flagged issue unresolvable)
```

---

### AuditLog
Every status change on an EmissionRecord creates an AuditLog row. This is append-only. No AuditLog row is ever deleted or updated.

```
AuditLog
  id           UUID PK
  record       FK → EmissionRecord
  action       CharField  (e.g. "STATUS_CHANGE", "EDIT", "FLAG")
  changed_by   FK → User
  changed_at   DateTimeField
  before_state JSONField  (snapshot of record fields before change)
  after_state  JSONField  (snapshot of record fields after change)
  note         TextField (nullable — analyst's comment)
```

Storing full before/after snapshots (not just diffs) makes audit queries simple: "show me what this record looked like at time T" is a single read, not a reconstruction.

---

## Scope Classification

| Source | Scope | GHG Protocol Category |
|--------|-------|----------------------|
| SAP (fuel, procurement) | 1 | Direct emissions from owned/controlled sources |
| Utility (electricity) | 2 | Indirect emissions from purchased energy |
| Travel (flights, hotels, ground) | 3 | Other indirect emissions — business travel |

Scope is assigned at ingest time based on `source_type`. This is a simplification: in reality, some SAP records (e.g. purchased goods) would be Scope 3. The current model handles the three sources in scope for this prototype; expanding to full Scope 3 categories would require a more granular category taxonomy.

---

## Unit Normalization

All quantities are normalized at ingest time to a base unit per category:

| Category | Base Unit | Rationale |
|----------|-----------|-----------|
| Fuel volume | Litres (L) | Emission factors are published per litre |
| Energy | kWh | Standard energy unit; aligns with utility billing |
| Mass | kg | Consistent with CO2e output unit |
| Distance | km | Flight and ground transport emission factors |
| Accommodation | nights | Hotel factors are per room-night |

Conversion logic is in `ingestion/parsers.py`. Original values are never modified — `quantity` and `unit` are write-once at ingest.

---

## Emission Factors

| Category | Factor | Source |
|----------|--------|--------|
| Diesel | 2.68 kg CO2e/L | DEFRA UK GHG Conversion Factors 2023 |
| Petrol | 2.31 kg CO2e/L | DEFRA UK GHG Conversion Factors 2023 |
| Electricity | 0.233 kg CO2e/kWh | CEA India Grid Emission Factor 2023 |
| Short-haul flight | 0.255 kg CO2e/km | DEFRA 2023 (economy class) |
| Long-haul flight | 0.195 kg CO2e/km | DEFRA 2023 (economy class, higher efficiency) |
| Hotel stay | 31.0 kg CO2e/night | GHG Protocol Scope 3 — Category 6 |
| Car (petrol) | 0.171 kg CO2e/km | DEFRA 2023 |

CEA (Central Electricity Authority) India grid factor is used for electricity rather than UK grid because the sample client is India-based. In production, grid factor selection would be driven by the meter's location.

---

## Auto-Flagging Logic

Records are automatically flagged at ingest if:
- `quantity` is zero or negative
- `quantity` exceeds 3 standard deviations from the mean for that source type and category (statistical outlier)
- Required fields are missing (date, quantity, unit)
- Unit string cannot be mapped to a known unit

Auto-flagged records enter the workflow at `FLAGGED` status, not `PENDING`. Analysts must explicitly approve or reject them — they cannot be silently passed through.

---

## Multi-tenancy Implementation

Every API view inherits from a base view that extracts `request.user.tenant` and applies it as a queryset filter before any other filtering. There is no code path that returns un-tenanted data. The Django admin is the only exception and is restricted to staff users.

In the current prototype, tenant is assigned to users at creation time via the User model's related profile. In production, this would be enforced at the database level via row-level security (Postgres RLS) as a second layer of defence.
