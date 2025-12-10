from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
class CustomUser(AbstractUser):
    USER_ROLES=(
      ('USER','User'),
      ("RIDER","Rider"),
      ("TAILOR","Tailor"),
      ("ADMIN", "Admin"),
    )
    role=models.CharField(max_length=10,choices=USER_ROLES, default="USER")
    email=models.EmailField(blank=True,null=True,max_length=100)
    phone=models.CharField(max_length=15,blank=True,null=True,unique=True,db_index=True)
    is_active=models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    phone_verified=models.BooleanField(default=False,help_text="Is phone number verified?")
    date_of_birth=models.DateField(blank=True,null=True,help_text="User's date of birth")
    USERNAME_FIELD='username'
    REQUIRED_FIELDS=[]
    
    def soft_delete(self):
      """Mark user as deleted instead of hard deleting"""
      self.is_active = False
      self.is_deleted = True
      self.save()
    
    def __str__(self):
      return f"{self.username} ({self.email}) ({self.role})"