from django.urls import path
from .views import (
    RiderRegisterView,
    RiderSendOTPView,
    RiderVerifyOTPView,
    RiderProfileView,
    RiderProfileSubmissionView,
    RiderProfileStatusView,
    RiderDocumentUploadView,
    RiderDocumentListView,
    RiderDocumentDeleteView,
    RiderAvailableOrdersView,
    RiderMyOrdersView,
    RiderOrderDetailView,
    RiderAcceptOrderView,
    RiderAddMeasurementsView,
    RiderUpdateOrderStatusView,
    RiderAnalyticsView,
)
from .views_review import (
    RiderProfileReviewListView,
    RiderProfileReviewDetailView,
)

app_name = 'riders'

urlpatterns = [
    # Authentication
    path('register/', RiderRegisterView.as_view(), name='register'),
    path('send-otp/', RiderSendOTPView.as_view(), name='send-otp'),
    path('verify-otp/', RiderVerifyOTPView.as_view(), name='verify-otp'),
    
    # Profile
    path('profile/', RiderProfileView.as_view(), name='profile'),
    path('profile/submit/', RiderProfileSubmissionView.as_view(), name='profile-submit'),
    path('profile/status/', RiderProfileStatusView.as_view(), name='profile-status'),
    
    # Documents
    path('documents/', RiderDocumentListView.as_view(), name='documents-list'),
    path('documents/upload/', RiderDocumentUploadView.as_view(), name='document-upload'),
    path('documents/<int:document_id>/', RiderDocumentDeleteView.as_view(), name='document-delete'),
    
    # Orders
    path('orders/available/', RiderAvailableOrdersView.as_view(), name='available-orders'),
    path('orders/my-orders/', RiderMyOrdersView.as_view(), name='my-orders'),
    path('orders/<int:order_id>/', RiderOrderDetailView.as_view(), name='order-detail'),
    path('orders/<int:order_id>/accept/', RiderAcceptOrderView.as_view(), name='accept-order'),
    path('orders/<int:order_id>/measurements/', RiderAddMeasurementsView.as_view(), name='add-measurements'),
    path('orders/<int:order_id>/update-status/', RiderUpdateOrderStatusView.as_view(), name='update-status'),
    
    # Analytics
    path('analytics/', RiderAnalyticsView.as_view(), name='rider-analytics'),
    
    # Admin Review
    path('admin/reviews/', RiderProfileReviewListView.as_view(), name='admin-reviews'),
    path('admin/reviews/<int:pk>/', RiderProfileReviewDetailView.as_view(), name='admin-review-detail'),
]

