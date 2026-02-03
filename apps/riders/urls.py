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
from .views_tailor import (
    tailor_invitation_codes,
    deactivate_invitation_code,
    tailor_my_riders,
    remove_rider_from_team,
)
from .views_rider import (
    join_tailor_team,
    rider_my_tailors,
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
    
    # Tailor - Invitation Codes & Team Management
    path('tailor/invitation-codes/', tailor_invitation_codes, name='tailor-invitation-codes'),
    path('tailor/invitation-codes/<str:code>/', deactivate_invitation_code, name='deactivate-invitation-code'),
    path('tailor/my-riders/', tailor_my_riders, name='tailor-my-riders'),
    path('tailor/my-riders/<int:rider_id>/', remove_rider_from_team, name='remove-rider'),
    
    # Rider - Join Team & View Tailors
    path('join-team/', join_tailor_team, name='join-team'),
    path('my-tailors/', rider_my_tailors, name='my-tailors'),
]

