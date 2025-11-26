from django.db import models
from django.conf import settings
from apps.core.models import BaseModel


class FCMDeviceToken(BaseModel):
    """
    Model to store Firebase Cloud Messaging device tokens for push notifications
    """
    DEVICE_TYPE_CHOICES = (
        ('ios', 'iOS'),
        ('android', 'Android'),
        ('web', 'Web'),
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='fcm_tokens',
        help_text="User who owns this device token"
    )
    
    token = models.TextField(
        unique=True,
        help_text="FCM device token"
    )
    
    device_type = models.CharField(
        max_length=10,
        choices=DEVICE_TYPE_CHOICES,
        default='android',
        help_text="Type of device"
    )
    
    device_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Unique device identifier"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this token is currently active"
    )
    
    last_used_at = models.DateTimeField(
        auto_now=True,
        help_text="Last time this token was used"
    )
    
    class Meta:
        verbose_name = "FCM Device Token"
        verbose_name_plural = "FCM Device Tokens"
        unique_together = [['user', 'device_id']]
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['token']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.device_type} - {self.token[:20]}..."


class NotificationLog(BaseModel):
    """
    Model to log sent notifications for tracking and debugging
    """
    NOTIFICATION_TYPE_CHOICES = (
        ('ORDER_STATUS', 'Order Status'),
        ('PAYMENT', 'Payment'),
        ('RIDER_ASSIGNMENT', 'Rider Assignment'),
        ('PROFILE', 'Profile'),
        ('APPOINTMENT', 'Appointment'),
        ('SYSTEM', 'System'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_logs',
        help_text="User who received the notification"
    )
    
    fcm_token = models.ForeignKey(
        FCMDeviceToken,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notification_logs',
        help_text="FCM token used to send notification"
    )
    
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPE_CHOICES,
        help_text="Type of notification"
    )
    
    category = models.CharField(
        max_length=50,
        help_text="Notification category (e.g., order_confirmed, payment_received)"
    )
    
    title = models.CharField(
        max_length=255,
        help_text="Notification title"
    )
    
    body = models.TextField(
        help_text="Notification body/message"
    )
    
    data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional data payload"
    )
    
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Status of notification delivery"
    )
    
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text="Error message if notification failed"
    )
    
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When notification was sent"
    )
    
    is_read = models.BooleanField(
        default=False,
        help_text="Whether the user has read this notification"
    )
    
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the notification was read by the user"
    )
    
    class Meta:
        verbose_name = "Notification Log"
        verbose_name_plural = "Notification Logs"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['notification_type', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['user', 'is_read']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.notification_type} - {self.category} - {self.status}"

