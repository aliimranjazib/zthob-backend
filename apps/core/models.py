from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone

User = get_user_model()

class PhoneVerification(models.Model):
    """Reusable phone verification model for all user types"""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='phone_verifications'
    )
    phone_number = models.CharField(max_length=20)
    otp_code = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Phone Verification"
        verbose_name_plural = "Phone Verifications"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.phone_number} - {self.otp_code}"
    
    def is_expired(self):
        """Check if OTP has expired"""
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        """Check if OTP is valid and not expired"""
        return not self.is_expired() and not self.is_verified



class BaseModel(models.Model):
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    created_by=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True,related_name="%(class)s_created")
    

    class Meta:
        abstract=True
        ordering=['-created_at']
