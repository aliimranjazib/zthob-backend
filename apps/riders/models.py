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

