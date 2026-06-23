from django.contrib import admin
from apps.subcenter.models import Subcenter

@admin.register(Subcenter)
class SubcenterAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'center', 'created_at')
    list_filter = ('center',)
    search_fields = ('name', 'code')
