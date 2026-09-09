from django.urls import path

from apps.accounts.views_v2 import (
    V2MeView,
    V2PhoneLoginView,
    V2PhoneVerifyView,
    V2ProfileView,
    V2SwitchShopView,
)

app_name = 'accounts_v2'

urlpatterns = [
    path('auth/phone-login/', V2PhoneLoginView.as_view(), name='v2-phone-login'),
    path('auth/phone-verify/', V2PhoneVerifyView.as_view(), name='v2-phone-verify'),
    path('me/', V2MeView.as_view(), name='v2-me'),
    path('profile/', V2ProfileView.as_view(), name='v2-profile'),
    path('session/switch-shop/', V2SwitchShopView.as_view(), name='v2-switch-shop'),
]
