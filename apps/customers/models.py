from django.db import models
from django.conf import settings

# Create your models here.

class Address(models.Model):
    ADDRESS_TAG_CHOICES = [
        ('home', 'Home'),
        ('office', 'Office'),
        ('work', 'Work'),
        ('other', 'Other'),
    ]
    
    user=models.ForeignKey(settings.AUTH_USER_MODEL,
                            on_delete=models.CASCADE, 
                            related_name="addresses", 
                            null=True, blank=True)
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state_province = models.CharField(max_length=100, blank=True, null=True)
    zip_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, default="Saudi Arabia")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    is_default = models.BooleanField(default=False)
    formatted_address = models.TextField(blank=True, null=True, help_text="Full formatted address from Google Maps API")
    address_tag = models.CharField(max_length=20, choices=ADDRESS_TAG_CHOICES, default='home', help_text="Address type: home, office, work, other")
    extra_info = models.TextField(blank=True, null=True, help_text="Additional address information")
    class Meta:
        verbose_name_plural = "Addresses"

    

    def __str__(self):
        return f"{self.street}, {self.city}"
    
    def save(self, *args, **kwargs):
        if self.is_default and self.user:  # Added check for self.user
        # unset other defaults for this user
            Address.objects.filter(user=self.user, is_default=True).update(is_default=False)
        
        super().save(*args, **kwargs)



class CustomerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                null=True, blank=True,
                                related_name='customer_profile')
    gender=models.CharField(max_length=10, blank=True,null=True)
    date_of_birth=models.DateField(blank=True,null=True)
    default_address=models.ForeignKey(Address, on_delete=models.SET_NULL,
                                    null=True,
                                    blank=True,
                                    related_name="default_for_customers")
    loyalty_points = models.IntegerField(null=True, blank=True)
    tags=models.CharField(max_length=20, blank=True, null=True)
    def __str__(self):
        return f"Customer Profile for {self.user.username}"
    
class FamilyMember(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                            related_name="family_profile")
    name = models.CharField(max_length=255)
    gender = models.CharField(max_length=10, blank=True, null=True)
    relationship = models.CharField(max_length=50, blank=True, null=True)
    measurements = models.JSONField(blank=True, null=True)
    address=models.ForeignKey(Address, on_delete=models.CASCADE, null=True,blank=True)
    
    def __str__(self):
        return f"{self.name} ({self.relationship}) for {self.user.username}"