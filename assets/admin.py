from django.contrib import admin
from .models import Asset


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display  = ('name', 'asset_type', 'acquisition_value', 'status', 'location')
    list_filter   = ('asset_type', 'status')
    search_fields = ('name',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)

    def save_model(self, request, obj, form, change):
        if not change:          # somente na criação
            obj.user = request.user
        super().save_model(request, obj, form, change)

    def get_fields(self, request, obj=None):
        fields = ['name', 'asset_type', 'acquisition_value', 'purchase_date', 'status', 'location', 'notes']
        if request.user.is_superuser:
            fields.insert(0, 'user')
        return fields
