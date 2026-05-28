# Architectural Decisions — Breathe ESG Ingestion Platform

## SAP Data Format
**Decision:** Pipe-delimited flat file export

**Rationale:** SAP's most practical bulk export for MM/FI modules is a flat file via
transactions MB51 (material movements) or SE16 (table browser). IDocs are designed
for real-time system-to-system integration, not one-time data handoffs. OData requires
a formal API connection to the client's SAP landscape — a procurement and security
process that takes weeks. A flat file is what a sustainability lead can actually
obtain from their IT team within a day, making it the correct choice for a
time-sensitive ESG audit cycle.

**Alternatives rejected:** IDoc XML (requires EDI infrastructure), BAPI calls
(needs ABAP access), SAP BW extracts (requires BW licensing and separate project).

**Open question for PM:** Does the client have an IT contact who can schedule
automated MB51 exports, or will the sustainability lead do manual exports each period?
If the latter, we need to design the upload UX for non-technical users.

---

## Utility Data Format
**Decision:** Portal CSV export

**Rationale:** Major Indian utilities — Adani Electricity, BSES, BESCOM, MSEDCL —
all offer CSV downloads from their customer portals. PDF bill parsing is the
alternative, but it introduces OCR complexity, supplier-specific layout handling,
and significant failure rates on scanned documents. API access (e.g., Urjanet
aggregator) exists but requires formal data-sharing agreements. The CSV portal
export is what a facilities manager can produce tomorrow morning with zero
IT involvement.

**Alternatives rejected:** PDF parsing (brittle, requires OCR pipeline),
utility APIs (requires formal agreements and onboarding), AMR/AMI direct feeds
(only available for large industrial accounts).

**Open question for PM:** How many meters does this client have across sites?
Manual CSV downloads don't scale past ~20 meters per period. If the client
has 100+ meters, we need to discuss a data aggregator or automated portal scraping.

---

## Corporate Travel Format
**Decision:** JSON export matching Concur/Navan schema

**Rationale:** Unlike SAP, corporate travel platforms are built for integration.
Concur's Expense API returns JSON. Navan's export is JSON. The format is
consistent, machine-readable, and requires no OCR or parsing heuristics.
The ingestion pipeline maps known fields (origin, destination, travel_type,
amount) to EmissionRecord fields with deterministic logic.

**Alternatives rejected:** Concur SOAP API (legacy, deprecated for new
integrations), expense report PDFs (requires document parsing), manual
spreadsheet entry (no audit trail, high error rate).

**Open question for PM:** Which platform does the client use — Concur, Navan,
TravelPerk, or an in-house tool? The JSON field names differ slightly.
Concur uses `ExpenseTypeCode`; Navan uses `category`. This affects the
field mapping in the ingestor.

---

## Flight Distance Calculation
**Decision:** Lookup table for top routes, 1,500 km default for unknowns

**Rationale:** Travel exports provide airport codes (IATA), not distances.
Great-circle distance calculation requires either a geocoding API call per
record or a local airport coordinate database. For a prototype, a lookup
table covering the 50 most common Indian domestic and international routes
handles the majority of records. Unknown routes are flagged as PENDING
with a default of 1,500 km (median short-haul distance) for analyst review.
This avoids API dependency while preserving correctness for common cases.

**What production needs:** Integration with a flight distance API or
the OpenFlights dataset for full IATA coverage, removing the default fallback.

---

## Authentication
**Decision:** Django REST Framework Token Authentication

**Rationale:** Token auth is stateless, works cleanly with a React SPA, and
requires no cookie/session management. Each request carries the token in the
Authorization header, which is simple to implement and debug. For a 4-day
prototype, this is the correct level of complexity.

**What production needs:** JWT with short-lived access tokens and refresh
tokens (using SimpleJWT), token revocation on logout, and rate limiting
on the auth endpoint.

---

## Database
**Decision:** SQLite in development, PostgreSQL-ready in production

**Rationale:** SQLite requires zero infrastructure, runs identically to
PostgreSQL for our query patterns (no full-text search, no JSON operators
that diverge between engines), and makes local development and CI trivially
simple. The settings module reads DATABASE_URL from the environment, so
switching to a managed PostgreSQL instance on Render requires changing one
environment variable and nothing else in the codebase.

---

## Emission Factors
**Decision:** Hardcoded published factors from DEFRA 2023 and CEA India 2023

**Rationale:** Using published, versioned factors from a named authority
(DEFRA, CEA) means every CO2e calculation is auditable and reproducible.
Hardcoding them in a constants file makes the source explicit. The alternative
— a database-driven factor table — is the right production design but adds
schema complexity and a factor management UI that isn't justified for a prototype.

**What production needs:** A FactorSet model with source, version, and
effective_date fields, so factors can be updated without code changes
and historical records retain the factor that was current at ingest time.

---

## Questions for PM / Client Discovery
1. How many SAP plants / utility meters / employees does this client have?
   (Determines whether manual upload or automated pulls are needed)
2. Concur or Navan for travel? (Affects field mapping in the JSON ingestor)
3. Do they have a data engineer, or is this all done by the sustainability lead?
4. What is the audit lock date? (Determines the analyst review window)
5. Are emission factors client-specific or do we use standard published factors?
   Some clients have negotiated green tariffs that change their Scope 2 factor.
