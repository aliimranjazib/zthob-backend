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
    LANGUAGE_CHOICES = (
        ('en', 'English'),
        ('ar', 'Arabic'),
    )
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default='ar')
    
    @property
    def is_customer(self):
        """Check if user has a customer profile or USER role"""
        return hasattr(self, 'customer_profile') or self.role == 'USER'
    
    @property
    def is_tailor(self):
        """Check if user has a tailor profile or TAILOR role"""
        return hasattr(self, 'tailor_profile') or self.role == 'TAILOR'
    
    @property
    def is_rider(self):
        """Check if user has a rider profile or RIDER role"""
        return hasattr(self, 'rider_profile') or self.role == 'RIDER'

    @property
    def is_admin(self):
        """Check if user is a staff member or admin"""
        return self.is_staff or self.role == 'ADMIN'

    def get_all_roles(self):
        """Return list of all active roles for this user"""
        roles = []
        if self.is_customer: roles.append('USER')
        if self.is_tailor: roles.append('TAILOR')
        if self.is_rider: roles.append('RIDER')
        if self.is_admin: roles.append('ADMIN')
        return roles

    def remove_role(self, role_name):
        """
        Safely removes a specific role and its associated data.
        Does NOT delete the user account.
        """
        role_name = role_name.upper()
        
        if role_name == 'TAILOR' and hasattr(self, 'tailor_profile'):
            self.tailor_profile.delete()
        elif role_name == 'RIDER' and hasattr(self, 'rider_profile'):
            self.rider_profile.delete()
        
        # If the removed role was the primary role, revert to USER
        if self.role == role_name:
            self.role = 'USER'
            self.save()

    USERNAME_FIELD='username'
    REQUIRED_FIELDS=[]
    
    def soft_delete(self):
      """Mark user as deleted instead of hard deleting"""
      self.is_active = False
      self.is_deleted = True
      self.save()
    
    def __str__(self):
      return f"{self.username} ({self.email}) ({self.role})"