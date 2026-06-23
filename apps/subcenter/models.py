from django.db import models

class Subcenter(models.Model):
    center = models.ForeignKey(
        'center.Center',
        on_delete=models.CASCADE,
        related_name='subcenters'
    )
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'subcenter_subcenters'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"
