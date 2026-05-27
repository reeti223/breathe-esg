# Tradeoffs — Breathe ESG Ingestion Platform

## Three things deliberately not built

### 1. PDF parsing for utility bills
**What it is:** Automatically extracting meter readings and
consumption data from scanned or digital PDF utility bills.

**Why I didn't build it:** PDF parsing is a significant
engineering problem. Utility bills have no standard format —
every supplier lays out data differently. A robust solution
requires OCR, layout detection, and supplier-specific templates.
This would have taken 2-3 days alone and would be brittle in
production. The CSV portal export achieves the same result
with far less complexity and is what most facilities teams
already do manually.

**What it would take in production:** A dedicated PDF extraction
service using something like AWS Textract or a trained document
model, with human-in-the-loop review for low-confidence
extractions.

---

### 2. Automated scheduled data pulls
**What it is:** A background job that automatically pulls data
from SAP, utility portals, and travel platforms on a schedule
without human intervention.

**Why I didn't build it:** Scheduled pulls require standing
integrations with client systems — OAuth tokens, API keys,
firewall rules, and IT agreements. These are procurement and
security conversations that take weeks, not hours. For a
prototype demonstrating the ingestion and review workflow,
file upload achieves the same result and is actually how most
clients will start anyway.

**What it would take in production:** Celery + Redis for task
scheduling, per-tenant credential storage with encryption,
webhook handlers for platforms that push rather than pull,
and retry logic with alerting for failed pulls.

---

### 3. Role-based access control (RBAC)
**What it is:** Different permission levels for different users
— data uploaders, analysts who review, managers who approve,
auditors who have read-only access.

**Why I didn't build it:** The assignment specifies analysts
reviewing and approving data. Implementing full RBAC adds
significant complexity to both the backend (permission checks
on every view) and the frontend (conditional UI based on role).
For a prototype with one analyst persona, a single
authenticated user with full access demonstrates the workflow
clearly without the overhead.

**What it would take in production:** Django's built-in groups
and permissions system extended with custom roles, row-level
permissions for tenant isolation, and an admin interface for
managing user roles per tenant.