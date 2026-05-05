from django.contrib import admin, messages
from django.utils import timezone
from .models import TailorWallet, WalletTransaction, PayoutRequest
from .services import WalletService

@admin.register(TailorWallet)
class TailorWalletAdmin(admin.ModelAdmin):
    list_display = ('tailor', 'available_balance', 'pending_balance', 'total_earned', 'total_withdrawn')
    search_fields = ('tailor__username', 'tailor__first_name', 'tailor__last_name')
    readonly_fields = ('available_balance', 'pending_balance', 'total_earned', 'total_withdrawn')

@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'wallet', 'transaction_type', 'source', 'amount', 'order', 'created_at')
    list_filter = ('transaction_type', 'source', 'created_at')
    search_fields = ('wallet__tailor__username', 'order__order_number', 'description')
    readonly_fields = ('running_balance',)

@admin.register(PayoutRequest)
class PayoutRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'tailor', 'amount', 'status', 'created_at', 'processed_at')
    list_filter = ('status', 'created_at')
    search_fields = ('tailor__username', 'payment_reference')
    actions = ['mark_as_paid']

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
