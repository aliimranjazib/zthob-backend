from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html

from .forms import AdminOutboundMessageForm
from .models import AdminMessageDelivery, AdminOutboundMessage
from .tasks import process_admin_message_task


class AdminMessageDeliveryInline(admin.TabularInline):
  model = AdminMessageDelivery
  extra = 0
  can_delete = False
  readonly_fields = [
    'user',
    'phone_used',
    'sms_status',
    'push_status',
    'status',
    'provider_message_id',
    'error_message',
    'sent_at',
  ]
  fields = readonly_fields

  def has_add_permission(self, request, obj=None):
    return False


@admin.register(AdminOutboundMessage)
class AdminOutboundMessageAdmin(admin.ModelAdmin):
  form = AdminOutboundMessageForm
  list_display = [
    'id',
    'channel_badge',
    'audience_display',
    'status_badge',
    'total_recipients',
    'sent_count',
    'failed_count',
    'sent_by',
    'created_at',
  ]
  list_filter = ['status', 'channel', 'audience_type', 'created_at']
  search_fields = ['body', 'title', 'sent_by__username']
  readonly_fields = [
    'status',
    'sent_by',
    'sent_at',
    'total_recipients',
    'sent_count',
    'failed_count',
    'error_summary',
    'created_at',
    'updated_at',
  ]
  filter_horizontal = ['recipients']
  inlines = [AdminMessageDeliveryInline]
  fieldsets = (
    ('Message', {
      'fields': ('channel', 'title', 'body'),
    }),
    ('Audience', {
      'fields': ('audience_type', 'target_user', 'target_role', 'recipients'),
      'description': (
        'Single user: pick one user. '
        'Role: sends to all active users with that role. '
        'Selected users: choose specific recipients (or use the Users list action).'
      ),
    }),
    ('Delivery status', {
      'fields': (
        'status',
        'sent_by',
        'sent_at',
        'total_recipients',
        'sent_count',
        'failed_count',
        'error_summary',
        'created_at',
        'updated_at',
      ),
    }),
  )

  def get_readonly_fields(self, request, obj=None):
    readonly = list(super().get_readonly_fields(request, obj))
    if obj and obj.status not in ('draft',):
      readonly.extend(['channel', 'audience_type', 'target_user', 'target_role', 'title', 'body'])
    return readonly

  def has_change_permission(self, request, obj=None):
    if obj and obj.status != 'draft':
      return False
    return super().has_change_permission(request, obj)

  def has_delete_permission(self, request, obj=None):
    if obj and obj.status not in ('draft', 'failed'):
      return False
    return super().has_delete_permission(request, obj)

  def save_model(self, request, obj, form, change):
    obj.sent_by = request.user
    obj.status = 'queued'
    super().save_model(request, obj, form, change)

  def save_related(self, request, form, formsets, change):
    super().save_related(request, form, formsets, change)
    process_admin_message_task.delay(form.instance.pk)
    self.message_user(
      request,
      f'Message queued for delivery to the selected audience.',
      messages.SUCCESS,
    )

  def get_urls(self):
    urls = super().get_urls()
    custom_urls = [
      path(
        'compose-selected/',
        self.admin_site.admin_view(self.compose_selected_view),
        name='messaging_adminoutboundmessage_compose_selected',
      ),
    ]
    return custom_urls + urls

  def compose_selected_view(self, request):
    recipient_ids = request.GET.get('recipients', '')
    ids = [value for value in recipient_ids.split(',') if value.isdigit()]
    if not ids:
      self.message_user(request, 'No users selected.', messages.ERROR)
      return HttpResponseRedirect(reverse('admin:accounts_customuser_changelist'))

    add_url = reverse('admin:messaging_adminoutboundmessage_add')
    return HttpResponseRedirect(f'{add_url}?audience_type=selected&recipients={",".join(ids)}')

  def get_changeform_initial_data(self, request):
    initial = super().get_changeform_initial_data(request)
    audience_type = request.GET.get('audience_type')
    if audience_type:
      initial['audience_type'] = audience_type
    recipient_ids = [int(value) for value in request.GET.get('recipients', '').split(',') if value.isdigit()]
    if recipient_ids:
      from django.contrib.auth import get_user_model
      initial['recipients'] = get_user_model().objects.filter(pk__in=recipient_ids)
    return initial

  def channel_badge(self, obj):
    colors = {'sms': '#17a2b8', 'push': '#6f42c1', 'both': '#28a745'}
    color = colors.get(obj.channel, '#6c757d')
    return format_html(
      '<span style="background-color:{}; color:white; padding:3px 8px; border-radius:4px;">{}</span>',
      color,
      obj.get_channel_display(),
    )
  channel_badge.short_description = 'Channel'

  def status_badge(self, obj):
    colors = {
      'draft': '#6c757d',
      'queued': '#ffc107',
      'processing': '#17a2b8',
      'completed': '#28a745',
      'failed': '#dc3545',
    }
    color = colors.get(obj.status, '#6c757d')
    return format_html(
      '<span style="background-color:{}; color:white; padding:3px 8px; border-radius:4px;">{}</span>',
      color,
      obj.get_status_display(),
    )
  status_badge.short_description = 'Status'

  def audience_display(self, obj):
    if obj.audience_type == 'single' and obj.target_user:
      return f'Single: {obj.target_user.username}'
    if obj.audience_type == 'role' and obj.target_role:
      return f'Role: {obj.get_target_role_display()}'
    if obj.audience_type == 'selected':
      return f'Selected ({obj.total_recipients or obj.recipients.count()})'
    return obj.get_audience_type_display()
  audience_display.short_description = 'Audience'

  def has_module_permission(self, request):
    return request.user.is_staff

  def has_view_permission(self, request, obj=None):
    return request.user.is_staff and (
      request.user.is_superuser or request.user.has_perm('messaging.send_admin_message')
    )

  def has_add_permission(self, request):
    return request.user.is_staff and (
      request.user.is_superuser or request.user.has_perm('messaging.send_admin_message')
    )


@admin.register(AdminMessageDelivery)
class AdminMessageDeliveryAdmin(admin.ModelAdmin):
  list_display = [
    'id',
    'message',
    'user',
    'status',
    'sms_status',
    'push_status',
    'phone_used',
    'sent_at',
  ]
  list_filter = ['status', 'sms_status', 'push_status']
  search_fields = ['user__username', 'phone_used', 'provider_message_id']
  readonly_fields = [
    'message',
    'user',
    'phone_used',
    'sms_status',
    'push_status',
    'status',
    'provider_message_id',
    'error_message',
    'sent_at',
    'created_at',
    'updated_at',
  ]

  def has_add_permission(self, request):
    return False

  def has_change_permission(self, request, obj=None):
    return False

  def has_module_permission(self, request):
    return request.user.is_staff

  def has_view_permission(self, request, obj=None):
    return request.user.is_staff
