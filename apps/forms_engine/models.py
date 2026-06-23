from django.db import models
from django.conf import settings

class FormDefinition(models.Model):
    name = models.CharField(max_length=255)
    identifier = models.SlugField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_forms'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = 'forms_definition'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

class FormField(models.Model):
    class FieldType(models.TextChoices):
        TEXT = 'TEXT', 'Text'
        TEXTAREA = 'TEXTAREA', 'TextArea'
        NUMBER = 'NUMBER', 'Number'
        DATE = 'DATE', 'Date'
        EMAIL = 'EMAIL', 'Email'
        PHONE = 'PHONE', 'Phone'
        SELECT = 'SELECT', 'Select'
        CHECKBOX = 'CHECKBOX', 'Checkbox'
        RADIO = 'RADIO', 'Radio'
        MULTISELECT = 'MULTISELECT', 'MultiSelect'
        FILE = 'FILE', 'File Upload'

    form = models.ForeignKey(
        FormDefinition,
        on_delete=models.CASCADE,
        related_name='fields'
    )
    label = models.CharField(max_length=255)
    field_type = models.CharField(
        max_length=20,
        choices=FieldType.choices,
        default=FieldType.TEXT
    )
    required = models.BooleanField(default=True)
    placeholder = models.CharField(max_length=255, blank=True, null=True)
    options = models.TextField(
        blank=True,
        null=True,
        help_text="Comma-separated values for Select, Radio, Checkbox, MultiSelect"
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'forms_field'
        ordering = ['order']

    def __str__(self):
        return f"{self.label} ({self.field_type}) in {self.form.name}"

    def get_options_list(self):
        if self.options:
            return [opt.strip() for opt in self.options.split(',') if opt.strip()]
        return []

class FormResponse(models.Model):
    form = models.ForeignKey(
        FormDefinition,
        on_delete=models.CASCADE,
        related_name='responses'
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='submitted_form_responses'
    )
    submitted_role = models.CharField(max_length=50)
    center = models.ForeignKey(
        'center.Center',
        on_delete=models.CASCADE,
        related_name='form_responses'
    )
    subcenter = models.ForeignKey(
        'subcenter.Subcenter',
        on_delete=models.CASCADE,
        related_name='form_responses'
    )
    submitted_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'forms_response'
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['form', 'center', 'subcenter', 'submitted_at']),
        ]

    def __str__(self):
        return f"{self.form.name} response by {self.submitted_by.username} at {self.submitted_at}"

class Answer(models.Model):
    response = models.ForeignKey(
        FormResponse,
        on_delete=models.CASCADE,
        related_name='answers'
    )
    field = models.ForeignKey(
        FormField,
        on_delete=models.CASCADE,
        related_name='answers'
    )
    value = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'forms_answer'
        unique_together = ('response', 'field')

    def __str__(self):
        return f"Ans for {self.field.label}: {self.value}"
