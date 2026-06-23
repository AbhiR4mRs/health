from django.contrib import admin
from apps.forms_engine.models import FormDefinition, FormField, FormResponse, Answer

class FormFieldInline(admin.TabularInline):
    model = FormField
    extra = 1

@admin.register(FormDefinition)
class FormDefinitionAdmin(admin.ModelAdmin):
    list_display = ('name', 'identifier', 'created_by', 'created_at', 'active')
    inlines = [FormFieldInline]
    prepopulated_fields = {"identifier": ("name",)}
    search_fields = ('name', 'identifier')

class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0
    readonly_fields = ('field', 'value')

@admin.register(FormResponse)
class FormResponseAdmin(admin.ModelAdmin):
    list_display = ('form', 'submitted_by', 'submitted_role', 'center', 'subcenter', 'submitted_at')
    list_filter = ('form', 'center', 'subcenter')
    inlines = [AnswerInline]
    readonly_fields = ('form', 'submitted_by', 'submitted_role', 'center', 'subcenter', 'submitted_at')
