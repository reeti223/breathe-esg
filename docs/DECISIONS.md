# Decisions — Breathe ESG Ingestion Platform

## SAP Data Format
**Decision:** Pipe-delimited flat file export (not IDoc, not OData)

**Why:** SAP's most common bulk export for MM/FI modules is a
flat file dump via transaction SE16 or MB51. IDocs are used for
real-time integration between SAP systems — not for one-time
data handoffs to third parties. OData would require standing up
an API connection to the client's SAP system, which is a
procurement and security conversation that takes weeks.
A flat file is what a sustainability lead can actually get from
their IT team in one day.

**What I ignored:** IDoc XML format, BAPI calls, SAP BW exports.
These are valid but require deeper SAP access than a new
onboarding client would grant immediately.

**What I'd ask the PM:** Does the client have an IT contact who
can run MB51 or SE16 exports on a schedule? Or are we relying
on the sustainability lead to do manual exports?

---

## Utility Data Format
**Decision:** Portal CSV export

**Why:** Most Indian utilities (Adani, BSES, BESCOM) offer a
CSV download from their online portal. PDF bills are the other
common format but require OCR which adds significant complexity
and failure modes. API access exists for some utilities but
requires formal agreements. CSV from the portal is what a
facilities manager can actually produce tomorrow morning.

**What I ignored:** PDF parsing, utility API integrations,
automated meter reading systems (AMR/AMI).

**What I'd ask the PM:** How many meters does this client have?
If it's 100+ meters across sites, manual CSV downloads don't
scale and we need to discuss API access or a data aggregator
like Urjanet.

---

## Corporate Travel Format
**Decision:** JSON export (Concur/Navan style)

**Why:** Concur's API returns JSON. Navan's export is JSON.
Most corporate travel platforms offer JSON as their primary
programmatic format. Unlike SAP, travel platforms are designed
to be integrated with — their exports are clean and consistent.

**What I ignored:** Concur's SOAP API (legacy), expense report
PDFs, manual spreadsheet entry.

**What I'd ask the PM:** Which platform does the client use —
Concur, Navan, or something else? Concur has a formal API with
OAuth; Navan has a simpler export. The JSON structure differs
slightly between platforms.

---

## Flight Distance Calculation
**Decision:** Lookup table for common routes, 1500km default

**Why:** Travel exports often give airport codes but not
distances. Great-circle distance calculation requires a
geocoding library. For a prototype, a lookup table of common
Indian and international routes is sufficient. Unknown routes
default to 1500km with a flag for analyst review.

**What I'd ask the PM:** Should we integrate a flight distance
API like the Great Circle Mapper for production?

---

## Authentication
**Decision:** DRF Token Authentication

**Why:** Simple, stateless, works well for a React SPA calling
a REST API. JWT would be better for production (token expiry,
refresh tokens) but adds complexity that isn't justified for
a 4-day prototype.

---

## Database
**Decision:** SQLite for development, designed for PostgreSQL
in production

**Why:** SQLite requires zero setup and works identically to
PostgreSQL for our query patterns. The settings are structured
so switching to PostgreSQL for deployment requires only
changing the DATABASE_URL environment variable.

---

## What I would ask the PM
1. How many meters / SAP plants / employees does this client have?
2. Is the travel data from Concur or Navan specifically?
3. Do they have a data engineer who can run scheduled exports
   or is this all manual?
4. What is the audit deadline — how much time do analysts have
   to review before lock?
5. Are emission factors client-specific or do we use standard
   published factors?