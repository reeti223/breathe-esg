# Sources — Breathe ESG Ingestion Platform

## SAP — Fuel & Procurement Data

### What I researched
SAP's MM (Materials Management) and FI (Finance) modules are
the two most common sources of fuel and procurement data in
enterprise clients. The most practical export mechanism for
a new client onboarding is a flat file dump via SAP transaction
MB51 (material document list) or ME2M (purchase orders by
material). These exports are pipe-delimited or tab-delimited
by default, with column headers that vary by SAP configuration
— German headers (BUDAT, MENGE, MEINS, MATNR, WERKS) are common
in older configurations, English headers in newer ones.

### What I learned
- SAP dates come in DD.MM.YYYY format by default (German locale)
  but can be configured to YYYY-MM-DD
- Quantities use comma as decimal separator in German locale
  (e.g. 1.234,56 means 1234.56)
- Plant codes (WERKS) are internal identifiers that mean nothing
  without a lookup table from the client's IT team
- Material numbers (MATNR) are also internal — mapping them to
  fuel types requires a material master lookup
- Units (MEINS) use SAP internal codes: L for litres, KG for
  kilograms, M3 for cubic metres

### What my sample data looks like and why
My sample uses pipe-delimited format with German column headers
(BUDAT, MENGE, MEINS, MATNR, WERKS, LIFNR, SGTXT) because this
is the most common format seen in MM exports from mid-size
manufacturing clients. Material names include recognizable fuel
keywords (DIESEL-B7, PETROL-95, LPG-MIX) — in reality these
would be opaque codes like 100000234 requiring a master data
lookup. I included one row with a zero quantity and one with an
unrealistically large quantity to demonstrate the auto-flagging
logic.

### What would break in real deployment
- Material numbers would be opaque SAP codes, not human-readable
  fuel names — we would need a material master extract from the
  client
- German decimal format (1.234,56) would break our parser
- Multiple company codes and controlling areas would need to be
  handled
- Some clients export via IDOC XML instead of flat file —
  our parser does not handle XML
- Character encoding issues are common (SAP often exports in
  ISO-8859-1, not UTF-8)

---

## Utility Data — Electricity

### What I researched
Indian utility providers (Adani Electricity, BSES Rajdhani,
BESCOM, MSEDCL) all offer online portal access where facilities
managers can download consumption history as CSV. The typical
export includes meter ID, billing period start and end dates,
consumption in kWh, tariff code, and supplier name. Billing
periods do not align with calendar months — a billing cycle
might run from the 15th to the 14th of the following month.
Some large industrial consumers have interval meter data
(15-minute readings) rather than monthly billing data.

### What I learned
- Meter readings are in kWh for most commercial/industrial
  consumers but some older meters report in units (1 unit = 1 kWh)
- Tariff codes (LT-Commercial, C2-Industrial, HT-1) determine
  the rate structure but not the consumption calculation
- Billing periods vary by supplier and meter type
- The India grid average emission factor is 0.233 kg CO2e/kWh
  per CEA (Central Electricity Authority) 2023 data
- Some sites have solar generation that offsets grid consumption
  — net metering complicates the calculation

### What my sample data looks like and why
Three meters across three sites (Mumbai HQ, Delhi Office,
Bangalore Office) with three months of data each. Consumption
volumes are realistic for mid-size commercial office spaces
(8,000-50,000 kWh/month). Suppliers are real Indian utilities.
Tariff codes reflect real tariff categories used by these
utilities.

### What would break in real deployment
- Billing periods that don't align with calendar months would
  cause double-counting if we aggregate by month naively
- Net metering (solar offset) is not handled
- Some utilities export in MWh not kWh — our parser handles
  this but it needs testing
- Multi-currency billing (some utilities bill in local currency
  with taxes) is not handled
- Interval meter data (15-minute readings) would require
  aggregation before ingestion

---

## Corporate Travel — Flights, Hotels, Ground Transport

### What I researched
Concur (SAP Concur) is the dominant corporate travel and expense
platform in enterprise clients. Its API returns JSON with a
consistent structure. Navan (formerly TripActions) is the
main competitor and also exports JSON. Key fields in a Concur
export include ExpenseTypeCode (AIR, HOTEL, CAR), 
TransactionDate, VendorName, DepartureAirportCode,
ArrivalAirportCode, and Amount. Distances are rarely included
directly — they must be calculated from airport codes.

### What I learned
- Concur uses IATA airport codes (DEL, BOM, LHR) not city names
- Distance is almost never in the export — great-circle distance
  must be calculated from origin/destination codes
- Hotel stays record check-in date and number of nights
- Ground transport (taxi, car rental) sometimes has distance,
  sometimes only cost
- The GHG Protocol Scope 3 standard requires radiative forcing
  factor for flights (typically 2x the CO2 alone) — we use
  DEFRA's combined factor of 0.255 kg CO2e/km which includes
  this
- Rail travel has significantly lower emissions than flights
  (0.041 kg CO2e/km vs 0.255 for flights)

### What my sample data looks like and why
A mix of domestic Indian routes (DEL-BOM, DEL-BLR), 
international routes (BOM-LHR, BOM-DXB, DEL-JFK), hotel stays,
car trips, and one rail journey. Vendors are real airlines and
hotel chains operating in India. One car trip has zero distance
to demonstrate flagging. The JSON structure mirrors Concur's
actual API response shape with simplified field names.

### What would break in real deployment
- Airport codes not in our lookup table default to 1500km —
  this is a rough estimate and could be significantly wrong
- Concur's actual API requires OAuth 2.0 authentication and
  pagination for large datasets
- Expense reports sometimes have multiple legs in one record
  (connecting flights) — our parser treats each record as
  one leg
- Personal car mileage claims use a different emission factor
  than car rentals
- Some clients have a travel policy that distinguishes economy
  vs business class — emission factors differ significantly
  (business class uses more space per passenger)