"""
URL configuration for zthob project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.contrib import admin
from django.urls import path, include,re_path
from rest_framework import permissions
from django.conf.urls.static import static
from django.template.response import TemplateResponse

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

# Customize admin site
admin.site.site_header = "Mgask Administration"
admin.site.site_title = "Mgask Admin"
admin.site.index_title = "Welcome to Zthob Mgask"

# Override admin index to add image galleries
original_index = admin.site.index

def custom_admin_index(request, extra_context=None):
    """Enhanced admin index with image galleries and order statistics"""
    from apps.tailors.models import FabricImage, TailorProfile
    from apps.riders.models import RiderDocument
    from apps.orders.models import Order
    from apps.tailors.models import Fabric
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models import Count, Sum
    from decimal import Decimal
    
    extra_context = extra_context or {}
    
    # Get recent fabric images (primary images)
    recent_fabric_images = FabricImage.objects.filter(
        is_primary=True
    ).select_related('fabric').order_by('-created_at')[:12]
    
    # Get tailor shop images
    tailor_shop_images = TailorProfile.objects.filter(
        shop_image__isnull=False
    ).select_related('user').order_by('-created_at')[:12]
    
    # Get recent rider documents (verified)
    recent_rider_documents = RiderDocument.objects.filter(
        is_verified=True
    ).select_related('rider_profile__user').order_by('-verified_at')[:12]
    
    # Calculate date ranges for order statistics
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    yesterday_end = today_start
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)
    
    # Get order statistics
    today_orders = Order.objects.filter(created_at__gte=today_start)
    yesterday_orders = Order.objects.filter(created_at__gte=yesterday_start, created_at__lt=today_start)
    weekly_orders = Order.objects.filter(created_at__gte=week_start)
    monthly_orders = Order.objects.filter(created_at__gte=month_start)
    
    # Calculate order counts and revenue
    order_stats = {
        'today': {
            'count': today_orders.count(),
            'revenue': today_orders.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00'),
            'pending': today_orders.filter(status='pending').count(),
            'confirmed': today_orders.filter(status='confirmed').count(),
            'delivered': today_orders.filter(status='delivered').count(),
        },
        'yesterday': {
            'count': yesterday_orders.count(),
            'revenue': yesterday_orders.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00'),
            'pending': yesterday_orders.filter(status='pending').count(),
            'confirmed': yesterday_orders.filter(status='confirmed').count(),
            'delivered': yesterday_orders.filter(status='delivered').count(),
        },
        'weekly': {
            'count': weekly_orders.count(),
            'revenue': weekly_orders.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00'),
            'pending': weekly_orders.filter(status='pending').count(),
            'confirmed': weekly_orders.filter(status='confirmed').count(),
            'delivered': weekly_orders.filter(status='delivered').count(),
        },
        'monthly': {
            'count': monthly_orders.count(),
            'revenue': monthly_orders.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00'),
            'pending': monthly_orders.filter(status='pending').count(),
            'confirmed': monthly_orders.filter(status='confirmed').count(),
            'delivered': monthly_orders.filter(status='delivered').count(),
        },
    }
    
    # Get daily order counts for the last 7 days (for line chart)
    daily_orders_data = []
    daily_labels = []
    for i in range(6, -1, -1):  # Last 7 days including today
        date = today_start - timedelta(days=i)
        date_end = date + timedelta(days=1)
        count = Order.objects.filter(created_at__gte=date, created_at__lt=date_end).count()
        daily_orders_data.append(count)
        daily_labels.append(date.strftime('%b %d'))
    
    # Get statistics
    from apps.customers.models import CustomerProfile
    from apps.riders.models import RiderProfile
    from apps.tailors.models import TailorProfileReview
    
    stats = {
        'total_fabrics': Fabric.objects.count(),
        'total_fabric_images': FabricImage.objects.count(),
        'total_tailors': TailorProfile.objects.count(),
        'total_tailors_with_images': TailorProfile.objects.filter(shop_image__isnull=False).count(),
        'total_riders': RiderDocument.objects.values('rider_profile').distinct().count(),
        'total_verified_documents': RiderDocument.objects.filter(is_verified=True).count(),
        'total_orders': Order.objects.count(),
        'pending_orders': Order.objects.filter(status='pending').count(),
        'paid_orders': Order.objects.filter(payment_status='paid').count(),
        'total_customer_profiles': CustomerProfile.objects.count(),
        'total_rider_profiles': RiderProfile.objects.count(),
        'pending_tailor_reviews': TailorProfileReview.objects.filter(review_status='pending').count(),
    }
    
    # Prepare image data
    fabric_images_data = []
    for img in recent_fabric_images:
        try:
            if img.image:
                fabric_images_data.append({
                    'id': img.id,
                    'image_url': img.image.url,
                    'fabric_name': img.fabric.name if img.fabric else 'Unknown',
                    'fabric_sku': img.fabric.sku if img.fabric else None,
                    'fabric_url': f'/admin/tailors/fabric/{img.fabric.id}/change/' if img.fabric and img.fabric.id else None,
                })
        except (ValueError, AttributeError):
            continue
    
    tailor_images_data = []
    for profile in tailor_shop_images:
        try:
            if profile.shop_image:
                tailor_images_data.append({
                    'id': profile.id,
                    'image_url': profile.shop_image.url,
                    'shop_name': profile.shop_name or (profile.user.username if profile.user else 'Unknown'),
                    'tailor_url': f'/admin/tailors/tailorprofile/{profile.id}/change/',
                })
        except (ValueError, AttributeError):
            continue
    
    rider_documents_data = []
    for doc in recent_rider_documents:
        try:
            if doc.document_image:
                rider_name = 'Unknown'
                if doc.rider_profile:
                    rider_name = doc.rider_profile.full_name or (doc.rider_profile.user.username if hasattr(doc.rider_profile, 'user') and doc.rider_profile.user else 'Unknown')
                rider_documents_data.append({
                    'id': doc.id,
                    'image_url': doc.document_image.url,
                    'document_type': doc.get_document_type_display(),
                    'rider_name': rider_name,
                    'rider_url': f'/admin/riders/riderprofile/{doc.rider_profile.id}/change/' if doc.rider_profile and doc.rider_profile.id else None,
                })
        except (ValueError, AttributeError):
            continue
    
    extra_context.update({
        'fabric_images': fabric_images_data,
        'tailor_images': tailor_images_data,
        'rider_documents': rider_documents_data,
        'stats': stats,
        'order_stats': order_stats,
        'daily_orders_data': daily_orders_data,
        'daily_labels': daily_labels,
    })
    
    return original_index(request, extra_context)

# Override the index view
admin.site.index = custom_admin_index

urlpatterns = [
    path("admin/", admin.site.urls),
    path('api/accounts/',include('apps.accounts.urls')),
    path('api/tailors/',include('apps.tailors.urls')),
    path('api/customers/',include('apps.customers.urls')),
    path('api/orders/',include('apps.orders.urls')),
    path('api/riders/',include('apps.riders.urls')),
    path('api/notifications/',include('apps.notifications.urls')),
    path('api/deliveries/',include('apps.deliveries.urls')),
    path('api/customization/',include('apps.customization.urls')),
    path('api/measurements/', include('apps.measurements.urls')),  # Measurement templates
    
    # System Configuration
    path('api/config/', include('apps.core.urls')),
    
    # API documentation URLs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
