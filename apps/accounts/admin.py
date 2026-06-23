from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from apps.accounts.models import CustomUser

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'email', 'role', 'conductor_role', 'center', 'subcenter', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        ('Hierarchy Scoping Options', {'fields': ('role', 'conductor_role', 'center', 'subcenter')}),
    )
    list_filter = ['role', 'conductor_role', 'is_staff']

admin.site.register(CustomUser, CustomUserAdmin)
