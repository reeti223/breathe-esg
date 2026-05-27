# Data Model — Breathe ESG Ingestion Platform

## Overview
The data model is designed around four core principles:
multi-tenancy, source-of-truth tracking, unit normalization,
and a complete audit trail before data reaches auditors.

## Entities

### Tenant
One row per client company. Every record is scoped to a tenant
so data never leaks between clients. This is the foundation of
multi-tenancy.

### DataSource
Tracks every ingest job — which file was uploaded, by whom,
when, and whether it succeeded or failed. This is the
source-of-truth record: if an analyst asks "where did this
number come from", DataSource has the answer.

### EmissionRecord
The core normalized record. One row = one activity event
(a fuel purchase, a meter reading, a flight).

Key design decisions:
- `quantity` stores the original value as-ingested
- `quantity_normalized` stores the value converted to a base unit
- `unit_normalized` is always one of: kWh, L, kg, km
- `raw_data` (JSONField) stores the original row verbatim
- `scope` is 1, 2, or 3 per GHG Protocol
- `status` drives the review workflow: PENDING → APPROVED or FLAGGED or REJECTED
- `co2e_kg` is calculated at ingest time using published emission factors
- `is_edited` and `edit_note` track any analyst corrections

### AuditLog
Every status change on an EmissionRecord creates an AuditLog row.
Stores before/after state as JSON. This is what auditors read.

## Scope Classification
- Scope 1: SAP fuel records (direct combustion)
- Scope 2: Utility electricity records (purchased energy)
- Scope 3: Corporate travel records (value chain)

## Unit Normalization
All quantities are normalized at ingest time:
- Energy → kWh
- Fuel volume → Litres
- Mass → kg
- Distance → km

Original values are preserved in `quantity` and `unit`.

## Emission Factors
- Diesel: 2.68 kg CO2e/L (DEFRA 2023)
- Petrol: 2.31 kg CO2e/L (DEFRA 2023)
- Electricity: 0.233 kg CO2e/kWh (CEA India Grid 2023)
- Flights: 0.255 kg CO2e/km (DEFRA 2023)
- Hotels: 31.0 kg CO2e/night (GHG Protocol)
- Car travel: 0.171 kg CO2e/km (DEFRA 2023)

## Multi-tenancy
Every table that holds client data has a FK to Tenant.
API views filter by the authenticated user's tenant at query time.
No cross-tenant data is ever returned.