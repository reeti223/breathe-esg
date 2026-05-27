from django.db import models
from django.contrib.auth.models import User
import uuid


class Tenant(models.Model):
    """One row per client company."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class DataSource(models.Model):
    """Tracks every ingest job — who uploaded what, when."""
    SOURCE_TYPES = [
        ('SAP', 'SAP Fuel & Procurement'),
        ('UTILITY', 'Utility / Electricity'),
        ('TRAVEL', 'Corporate Travel'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('DONE', 'Done'),
        ('FAILED', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='sources')
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    filename = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    row_count = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)

    def __str__(self):
        return f"{self.source_type} — {self.filename} ({self.status})"


class EmissionRecord(models.Model):
    """
    One normalized row of emission activity.
    This is the core of the data model.
    """
    SCOPE_CHOICES = [
        (1, 'Scope 1 — Direct emissions'),
        (2, 'Scope 2 — Purchased electricity'),
        (3, 'Scope 3 — Value chain'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('FLAGGED', 'Flagged / Suspicious'),
        ('REJECTED', 'Rejected'),
    ]
    UNIT_CHOICES = [
        ('kWh', 'Kilowatt-hours'),
        ('MWh', 'Megawatt-hours'),
        ('L', 'Litres'),
        ('m3', 'Cubic metres'),
        ('kg', 'Kilograms'),
        ('t', 'Metric tonnes'),
        ('km', 'Kilometres'),
        ('mi', 'Miles'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='records')
    source = models.ForeignKey(DataSource, on_delete=models.CASCADE, related_name='records')

    # Scope and category
    scope = models.IntegerField(choices=SCOPE_CHOICES)
    category = models.CharField(max_length=100)  # e.g. "diesel", "electricity", "flight"

    # Activity data (what was consumed / done)
    activity_date = models.DateField()
    quantity = models.DecimalField(max_digits=15, decimal_places=4)
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES)
    quantity_normalized = models.DecimalField(max_digits=15, decimal_places=4, null=True)
    unit_normalized = models.CharField(max_length=10, blank=True)

    # Emission calculation
    emission_factor = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    emission_factor_source = models.CharField(max_length=255, blank=True)
    co2e_kg = models.DecimalField(max_digits=15, decimal_places=4, null=True)

    # Source tracking
    raw_data = models.JSONField(default=dict)       # original row as-ingested
    source_row_id = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, blank=True)
    vendor = models.CharField(max_length=255, blank=True)
    description = models.CharField(max_length=500, blank=True)

    # Review workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    flag_reason = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_records'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # Audit trail
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_edited = models.BooleanField(default=False)
    edit_note = models.TextField(blank=True)

    class Meta:
        ordering = ['-activity_date']

    def __str__(self):
        return f"{self.category} | {self.quantity} {self.unit} | {self.activity_date}"


class AuditLog(models.Model):
    """Every change to an EmissionRecord is logged here."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    record = models.ForeignKey(EmissionRecord, on_delete=models.CASCADE, related_name='audit_logs')
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=50)   # e.g. APPROVED, FLAGGED, EDITED
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['-changed_at']

    def __str__(self):
        return f"{self.action} on {self.record_id} by {self.changed_by}"