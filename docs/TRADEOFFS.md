# Tradeoffs — Breathe ESG Ingestion Platform

## Three Things Deliberately Not Built

---

### 1. PDF Parsing for Utility Bills

**What it is:** Automatically extracting meter readings and consumption figures
from scanned or digital PDF utility bills without human intervention.

**Why it was excluded:** PDF parsing is an engineering problem in its own right.
Indian utility bills have no standard layout — Adani Electricity, BSES, and BESCOM
all format their bills differently, and scanned bills introduce OCR noise on top
of that. A reliable PDF extraction pipeline requires a document intelligence service
(AWS Textract, Azure Form Recognizer), supplier-specific field templates, confidence
scoring, and a human-in-the-loop review queue for low-confidence extractions.
Building this correctly would consume 2–3 days and would still be brittle in
production when a supplier updates their bill layout.

The CSV portal export achieves the same data acquisition with far less complexity,
and it is what most facilities teams already do for their own record-keeping.

**What production implementation requires:** A dedicated extraction service,
trained per-supplier document models, confidence thresholds with fallback to
manual entry, and audit logging of every OCR correction.

---

### 2. Scheduled Automated Data Pulls

**What it is:** Background jobs that automatically pull data from SAP,
utility portals, and travel platforms on a recurring schedule without
requiring a human to upload a file each period.

**Why it was excluded:** Automated pulls require standing integrations —
OAuth tokens stored per tenant, API keys managed with rotation, firewall
allowlisting on the client's SAP system, and formal data-sharing agreements
with utility providers. These are procurement and security conversations
that take weeks, not hours. For a prototype whose purpose is demonstrating
the ingestion, normalization, and review workflow, file upload is the correct
abstraction. It is also how every real client will start: the first 2–3 periods
are always manual while IT agreements are processed.

**What production implementation requires:** Celery with Redis as the broker
for task scheduling; per-tenant encrypted credential storage using a secrets
manager (AWS Secrets Manager or HashiCorp Vault); webhook receivers for
platforms that push rather than expose a pull API; exponential backoff and
dead-letter queues for failed pulls; and alerting when a scheduled pull
misses its window (which would create a gap in the audit trail).

---

### 3. Role-Based Access Control (RBAC)

**What it is:** Distinct permission levels for different user types —
data uploaders who can only submit files, analysts who review and flag records,
managers who approve or reject, and auditors who have read-only access to
approved records and audit logs.

**Why it was excluded:** The assignment specifies a single analyst persona
reviewing and approving ingested data. Implementing full RBAC adds permission
checks to every API view, row-level filtering by role, conditional UI rendering
in the frontend, and an admin interface for assigning roles per tenant.
For a prototype demonstrating the core workflow, a single authenticated user
with full permissions makes the workflow clear without the overhead.

**What production implementation requires:** Django's groups and permissions
system extended with custom roles (UPLOADER, ANALYST, MANAGER, AUDITOR);
row-level permissions enforced at the queryset level so an AUDITOR cannot
modify records they can read; a tenant admin interface for role assignment;
and API endpoint documentation that maps each endpoint to its minimum required role.

---

## One Deliberate Simplification Worth Noting

### Emission Factor Versioning

The current model stores CO2e as a calculated field at ingest time using
hardcoded factors. This means if DEFRA updates its factors next year,
historical records cannot be recalculated without a data migration.

In production, the correct design is a `FactorSet` model with `source`,
`version`, and `effective_date` fields, with `EmissionRecord` holding a
foreign key to the factor used at ingest time. This preserves reproducibility
(auditors can see exactly which factor was applied) and enables retroactive
recalculation when factors are revised — both of which are requirements for
a GHG Protocol-compliant audit.

This was simplified for the prototype to keep the schema and ingest pipeline
focused on the core workflow rather than factor management infrastructure.
