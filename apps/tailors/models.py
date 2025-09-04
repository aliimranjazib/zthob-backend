from django.db import models
from django.conf import settings

# Create your models here.
class TailorProfile(models.Model):
    user=models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,
                              related_name='tailor_prpfile')
    shop_name=models.CharField(max_length=100)
    contact_number=models.CharField(max_length=20,null=True,blank=True)
    establishment_year=models.PositiveIntegerField()
    tailor_experience=models.PositiveIntegerField()
    working_hours=models.JSONField(default=dict,blank=True,null=True)
    address = models.TextField(max_length=250, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    shop_status=models.BooleanField(default=True)