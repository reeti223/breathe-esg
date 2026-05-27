import csv
import json
import io
from decimal import Decimal
from datetime import datetime


def parse_date(date_str):
    """Try multiple date formats — SAP exports are inconsistent."""
    formats = [
        '%Y-%m-%d', '%d.%m.%Y', '%m/%d/%Y',
        '%d-%m-%Y', '%Y%m%d', '%d/%m/%Y'
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return None


def normalize_unit(quantity, unit):
    """Convert everything to a base unit for comparison."""
    unit = unit.strip().lower()
    quantity = Decimal(str(quantity))

    conversions = {
        'mwh': (quantity * 1000, 'kWh'),
        'gwh': (quantity * 1000000, 'kWh'),
        'kwh': (quantity, 'kWh'),
        'l': (quantity, 'L'),
        'liter': (quantity, 'L'),
        'litre': (quantity, 'L'),
        'liters': (quantity, 'L'),
        'litres': (quantity, 'L'),
        'gal': (quantity * Decimal('3.78541'), 'L'),
        'gallon': (quantity * Decimal('3.78541'), 'L'),
        'gallons': (quantity * Decimal('3.78541'), 'L'),
        'kg': (quantity, 'kg'),
        'kilogram': (quantity, 'kg'),
        'kilograms': (quantity, 'kg'),
        't': (quantity * 1000, 'kg'),
        'tonne': (quantity * 1000, 'kg'),
        'tonnes': (quantity * 1000, 'kg'),
        'ton': (quantity * 1000, 'kg'),
        'km': (quantity, 'km'),
        'mi': (quantity * Decimal('1.60934'), 'km'),
        'mile': (quantity * Decimal('1.60934'), 'km'),
        'miles': (quantity * Decimal('1.60934'), 'km'),
        'm3': (quantity, 'm3'),
    }
    return conversions.get(unit, (quantity, unit))


def flag_suspicious(record):
    """
    Auto-flag records that look wrong.
    Returns a reason string or empty string if clean.
    """
    reasons = []

    if record['quantity'] <= 0:
        reasons.append('Zero or negative quantity')

    if record['quantity'] > 1000000:
        reasons.append('Unusually large quantity — verify before approving')

    if record['activity_date'] is None:
        reasons.append('Could not parse date')

    return '; '.join(reasons)


# ---------------------------------------------------------------------------
# SAP parser
# SAP flat-file export (pipe-delimited, common in MM/FI module exports)
# Headers may be in German in some configs — we handle both
# ---------------------------------------------------------------------------
SAP_COLUMN_MAP = {
    # English → normalized
    'posting_date': 'date', 'budat': 'date',
    'document_date': 'date', 'bldat': 'date',
    'quantity': 'quantity', 'menge': 'quantity',
    'unit': 'unit', 'meins': 'unit',
    'material': 'category', 'matnr': 'category',
    'plant': 'location', 'werks': 'location',
    'vendor': 'vendor', 'lifnr': 'vendor',
    'text': 'description', 'sgtxt': 'description',
    'amount': 'amount',
}

FUEL_KEYWORDS = ['diesel', 'petrol', 'gasoline', 'fuel', 'benzin', 'kraftstoff', 'gas', 'lpg', 'cng']

SAP_EMISSION_FACTORS = {
    'diesel': Decimal('2.68'),    # kg CO2e per litre
    'petrol': Decimal('2.31'),
    'gasoline': Decimal('2.31'),
    'lpg': Decimal('1.51'),
    'cng': Decimal('2.02'),
    'default': Decimal('2.68'),
}


def parse_sap(file_content):
    """Parse SAP pipe-delimited flat file export."""
    records = []
    errors = []

    # Detect delimiter
    sample = file_content[:500]
    delimiter = '|' if '|' in sample else ','

    reader = csv.DictReader(io.StringIO(file_content), delimiter=delimiter)

    for i, row in enumerate(reader):
        try:
            # Normalize column names
            normalized = {}
            for key, value in row.items():
                if key:
                    mapped = SAP_COLUMN_MAP.get(key.strip().lower(), key.strip().lower())
                    normalized[mapped] = value.strip() if value else ''

            raw_quantity = normalized.get('quantity', '0').replace(',', '.')
            raw_unit = normalized.get('unit', 'L')
            raw_date = normalized.get('date', '')
            category = normalized.get('category', 'unknown').lower()

            quantity = Decimal(raw_quantity) if raw_quantity else Decimal('0')
            activity_date = parse_date(raw_date)
            quantity_norm, unit_norm = normalize_unit(quantity, raw_unit)

            # Determine fuel type for emission factor
            fuel_type = 'default'
            for fuel in FUEL_KEYWORDS:
                if fuel in category:
                    fuel_type = fuel
                    break

            ef = SAP_EMISSION_FACTORS.get(fuel_type, SAP_EMISSION_FACTORS['default'])
            co2e = quantity_norm * ef if unit_norm == 'L' else None

            record = {
                'scope': 1,
                'category': category or 'fuel',
                'activity_date': activity_date,
                'quantity': quantity,
                'unit': raw_unit,
                'quantity_normalized': quantity_norm,
                'unit_normalized': unit_norm,
                'emission_factor': ef,
                'emission_factor_source': 'DEFRA 2023',
                'co2e_kg': co2e,
                'location': normalized.get('location', ''),
                'vendor': normalized.get('vendor', ''),
                'description': normalized.get('description', ''),
                'source_row_id': str(i + 1),
                'raw_data': dict(row),
            }

            record['flag_reason'] = flag_suspicious(record)
            records.append(record)

        except Exception as e:
            errors.append(f"Row {i+1}: {str(e)}")

    return records, errors


# ---------------------------------------------------------------------------
# Utility / Electricity parser
# Standard portal CSV export format
# ---------------------------------------------------------------------------
UTILITY_COLUMN_MAP = {
    'meter_id': 'meter_id', 'meter id': 'meter_id',
    'billing_period_start': 'date', 'period_start': 'date', 'start_date': 'date',
    'billing_period_end': 'period_end', 'period_end': 'period_end',
    'consumption_kwh': 'quantity', 'consumption': 'quantity', 'usage_kwh': 'quantity',
    'unit': 'unit',
    'tariff': 'tariff', 'tariff_code': 'tariff',
    'site': 'location', 'site_name': 'location', 'facility': 'location',
    'supplier': 'vendor', 'utility_provider': 'vendor',
}

GRID_EMISSION_FACTOR = Decimal('0.233')  # kg CO2e per kWh — India grid average 2023


def parse_utility(file_content):
    """Parse utility portal CSV export."""
    records = []
    errors = []

    reader = csv.DictReader(io.StringIO(file_content))

    for i, row in enumerate(reader):
        try:
            normalized = {}
            for key, value in row.items():
                if key:
                    mapped = UTILITY_COLUMN_MAP.get(key.strip().lower(), key.strip().lower())
                    normalized[mapped] = value.strip() if value else ''

            raw_quantity = normalized.get('quantity', '0').replace(',', '')
            raw_unit = normalized.get('unit', 'kWh')
            raw_date = normalized.get('date', '')

            quantity = Decimal(raw_quantity) if raw_quantity else Decimal('0')
            activity_date = parse_date(raw_date)
            quantity_norm, unit_norm = normalize_unit(quantity, raw_unit)

            # Convert to kWh for emission calculation
            kwh = quantity_norm if unit_norm == 'kWh' else quantity_norm / 1000
            co2e = kwh * GRID_EMISSION_FACTOR

            record = {
                'scope': 2,
                'category': 'electricity',
                'activity_date': activity_date,
                'quantity': quantity,
                'unit': raw_unit,
                'quantity_normalized': quantity_norm,
                'unit_normalized': unit_norm,
                'emission_factor': GRID_EMISSION_FACTOR,
                'emission_factor_source': 'CEA India Grid 2023',
                'co2e_kg': co2e,
                'location': normalized.get('location', ''),
                'vendor': normalized.get('vendor', ''),
                'description': f"Meter: {normalized.get('meter_id', '')} | Tariff: {normalized.get('tariff', '')}",
                'source_row_id': str(i + 1),
                'raw_data': dict(row),
            }

            record['flag_reason'] = flag_suspicious(record)
            records.append(record)

        except Exception as e:
            errors.append(f"Row {i+1}: {str(e)}")

    return records, errors


# ---------------------------------------------------------------------------
# Corporate travel parser
# Concur / Navan style JSON export
# ---------------------------------------------------------------------------
FLIGHT_EF = Decimal('0.255')       # kg CO2e per km per passenger
HOTEL_EF = Decimal('31.0')         # kg CO2e per night
CAR_EF = Decimal('0.171')          # kg CO2e per km
RAIL_EF = Decimal('0.041')         # kg CO2e per km

AIRPORT_DISTANCES = {
    ('DEL', 'BOM'): 1148, ('BOM', 'DEL'): 1148,
    ('DEL', 'BLR'): 1740, ('BLR', 'DEL'): 1740,
    ('DEL', 'LHR'): 6700, ('LHR', 'DEL'): 6700,
    ('BOM', 'DXB'): 1935, ('DXB', 'BOM'): 1935,
    ('DEL', 'JFK'): 11760, ('JFK', 'DEL'): 11760,
    ('BLR', 'SIN'): 3260, ('SIN', 'BLR'): 3260,
}


def get_flight_distance(origin, destination):
    key = (origin.upper(), destination.upper())
    return AIRPORT_DISTANCES.get(key, 1500)  # default 1500km if unknown


def parse_travel(file_content):
    """Parse Concur/Navan style JSON travel export."""
    records = []
    errors = []

    try:
        data = json.loads(file_content)
        if isinstance(data, dict):
            # Concur wraps in {"Items": [...]}
            trips = data.get('Items', data.get('trips', data.get('records', [data])))
        else:
            trips = data
    except json.JSONDecodeError as e:
        return [], [f"Invalid JSON: {str(e)}"]

    for i, trip in enumerate(trips):
        try:
            trip_type = trip.get('type', trip.get('ExpenseTypeCode', 'FLIGHT')).upper()
            raw_date = trip.get('date', trip.get('TransactionDate', trip.get('start_date', '')))
            activity_date = parse_date(str(raw_date)) if raw_date else None

            if trip_type in ('FLIGHT', 'AIR', 'AIRFARE'):
                origin = trip.get('origin', trip.get('DepartureAirportCode', 'UNK'))
                destination = trip.get('destination', trip.get('ArrivalAirportCode', 'UNK'))
                distance = trip.get('distance_km') or get_flight_distance(origin, destination)
                quantity = Decimal(str(distance))
                co2e = quantity * FLIGHT_EF
                category = 'flight'
                scope = 3
                description = f"{origin} → {destination}"
                unit = 'km'

            elif trip_type in ('HOTEL', 'LODGING', 'ACCOMMODATION'):
                nights = Decimal(str(trip.get('nights', trip.get('duration_nights', 1))))
                quantity = nights
                co2e = nights * HOTEL_EF
                category = 'hotel'
                scope = 3
                description = trip.get('hotel_name', trip.get('PropertyName', ''))
                unit = 'nights'

            elif trip_type in ('CAR', 'CAR_RENTAL', 'GROUND', 'TAXI', 'RIDE'):
                distance = Decimal(str(trip.get('distance_km', trip.get('Miles', 50))))
                quantity = distance
                co2e = distance * CAR_EF
                category = 'car_travel'
                scope = 3
                description = trip.get('vendor', trip.get('VendorName', ''))
                unit = 'km'

            elif trip_type in ('RAIL', 'TRAIN'):
                distance = Decimal(str(trip.get('distance_km', 100)))
                quantity = distance
                co2e = distance * RAIL_EF
                category = 'rail_travel'
                scope = 3
                description = trip.get('route', '')
                unit = 'km'

            else:
                quantity = Decimal('0')
                co2e = Decimal('0')
                category = trip_type.lower()
                scope = 3
                description = ''
                unit = 'km'

            record = {
                'scope': scope,
                'category': category,
                'activity_date': activity_date,
                'quantity': quantity,
                'unit': unit,
                'quantity_normalized': quantity,
                'unit_normalized': unit,
                'emission_factor': FLIGHT_EF if category == 'flight' else
                                   HOTEL_EF if category == 'hotel' else CAR_EF,
                'emission_factor_source': 'DEFRA 2023 / GHG Protocol',
                'co2e_kg': co2e,
                'location': trip.get('location', trip.get('city', '')),
                'vendor': trip.get('vendor', trip.get('VendorName', '')),
                'description': description,
                'source_row_id': str(i + 1),
                'raw_data': trip,
            }

            record['flag_reason'] = flag_suspicious(record)
            records.append(record)

        except Exception as e:
            errors.append(f"Trip {i+1}: {str(e)}")

    return records, errors