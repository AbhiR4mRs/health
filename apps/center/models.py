from django.db import models

class Center(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'center_centers'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"
