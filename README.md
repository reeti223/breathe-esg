# Breathe ESG Ingestion Platform

A Django REST + React full-stack app that ingests emissions data from 
three enterprise source types, normalizes it, and surfaces an analyst 
review dashboard before records are locked for audit.

**Live Demo:** https://breathe-esg-ket4.onrender.com/

## Sources Handled
- SAP flat-file exports (MB51/ME2M format) — fuel & procurement
- Utility CSV/PDF bills — electricity (Scope 2)
- Corporate travel data (Concur format) — flights, hotels, ground

## Stack
Django REST Framework · React · PostgreSQL · Railway

## Docs
- `docs/MODEL.md` — data model & multi-tenancy design
- `docs/DECISIONS.md` — every ambiguity resolved
- `docs/SOURCES.md` — real-world format research
