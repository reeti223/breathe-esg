# Sources & Research — Breathe ESG Ingestion Platform

---

## SAP — Fuel & Procurement Data

### What I researched
SAP's MM (Materials Management) and FI (Finance) modules are the primary sources
of fuel and procurement data in enterprise clients. The most practical export
for a new onboarding client is a flat file via transaction **MB51** (material
document list) or **ME2M** (purchase orders by material). These exports are
pipe-delimited or tab-delimited, with column headers that vary by SAP
configuration — German headers (BUDAT, MENGE, MEINS, MATNR, WERKS) are common
in older configurations, English headers in newer ones.

### Key findings
- SAP dates default to **DD.MM.YYYY** (German locale) but can be configured to ISO 8601
- German locale uses comma as decimal separator: `1.234,56` means 1234.56
- Plant codes (WERKS) are internal identifiers requiring a lookup table from the client's IT team
- Material numbers (MATNR) are opaque codes — mapping them to fuel types requires a material master extract
- Unit codes (MEINS): `L` = litres, `KG` = kilograms, `M3` = cubic metres

### Sample data design choices
Pipe-delimited format with German column headers because this matches MM exports
from mid-size manufacturing clients. Material names use recognizable fuel keywords
(DIESEL-B7, PETROL-95) — in production these would be opaque codes like `100000234`.
One row has zero quantity and one has an unrealistically large quantity to demonstrate
auto-flagging logic.

### Known gaps for production
- Material numbers would be opaque SAP codes, not human-readable — a material master
  extract is required at onboarding
- German decimal format (`1.234,56`) would break the current parser without locale handling
- Some clients export via IDoc XML — the current parser handles flat files only
- Character encoding: SAP commonly exports ISO-8859-1, not UTF-8

---

## Utility Data — Electricity

### What I researched
Indian utility providers (Adani Electricity, BSES Rajdhani, BESCOM, MSEDCL) offer
CSV consumption history downloads from their customer portals. A typical export
includes meter ID, billing period dates, consumption in kWh, tariff code, and
supplier name. Billing cycles do not align with calendar months — a cycle might
run from the 15th to the 14th of the following month.

### Key findings
- Most commercial/industrial meters report in kWh; older meters may report in
  "units" (1 unit = 1 kWh)
- Tariff codes (LT-Commercial, C2-Industrial, HT-1) define rate structure but
  not consumption
- **India grid emission factor: 0.233 kg CO2e/kWh** — Central Electricity Authority
  (CEA), *CO2 Baseline Database for the Indian Power Sector*, Version 17, 2023.
  [cea.nic.in](https://cea.nic.in/old/reports/others/thermal/tpece/cdm_co2/user_guide_ver17.pdf)
- Sites with solar generation require net metering treatment — grid consumption
  cannot be taken at face value from the portal export

### Sample data design choices
Three meters across three sites (Mumbai HQ, Delhi Office, Bangalore Office) with
three months of data each. Consumption volumes (8,000–50,000 kWh/month) are
realistic for mid-size commercial offices. Suppliers and tariff codes are real.

### Known gaps for production
- Non-calendar billing periods cause double-counting if naively aggregated by month
- Net metering (solar offset) is not handled in the current model
- Some utilities export in MWh; conversion is implemented but needs edge-case testing
- Interval meter data (15-minute readings) requires aggregation before ingestion

---

## Corporate Travel — Flights, Hotels, Ground Transport

### What I researched
SAP Concur is the dominant corporate travel platform in enterprise clients.
Its API returns JSON with a consistent structure. Navan (formerly TripActions)
is the main competitor and also exports JSON. Key fields include
`ExpenseTypeCode` (AIR, HOTEL, CAR), `TransactionDate`, `VendorName`,
`DepartureAirportCode`, `ArrivalAirportCode`, and `Amount`. Distances are
rarely included and must be derived from airport codes.

### Key findings
- Concur uses IATA airport codes (DEL, BOM, LHR), not city names; distances
  must be calculated from coordinates
- Hotel stays record check-in date and number of nights
- Ground transport sometimes includes distance, sometimes only cost
- Rail travel emission factor: **0.041 kg CO2e/km** vs flights at **0.255 kg CO2e/km**
  — DEFRA 2023 (see below)
- The GHG Protocol Scope 3 standard requires a radiative forcing uplift for
  aviation; DEFRA's 0.255 kg CO2e/km combined factor already incorporates this

### Sample data design choices
Mix of domestic Indian routes (DEL-BOM, DEL-BLR), international routes
(BOM-LHR, BOM-DXB, DEL-JFK), hotel stays, car trips, and one rail journey.
Vendors are real airlines and hotel chains. One car trip has zero distance
to demonstrate FLAGGED status. JSON structure mirrors Concur's API response
shape with simplified field names.

### Known gaps for production
- Airport codes outside the lookup table default to 1,500 km — could be
  significantly wrong for long-haul routes
- Concur's API requires OAuth 2.0 and pagination for datasets > 200 records
- Multi-leg itineraries in a single record are not handled; each record is
  treated as one direct leg
- Business class vs economy class distinction is not implemented; business class
  carries a significantly higher per-passenger emission factor

---

## Emission Factors — Primary Sources

| Activity | Factor | Source |
|---|---|---|
| Diesel combustion | 2.68 kg CO2e/L | DEFRA, *Greenhouse Gas Reporting: Conversion Factors 2023*, Table 1 |
| Petrol combustion | 2.31 kg CO2e/L | DEFRA 2023, Table 1 |
| Grid electricity (India) | 0.233 kg CO2e/kWh | CEA, *CO2 Baseline Database*, Version 17, 2023 |
| Short-haul flights | 0.255 kg CO2e/km | DEFRA 2023, Table 6 (economy, with radiative forcing) |
| Hotel stays | 31.0 kg CO2e/night | GHG Protocol, *Scope 3 Evaluator*, hospitality category |
| Car travel | 0.171 kg CO2e/km | DEFRA 2023, Table 5 (average petrol car) |
| Rail travel | 0.041 kg CO2e/km | DEFRA 2023, Table 6 |

**Full references:**
- DEFRA (2023). *Greenhouse Gas Reporting: Conversion Factors 2023*.
  UK Department for Energy Security and Net Zero.
  https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2023
- CEA (2023). *CO2 Baseline Database for the Indian Power Sector*, Version 17.
  Central Electricity Authority, Ministry of Power, Government of India.
  https://cea.nic.in
- GHG Protocol (2013). *Technical Guidance for Calculating Scope 3 Emissions*.
  World Resources Institute / World Business Council for Sustainable Development.
  https://ghgprotocol.org/scope-3-technical-guidance

---

## Standards & Methodology

- **GHG Protocol Corporate Standard** — defines Scope 1, 2, 3 classification used
  throughout the data model. https://ghgprotocol.org/corporate-standard
- **ISO 14064-1:2018** — organizational-level GHG quantification standard;
  informed the audit trail and record locking design
- **SAP MB51 / ME2M transaction documentation** — SAP Help Portal,
  https://help.sap.com
- **Concur Expense API documentation** — SAP Concur Developer Center,
  https://developer.concur.com/api-reference/expense/expense-report/expense-report-get.html
