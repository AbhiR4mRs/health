from django.contrib import admin
from apps.surveys.models import HealthSurvey, SurveyMember

class SurveyMemberInline(admin.TabularInline):
    model = SurveyMember
    extra = 1

@admin.register(HealthSurvey)
class HealthSurveyAdmin(admin.ModelAdmin):
    list_display = ('house_number', 'panchayat', 'ward', 'family_head_name', 'family_members_count', 'submitted_by', 'submitted_at')
    list_filter = ('center', 'subcenter', 'submitted_at')
    search_fields = ('house_number', 'family_head_name', 'panchayat', 'ward')
    inlines = [SurveyMemberInline]

@admin.register(SurveyMember)
class SurveyMemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'age', 'gender', 'vaccination_status', 'is_pregnant', 'has_diabetes', 'has_cancer')
    list_filter = ('gender', 'vaccination_status', 'is_pregnant', 'has_diabetes', 'has_cancer')
    search_fields = ('name', 'diseases')
