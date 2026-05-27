from django.contrib import admin
from .models import Tenant, DataSource, EmissionRecord, AuditLog

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']

@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ['source_type', 'filename', 'status', 'row_count', 'uploaded_at']

@admin.register(EmissionRecord)
class EmissionRecordAdmin(admin.ModelAdmin):
    list_display = ['category', 'scope', 'quantity', 'unit', 'co2e_kg', 'status', 'activity_date']
    list_filter = ['scope', 'status', 'source__source_type']
    search_fields = ['category', 'location', 'vendor']

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'changed_by', 'changed_at', 'note']