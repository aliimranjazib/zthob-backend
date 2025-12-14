from django.urls import path

from apps.accounts.views import (
    UserRegistrationView,
    UserLoginView,
    UserProfileView,
    ChangePasswordView,
    UserLogoutView,
    PhoneLoginView,
    PhoneVerifyView,
    PhoneResendOTPView,
    DeleteAccountView,
    PublicDeleteAccountRequestView,
    PublicDeleteAccountSendOTPView,
    test_deployment)

app_name = 'accounts'
urlpatterns = [
    path('register/',UserRegistrationView.as_view(),name='user-register'),
    path('login/',UserLoginView.as_view(),name='user-login'),
    path('logout/',UserLogoutView.as_view(),name='user-logout'),
    path('profile/',UserProfileView.as_view(),name='user-profile'),
    path('change-password/',ChangePasswordView.as_view(),name='change-password'),
    path('delete-account/',DeleteAccountView.as_view(),name='delete-account'),
    path('phone-login/',PhoneLoginView.as_view(),name='phone-login'),
    path('phone-verify/',PhoneVerifyView.as_view(),name='phone-verify'),
    path('phone-resend-otp/',PhoneResendOTPView.as_view(),name='phone-resend-otp'),
    path('test-deployment/', test_deployment, name='test-deployment'),
    
    # Public account deletion endpoints (Google Play compliance)
    path('delete-account-request/', PublicDeleteAccountRequestView.as_view(), name='delete-account-request'),
    path('delete-account-send-otp/', PublicDeleteAccountSendOTPView.as_view(), name='delete-account-send-otp'),
]
