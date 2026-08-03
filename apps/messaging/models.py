from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class AdminOutboundMessage(BaseModel):
  """Admin-composed outbound message to users (SMS, push, or both)."""

  CHANNEL_CHOICES = (
      ('sms', 'SMS'),
      ('push', 'Push notification'),
      ('both', 'SMS and push'),
  )

  AUDIENCE_CHOICES = (
      ('single', 'Single user'),
      ('role', 'All users with role'),
      ('selected', 'Selected users'),
  )

  TARGET_ROLE_CHOICES = (
      ('USER', 'Customer'),
      ('TAILOR', 'Tailor'),
      ('RIDER', 'Rider'),
  )

  STATUS_CHOICES = (
      ('draft', 'Draft'),
      ('queued', 'Queued'),
      ('processing', 'Processing'),
      ('completed', 'Completed'),
      ('failed', 'Failed'),
  )

  sent_by = models.ForeignKey(
      settings.AUTH_USER_MODEL,
      on_delete=models.SET_NULL,
      null=True,
      blank=True,
      related_name='admin_outbound_messages',
  )
  channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES, default='sms')
  audience_type = models.CharField(max_length=10, choices=AUDIENCE_CHOICES, default='single')
  target_user = models.ForeignKey(
      settings.AUTH_USER_MODEL,
      on_delete=models.SET_NULL,
      null=True,
      blank=True,
      related_name='admin_messages_received_target',
  )
  target_role = models.CharField(
      max_length=10,
      choices=TARGET_ROLE_CHOICES,
      blank=True,
      null=True,
  )
  recipients = models.ManyToManyField(
      settings.AUTH_USER_MODEL,
      blank=True,
      related_name='admin_outbound_message_batches',
  )
  title = models.CharField(
      max_length=255,
      blank=True,
      help_text='Required for push notifications',
  )
  body = models.TextField(help_text='Message text (SMS body and/or push body)')
  status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='draft', db_index=True)
  sent_at = models.DateTimeField(null=True, blank=True)
  total_recipients = models.PositiveIntegerField(default=0)
  sent_count = models.PositiveIntegerField(default=0)
  failed_count = models.PositiveIntegerField(default=0)
  error_summary = models.TextField(blank=True)

  class Meta:
    verbose_name = 'Admin message'
    verbose_name_plural = 'Messaging center'
    ordering = ['-created_at']
    permissions = [
        ('send_admin_message', 'Can send admin messages'),
    ]

  def __str__(self):
    return f"Admin message #{self.pk} ({self.get_channel_display()}) - {self.status}"


class AdminMessageDelivery(BaseModel):
  """Per-recipient delivery record for an admin outbound message."""

  DELIVERY_STATUS_CHOICES = (
      ('pending', 'Pending'),
      ('sent', 'Sent'),
      ('partial', 'Partially sent'),
      ('failed', 'Failed'),
      ('skipped', 'Skipped'),
  )

  CHANNEL_STATUS_CHOICES = (
      ('pending', 'Pending'),
      ('sent', 'Sent'),
      ('failed', 'Failed'),
      ('skipped', 'Skipped'),
  )

  message = models.ForeignKey(
      AdminOutboundMessage,
      on_delete=models.CASCADE,
      related_name='deliveries',
  )
  user = models.ForeignKey(
      settings.AUTH_USER_MODEL,
      on_delete=models.CASCADE,
      related_name='admin_message_deliveries',
  )
  phone_used = models.CharField(max_length=20, blank=True)
  sms_status = models.CharField(max_length=10, choices=CHANNEL_STATUS_CHOICES, default='pending')
  push_status = models.CharField(max_length=10, choices=CHANNEL_STATUS_CHOICES, default='pending')
  status = models.CharField(max_length=10, choices=DELIVERY_STATUS_CHOICES, default='pending', db_index=True)
  provider_message_id = models.CharField(max_length=100, blank=True)
  error_message = models.TextField(blank=True)
  sent_at = models.DateTimeField(null=True, blank=True)

  class Meta:
    verbose_name = 'Message delivery'
    verbose_name_plural = 'Message deliveries'
    ordering = ['-created_at']
    unique_together = [['message', 'user']]

  def __str__(self):
    return f"Delivery to {self.user_id} for message #{self.message_id} - {self.status}"
