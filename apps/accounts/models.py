from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
class CustomUser(AbstractUser):
    USER_ROLES=(
      ('USER','User'),
      ("RIDER","Rider"),
      ("TAILOR","Tailor"),
    )
    role=models.CharField(max_length=10,choices=USER_ROLES, default="USER")
    email=models.EmailField(unique=True,max_length=100)
    phone=models.CharField(max_length=15,blank=True,null=True)
    address=models.TextField(max_length=100,blank=True,null=True)
    measurement=models.JSONField(blank=True,null=True)
    vehicle_info=models.CharField(blank=True,null=True,max_length=50)
    license_number=models.CharField(blank=True,null=True,max_length=50)
    shop_name=models.CharField(blank=True,null=True,max_length=50)
    experience_years=models.PositiveIntegerField(blank=True,null=True,default=None)
    is_active=models.BooleanField(default=True)
    USERNAME_FIELD='username'
    REQUIRED_FIELDS=['email']
    
def __str__(self):
    return f"{self.username} ({self.email}) ({self.role})"