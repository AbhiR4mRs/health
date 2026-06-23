from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        HQ = 'HQ', 'Headquarters'
        CENTER = 'CENTER', 'Center'
        SUBCENTER = 'SUBCENTER', 'Subcenter'
        CONDUCTOR = 'CONDUCTOR', 'Survey Conductor'

    class ConductorRole(models.TextChoices):
        JHI = 'JHI', 'Junior Health Inspector'
        JPHN = 'JPHN', 'Junior Public Health Nurse'
        ASHA = 'ASHA', 'Accredited Social Health Activist'
        MLSP = 'MLSP', 'Mid-Level Service Provider'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CONDUCTOR
    )
    center = models.ForeignKey(
        'center.Center',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )
    subcenter = models.ForeignKey(
        'subcenter.Subcenter',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )
    conductor_role = models.CharField(
        max_length=10,
        choices=ConductorRole.choices,
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'accounts_customuser'
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['center']),
            models.Index(fields=['subcenter']),
        ]

    def __str__(self):
        role_desc = self.conductor_role if self.role == self.Role.CONDUCTOR else self.role
        return f"{self.username} - {role_desc}"

class AuditLog(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=255)
    ip_address = models.CharField(max_length=50, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'accounts_audit_log'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username if self.user else 'System'} - {self.action} at {self.timestamp}"
