from django.db import models
from django.core.validators import FileExtensionValidator
from django.utils.text import slugify

IMAGE_VALIDATOR = [FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png"])]

SEASON_CHOICES = [
    ('summer', 'Summer'),
    ('winter', 'Winter'),
    ('all_season', 'All Season'),
]
class SluggedModel(models.Model):
    """Abstract base class with slug field."""
    slug = models.SlugField(max_length=120, unique=True)
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

