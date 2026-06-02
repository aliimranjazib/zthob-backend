from django.contrib import admin, messages
from django.utils import timezone
from .models import (
    TailorWallet, WalletTransaction, PayoutRequest,
    RiderWallet, RiderWalletTransaction, RiderPayoutRequest,
)
from .services import WalletService

@admin.register(TailorWallet)
class TailorWalletAdmin(admin.ModelAdmin):
    list_display = ('tailor_shop_name', 'available_balance', 'pending_balance', 'total_earned', 'total_withdrawn')
    search_fields = ('tailor__username', 'tailor__tailor_profile__shop_name')
    readonly_fields = ('available_balance', 'pending_balance', 'total_earned', 'total_withdrawn')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('tailor', 'tailor__tailor_profile')

    @admin.display(description='Tailor / Shop Name')
    def tailor_shop_name(self, obj):
        if hasattr(obj.tailor, 'tailor_profile') and obj.tailor.tailor_profile.shop_name:
            return f"{obj.tailor.username} | {obj.tailor.tailor_profile.shop_name}"
        return obj.tailor.username

@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'tailor_shop_name', 'transaction_type', 'source', 'amount', 'order', 'created_at')
    list_filter = ('transaction_type', 'source', 'created_at')
    search_fields = ('wallet__tailor__username', 'wallet__tailor__tailor_profile__shop_name', 'order__order_number', 'description')
    readonly_fields = ('running_balance',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('wallet__tailor', 'wallet__tailor__tailor_profile', 'order')

    @admin.display(description='Tailor / Shop Name')
    def tailor_shop_name(self, obj):
        tailor = obj.wallet.tailor
        if hasattr(tailor, 'tailor_profile') and tailor.tailor_profile.shop_name:
            return f"{tailor.username} | {tailor.tailor_profile.shop_name}"
        return tailor.username

@admin.register(RiderWallet)
class RiderWalletAdmin(admin.ModelAdmin):
    list_display = ('rider_name', 'available_balance', 'pending_balance', 'total_earned', 'total_withdrawn')
    search_fields = ('rider__username', 'rider__rider_profile__full_name')
    readonly_fields = ('available_balance', 'pending_balance', 'total_earned', 'total_withdrawn')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('rider', 'rider__rider_profile')

    @admin.display(description='Rider')
    def rider_name(self, obj):
        if hasattr(obj.rider, 'rider_profile') and obj.rider.rider_profile.full_name:
            return f"{obj.rider.username} | {obj.rider.rider_profile.full_name}"
        return obj.rider.username

@admin.register(RiderWalletTransaction)
class RiderWalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'rider_name', 'transaction_type', 'source', 'amount', 'order', 'created_at')
    list_filter = ('transaction_type', 'source', 'created_at')
    search_fields = ('wallet__rider__username', 'wallet__rider__rider_profile__full_name', 'order__order_number', 'description')
    readonly_fields = ('running_balance',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('wallet__rider', 'wallet__rider__rider_profile', 'order')

    @admin.display(description='Rider')
    def rider_name(self, obj):
        rider = obj.wallet.rider
        if hasattr(rider, 'rider_profile') and rider.rider_profile.full_name:
            return f"{rider.username} | {rider.rider_profile.full_name}"
        return rider.username

@admin.register(PayoutRequest)
class PayoutRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'tailor_shop_name', 'amount', 'status', 'created_at', 'processed_at')
    list_filter = ('status', 'created_at')
    search_fields = ('tailor__username', 'tailor__tailor_profile__shop_name', 'payment_reference')
    actions = ['mark_as_paid']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('tailor', 'tailor__tailor_profile')

    @admin.display(description='Tailor / Shop Name')
    def tailor_shop_name(self, obj):
        if hasattr(obj.tailor, 'tailor_profile') and obj.tailor.tailor_profile.shop_name:
            return f"{obj.tailor.username} | {obj.tailor.tailor_profile.shop_name}"
        return obj.tailor.username

    @admin.action(description="Mark selected payout requests as PAID")
    def mark_as_paid(self, request, queryset):
        for payout in queryset:
            if payout.status != 'paid':
                WalletService.process_payout(
                    payout_request=payout,
                    admin_user=request.user,
                    reference_number="MANUAL-TRANS-ADMIN",
                    notes="Processed via admin bulk action"
                )
        self.message_user(request, "Selected payout requests marked as paid and wallets updated.", messages.SUCCESS)

@admin.register(RiderPayoutRequest)
class RiderPayoutRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'rider_name', 'amount', 'status', 'created_at', 'processed_at')
    list_filter = ('status', 'created_at')
    search_fields = ('rider__username', 'rider__rider_profile__full_name', 'payment_reference')
    actions = ['mark_as_paid']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('rider', 'rider__rider_profile')

    @admin.display(description='Rider')
    def rider_name(self, obj):
        if hasattr(obj.rider, 'rider_profile') and obj.rider.rider_profile.full_name:
            return f"{obj.rider.username} | {obj.rider.rider_profile.full_name}"
        return obj.rider.username

    @admin.action(description="Mark selected rider payout requests as PAID")
    def mark_as_paid(self, request, queryset):
        for payout in queryset:
            if payout.status != 'paid':
                WalletService.process_rider_payout(
                    payout_request=payout,
                    admin_user=request.user,
                    reference_number="MANUAL-TRANS-ADMIN",
                    notes="Processed via admin bulk action"
                )
        self.message_user(request, "Selected rider payout requests marked as paid and wallets updated.", messages.SUCCESS)
