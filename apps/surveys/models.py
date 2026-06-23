from django.db import models
from django.conf import settings

class HealthSurvey(models.Model):
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='health_surveys'
    )
    submitted_role = models.CharField(max_length=50)
    center = models.ForeignKey(
        'center.Center',
        on_delete=models.CASCADE,
        related_name='health_surveys'
    )
    subcenter = models.ForeignKey(
        'subcenter.Subcenter',
        on_delete=models.CASCADE,
        related_name='health_surveys'
    )
    submitted_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # House Details
    house_number = models.CharField(max_length=50)
    ward = models.CharField(max_length=100, db_index=True)
    panchayat = models.CharField(max_length=100, db_index=True)
    address = models.TextField()

    # Family Details
    family_head_name = models.CharField(max_length=255)
    family_members_count = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = 'surveys_health_survey'
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['center', 'subcenter', 'submitted_at']),
            models.Index(fields=['ward', 'panchayat']),
        ]

    def __str__(self):
        return f"House {self.house_number}, Ward {self.ward} by {self.submitted_by.username}"

class SurveyMember(models.Model):
    class Gender(models.TextChoices):
        MALE = 'M', 'Male'
        FEMALE = 'F', 'Female'
        OTHER = 'O', 'Other'

    class VaccinationStatus(models.TextChoices):
        FULLY = 'FULLY', 'Fully Vaccinated'
        PARTIALLY = 'PARTIALLY', 'Partially Vaccinated'
        NOT = 'NOT', 'Not Vaccinated'

    survey = models.ForeignKey(
        HealthSurvey,
        on_delete=models.CASCADE,
        related_name='members'
    )
    name = models.CharField(max_length=255)
    age = models.PositiveIntegerField(db_index=True)
    gender = models.CharField(max_length=1, choices=Gender.choices, db_index=True)
    occupation = models.CharField(max_length=100, blank=True, null=True)

    # Health Details
    diseases = models.TextField(blank=True, null=True, help_text="Comma-separated diseases (e.g. Fever, Hypertension, Tuberculosis)")
    disabilities = models.TextField(blank=True, null=True)
    vaccination_status = models.CharField(
        max_length=20,
        choices=VaccinationStatus.choices,
        default=VaccinationStatus.NOT,
        db_index=True
    )
    is_pregnant = models.BooleanField(default=False, db_index=True)
    blood_pressure_systolic = models.PositiveIntegerField(blank=True, null=True)
    blood_pressure_diastolic = models.PositiveIntegerField(blank=True, null=True)
    has_diabetes = models.BooleanField(default=False, db_index=True)
    has_cancer = models.BooleanField(default=False, db_index=True)
    mental_health_indicators = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'surveys_survey_member'
        ordering = ['name']
        indexes = [
            models.Index(fields=['age', 'gender']),
            models.Index(fields=['has_diabetes', 'has_cancer', 'is_pregnant']),
        ]

    def __str__(self):
        return f"{self.name} ({self.age}/{self.gender}) - {self.survey.house_number}"

    def get_diseases_list(self):
        if self.diseases:
            return [d.strip().lower() for d in self.diseases.split(',') if d.strip()]
        return []
