from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from .models import Tenant, DataSource, EmissionRecord
from .parsers import parse_sap, parse_utility, parse_travel


class IngestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, source_type):
        source_type = source_type.upper()
        if source_type not in ['SAP', 'UTILITY', 'TRAVEL']:
            return Response({'error': 'Invalid source type'}, status=400)

        # Get or create tenant for this user
        tenant, _ = Tenant.objects.get_or_create(
            slug=f"tenant-{request.user.id}",
            defaults={'name': f"{request.user.username}'s Org"}
        )

        # Create a DataSource record
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({'error': 'No file uploaded'}, status=400)

        file_content = uploaded_file.read().decode('utf-8', errors='replace')
        filename = uploaded_file.name

        data_source = DataSource.objects.create(
            tenant=tenant,
            source_type=source_type,
            filename=filename,
            uploaded_by=request.user,
            status='PROCESSING',
        )

        # Parse based on type
        try:
            if source_type == 'SAP':
                records, errors = parse_sap(file_content)
            elif source_type == 'UTILITY':
                records, errors = parse_utility(file_content)
            elif source_type == 'TRAVEL':
                records, errors = parse_travel(file_content)

            # Save records
            created = []
            for r in records:
                obj = EmissionRecord.objects.create(
                    tenant=tenant,
                    source=data_source,
                    scope=r['scope'],
                    category=r['category'],
                    activity_date=r['activity_date'] or '2024-01-01',
                    quantity=r['quantity'],
                    unit=r['unit'],
                    quantity_normalized=r['quantity_normalized'],
                    unit_normalized=r['unit_normalized'],
                    emission_factor=r['emission_factor'],
                    emission_factor_source=r['emission_factor_source'],
                    co2e_kg=r['co2e_kg'],
                    location=r['location'],
                    vendor=r['vendor'],
                    description=r['description'],
                    source_row_id=r['source_row_id'],
                    raw_data=r['raw_data'],
                    flag_reason=r['flag_reason'],
                    status='FLAGGED' if r['flag_reason'] else 'PENDING',
                )
                created.append(obj.id)

            data_source.status = 'DONE'
            data_source.row_count = len(created)
            data_source.error_message = '\n'.join(errors)
            data_source.save()

            return Response({
                'message': f'{len(created)} records ingested',
                'source_id': str(data_source.id),
                'errors': errors,
            }, status=201)

        except Exception as e:
            data_source.status = 'FAILED'
            data_source.error_message = str(e)
            data_source.save()
            return Response({'error': str(e)}, status=500)


class RecordsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tenant, _ = Tenant.objects.get_or_create(
            slug=f"tenant-{request.user.id}",
            defaults={'name': f"{request.user.username}'s Org"}
        )
        records = EmissionRecord.objects.filter(tenant=tenant)

        # Filters
        scope = request.query_params.get('scope')
        status_filter = request.query_params.get('status')
        source_type = request.query_params.get('source_type')

        if scope:
            records = records.filter(scope=scope)
        if status_filter:
            records = records.filter(status=status_filter)
        if source_type:
            records = records.filter(source__source_type=source_type.upper())

        data = []
        for r in records:
            data.append({
                'id': str(r.id),
                'scope': r.scope,
                'category': r.category,
                'activity_date': str(r.activity_date),
                'quantity': str(r.quantity),
                'unit': r.unit,
                'co2e_kg': str(r.co2e_kg) if r.co2e_kg else None,
                'location': r.location,
                'vendor': r.vendor,
                'description': r.description,
                'status': r.status,
                'flag_reason': r.flag_reason,
                'source_type': r.source.source_type,
                'created_at': str(r.created_at),
            })

        return Response(data)


class ReviewView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, record_id):
        try:
            tenant, _ = Tenant.objects.get_or_create(
                slug=f"tenant-{request.user.id}",
                defaults={'name': f"{request.user.username}'s Org"}
            )
            record = EmissionRecord.objects.get(id=record_id, tenant=tenant)
        except EmissionRecord.DoesNotExist:
            return Response({'error': 'Record not found'}, status=404)

        new_status = request.data.get('status')
        note = request.data.get('note', '')

        if new_status not in ['APPROVED', 'FLAGGED', 'REJECTED', 'PENDING']:
            return Response({'error': 'Invalid status'}, status=400)

        from django.utils import timezone
        from .models import AuditLog

        old_status = record.status
        record.status = new_status
        record.flag_reason = request.data.get('flag_reason', record.flag_reason)
        record.reviewed_by = request.user
        record.reviewed_at = timezone.now()
        record.save()

        AuditLog.objects.create(
            record=record,
            changed_by=request.user,
            action=new_status,
            before={'status': old_status},
            after={'status': new_status},
            note=note,
        )

        return Response({'message': f'Record {new_status.lower()}'})


class StatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tenant, _ = Tenant.objects.get_or_create(
            slug=f"tenant-{request.user.id}",
            defaults={'name': f"{request.user.username}'s Org"}
        )
        records = EmissionRecord.objects.filter(tenant=tenant)

        total = records.count()
        pending = records.filter(status='PENDING').count()
        approved = records.filter(status='APPROVED').count()
        flagged = records.filter(status='FLAGGED').count()
        rejected = records.filter(status='REJECTED').count()

        total_co2e = sum(
            float(r.co2e_kg) for r in records
            if r.co2e_kg and r.status == 'APPROVED'
        )

        scope1 = sum(float(r.co2e_kg) for r in records if r.scope == 1 and r.co2e_kg)
        scope2 = sum(float(r.co2e_kg) for r in records if r.scope == 2 and r.co2e_kg)
        scope3 = sum(float(r.co2e_kg) for r in records if r.scope == 3 and r.co2e_kg)

        return Response({
            'total_records': total,
            'pending': pending,
            'approved': approved,
            'flagged': flagged,
            'rejected': rejected,
            'approved_co2e_kg': round(total_co2e, 2),
            'scope1_co2e_kg': round(scope1, 2),
            'scope2_co2e_kg': round(scope2, 2),
            'scope3_co2e_kg': round(scope3, 2),
        })