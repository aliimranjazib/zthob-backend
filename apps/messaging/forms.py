from django import forms
from django.core.exceptions import ValidationError

from .models import AdminOutboundMessage


class AdminOutboundMessageForm(forms.ModelForm):
  class Meta:
    model = AdminOutboundMessage
    fields = [
      'channel',
      'audience_type',
      'target_user',
      'target_role',
      'recipients',
      'title',
      'body',
    ]
    widgets = {
      'body': forms.Textarea(attrs={'rows': 5}),
      'recipients': forms.SelectMultiple(attrs={'size': 12}),
    }

  def clean(self):
    cleaned = super().clean()
    audience_type = cleaned.get('audience_type')
    target_user = cleaned.get('target_user')
    target_role = cleaned.get('target_role')
    recipients = cleaned.get('recipients')
    channel = cleaned.get('channel')
    title = (cleaned.get('title') or '').strip()
    body = (cleaned.get('body') or '').strip()

    if not body:
      raise ValidationError({'body': 'Message body is required.'})

    if channel in ('push', 'both') and not title:
      raise ValidationError({'title': 'Title is required for push notifications.'})

    if audience_type == 'single' and not target_user:
      raise ValidationError({'target_user': 'Select a user for single-user messages.'})

    if audience_type == 'role' and not target_role:
      raise ValidationError({'target_role': 'Select a role for role-based messages.'})

    if audience_type == 'selected':
      selected = list(recipients) if recipients is not None else []
      if not selected:
        raise ValidationError({'recipients': 'Select at least one recipient.'})

    return cleaned
