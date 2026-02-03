from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator, RegexValidator
from apps.core.models import BaseModel


class RiderProfileReview(models.Model):
    """Model for tracking rider profile review process."""
    
    REVIEW_STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    profile = models.OneToOneField(
        'RiderProfile',
        on_delete=models.CASCADE,
        related_name='review',
        help_text="Rider profile being reviewed"
    )
    review_status = models.CharField(
        max_length=20,
        choices=REVIEW_STATUS_CHOICES,
        default='draft',
        help_text="Review status of the rider profile"
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
        related_name='reviewed_rider_profiles',
        help_text="Admin who reviewed this profile"
    )
    rejection_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for rejection if applicable"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Rider Profile Review"
        verbose_name_plural = "Rider Profile Reviews"
        ordering = ['-submitted_at']
    
    def __str__(self):
        rider_name = self.profile.full_name or self.profile.user.username if self.profile.user else 'Unknown'
        return f"Review for {rider_name} - {self.review_status}"


class RiderProfile(BaseModel):
    """
    Rider Profile Model
    Stores additional information for riders
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='rider_profile',
        help_text="User account for this rider"
    )
    
    # Personal Information
    full_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Full name of the rider"
    )
    
    # National Identity / Iqama
    iqama_number = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        unique=True,
        validators=[RegexValidator(regex=r'^\d{10}$', message='Iqama number must be exactly 10 digits')],
        help_text="Iqama Number (10-digit) or Saudi National ID for citizens"
    )
    
    iqama_expiry_date = models.DateField(
        blank=True,
        null=True,
        help_text="Iqama / National ID expiry date"
    )
    
    # Contact Information
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Primary contact number"
    )
    
    emergency_contact = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Emergency contact number"
    )
    
    # Driving License Information
    license_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Driving license number"
    )
    
    license_expiry_date = models.DateField(
        blank=True,
        null=True,
        help_text="Driving license expiry date"
    )
    
    license_type = models.CharField(
        max_length=50,
        choices=[
            ('private', 'Private'),
            ('general', 'General'),
            ('motorcycle', 'Motorcycle'),
            ('commercial', 'Commercial'),
        ],
        blank=True,
        null=True,
        help_text="Type of driving license"
    )
    
    # Vehicle Information
    vehicle_type = models.CharField(
        max_length=50,
        choices=[
            ('motorcycle', 'Motorcycle'),
            ('car', 'Car'),
            ('bicycle', 'Bicycle'),
            ('truck', 'Truck'),
            ('van', 'Van'),
            ('other', 'Other'),
        ],
        blank=True,
        null=True,
        help_text="Type of vehicle used for delivery"
    )
    
    vehicle_plate_number_arabic = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Vehicle plate number in Arabic"
    )
    
    vehicle_plate_number_english = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Vehicle plate number in English"
    )
    
    vehicle_make = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Vehicle make/brand (e.g., Toyota, Honda)"
    )
    
    vehicle_model = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Vehicle model (e.g., Camry, Accord)"
    )
    
    vehicle_year = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Vehicle manufacturing year"
    )
    
    vehicle_color = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Vehicle color"
    )
    
    vehicle_registration_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Vehicle Registration (Istimara) Number"
    )
    
    vehicle_registration_expiry_date = models.DateField(
        blank=True,
        null=True,
        help_text="Vehicle Registration (Istimara) expiry date"
    )
    
    # Insurance Details
    insurance_provider = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Insurance provider name"
    )
    
    insurance_policy_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Insurance policy number"
    )
    
    insurance_expiry_date = models.DateField(
        blank=True,
        null=True,
        help_text="Insurance expiry date"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the rider is currently active"
    )
    
    is_available = models.BooleanField(
        default=True,
        help_text="Whether the rider is currently available for new orders"
    )
    
    # Approval status (managed through RiderProfileReview)
    @property
    def is_approved(self):
        """Check if rider profile is approved"""
        try:
            return self.review.review_status == 'approved'
        except RiderProfileReview.DoesNotExist:
            return False
    
    @property
    def review_status(self):
        """Get current review status"""
        try:
            return self.review.review_status
        except RiderProfileReview.DoesNotExist:
            return 'draft'
    
    # Location (for tracking)
    current_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        help_text="Current latitude location"
    )
    
    current_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        help_text="Current longitude location"
    )
    
    # Statistics
    total_deliveries = models.PositiveIntegerField(
        default=0,
        help_text="Total number of completed deliveries"
    )
    
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        help_text="Average rating from customers"
    )
    
    class Meta:
        verbose_name = "Rider Profile"
        verbose_name_plural = "Rider Profiles"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.full_name or self.user.username} - {self.phone_number}"


class RiderDocument(models.Model):
    """
    Model for storing rider documents (Iqama, License, Istimara, Insurance)
    """
    DOCUMENT_TYPE_CHOICES = (
        ('iqama_front', 'Iqama Front'),
        ('iqama_back', 'Iqama Back'),
        ('license_front', 'Driving License Front'),
        ('license_back', 'Driving License Back'),
        ('istimara_front', 'Istimara Front'),
        ('istimara_back', 'Istimara Back'),
        ('insurance', 'Insurance Card'),
    )
    
    rider_profile = models.ForeignKey(
        RiderProfile,
        on_delete=models.CASCADE,
        related_name='documents',
        help_text="Rider profile this document belongs to"
    )
    
    document_type = models.CharField(
        max_length=50,
        choices=DOCUMENT_TYPE_CHOICES,
        help_text="Type of document"
    )
    
    document_image = models.ImageField(
        upload_to='rider_documents/',
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'pdf'])],
        help_text="Document image (JPG, JPEG, PNG, PDF)"
    )
    
    is_verified = models.BooleanField(
        default=False,
        help_text="Whether this document has been verified by admin"
    )
    
    verified_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the document was verified"
    )
    
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_rider_documents',
        help_text="Admin who verified this document"
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Admin notes about this document"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Rider Document"
        verbose_name_plural = "Rider Documents"
        ordering = ['-created_at']
        unique_together = [['rider_profile', 'document_type']]
    
    def __str__(self):
        return f"{self.rider_profile.full_name or self.rider_profile.user.username} - {self.get_document_type_display()}"


class RiderOrderAssignment(BaseModel):
    """
    Tracks rider assignments to orders
    """
    ASSIGNMENT_STATUS_CHOICES = (
        ('pending', 'Pending Acceptance'),
        ('accepted', 'Accepted'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='rider_assignment',
        help_text="Order assigned to this rider"
    )
    
    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assigned_orders',
        help_text="Rider assigned to this order"
    )
    
    status = models.CharField(
        max_length=20,
        choices=ASSIGNMENT_STATUS_CHOICES,
        default='pending',
        help_text="Status of the assignment"
    )
    
    accepted_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the rider accepted the order"
    )
    
    started_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the rider started working on the order"
    )
    
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the rider completed the delivery"
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes from the rider"
    )
    
    class Meta:
        verbose_name = "Rider Order Assignment"
        verbose_name_plural = "Rider Order Assignments"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.rider.username} - {self.order.order_number} - {self.status}"


class TailorInvitationCode(BaseModel):
    """
    Invitation codes for riders to join a tailor's delivery team.
    Tailors generate unique codes that riders can enter to associate themselves.
    """
    tailor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='rider_invitation_codes',
        limit_choices_to={'role': 'TAILOR'},
        help_text="Tailor who created this invitation code"
    )
    
    code = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Unique invitation code (e.g., TAL-42-X7K9P)"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this code can still be used"
    )
    
    max_uses = models.PositiveIntegerField(
        default=0,
        help_text="Maximum number of times this code can be used (0 = unlimited)"
    )
    
    times_used = models.PositiveIntegerField(
        default=0,
        help_text="How many times this code has been used"
    )
    
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this code expires (null = never)"
    )
    
    class Meta:
        verbose_name = "Tailor Invitation Code"
        verbose_name_plural = "Tailor Invitation Codes"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['tailor', 'is_active']),
        ]
    
    def __str__(self):
        tailor_name = self.tailor.username
        if hasattr(self.tailor, 'tailor_profile') and self.tailor.tailor_profile:
            tailor_name = self.tailor.tailor_profile.shop_name or tailor_name
        return f"{tailor_name} - {self.code}"
    
    def can_be_used(self):
        """
        Check if code is still valid.
        Returns: (bool, str) - (is_valid, error_message)
        """
        from django.utils import timezone
        
        if not self.is_active:
            return False, "Code is inactive"
        
        if self.expires_at and timezone.now() > self.expires_at:
            return False, "Code has expired"
        
        if self.max_uses > 0 and self.times_used >= self.max_uses:
            return False, "Code has reached maximum uses"
        
        return True, "Valid"
    
    @staticmethod
    def generate_unique_code(tailor_id):
        """
        Generate a unique invitation code for a tailor.
        Format: TAL-{TAILOR_ID}-{RANDOM}
        Example: TAL-42-X7K9P
        """
        import random
        import string
        
        # Generate random 5-character string
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        code = f"TAL-{tailor_id}-{random_part}"
        
        # Ensure uniqueness (very unlikely to collide, but check anyway)
        while TailorInvitationCode.objects.filter(code=code).exists():
            random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            code = f"TAL-{tailor_id}-{random_part}"
        
        return code


class TailorRiderAssociation(BaseModel):
    """
    Represents the relationship between a tailor and a rider.
    Created when a rider uses a tailor's invitation code.
    """
    tailor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='associated_riders',
        limit_choices_to={'role': 'TAILOR'},
        help_text="Tailor in this association"
    )
    
    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='associated_tailors',
        limit_choices_to={'role': 'RIDER'},
        help_text="Rider in this association"
    )
    
    joined_via_code = models.ForeignKey(
        TailorInvitationCode,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='associations',
        help_text="The invitation code used to join (for tracking)"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this association is currently active"
    )
    
    nickname = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional friendly name/nickname for this rider (set by tailor)"
    )
    
    priority = models.PositiveIntegerField(
        default=0,
        help_text="Priority/ranking for this rider (higher = more preferred)"
    )
    
    class Meta:
        verbose_name = "Tailor-Rider Association"
        verbose_name_plural = "Tailor-Rider Associations"
        ordering = ['-priority', '-created_at']
        unique_together = [['tailor', 'rider']]
        indexes = [
            models.Index(fields=['tailor', 'is_active']),
            models.Index(fields=['rider', 'is_active']),
        ]
    
    def __str__(self):
        tailor_name = self.tailor.username
        if hasattr(self.tailor, 'tailor_profile') and self.tailor.tailor_profile:
            tailor_name = self.tailor.tailor_profile.shop_name or tailor_name
        
        rider_name = self.rider.username
        if hasattr(self.rider, 'rider_profile') and self.rider.rider_profile:
            rider_name = self.rider.rider_profile.full_name or rider_name
        
        return f"{tailor_name} ↔ {rider_name}"

