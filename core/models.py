from django.db import models


class BaseModel(models.Model):
    """
    Abstract base model with common fields
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SiteConfiguration(models.Model):
    """
    Site-wide configuration settings
    """
    site_name = models.CharField(max_length=200, default='Marifetli')
    site_description = models.TextField(blank=True)
    contact_email = models.EmailField()
    is_maintenance_mode = models.BooleanField(default=False)
    maintenance_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.site_name} Configuration"

    class Meta:
        verbose_name_plural = "Site Configurations"