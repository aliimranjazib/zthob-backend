# apps/tailors/models/review.py
from django.db import models
from django.conf import settings

class TailorProfileReview(models.Model):
    """Model for tracking tailor profile review process."""
    
    REVIEW_STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    profile = models.OneToOneField(
        'TailorProfile',
        on_delete=models.CASCADE,
        related_name='review'
    )
    review_status = models.CharField(
        max_length=20,
        choices=REVIEW_STATUS_CHOICES,
        default='draft',
        help_text="Review status of the tailor profile"
    )
    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the profile was submitted for review"
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the profile was reviewed by admin"
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_tailor_profiles',
        help_text="Admin who reviewed this profile"
    )
    rejection_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for rejection if applicable"
    )
    service_areas = models.JSONField(
        default=list,
        blank=True,
        help_text="List of cities/areas served by this tailor"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Profile Review"
        verbose_name_plural = "Profile Reviews"
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"Review for {self.profile.shop_name} - {self.review_status}"