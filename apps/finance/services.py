from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from .models import TailorWallet, WalletTransaction, PayoutRequest

class WalletService:
    """
    Industry-level service to handle all wallet operations.
    Ensures atomicity and data consistency.
    """

    @staticmethod
    def get_or_create_wallet(tailor):
        """Ensures a tailor has a wallet initialized."""
        wallet, created = TailorWallet.objects.get_or_create(tailor=tailor)
        return wallet

    @classmethod
    @transaction.atomic
    def process_order_earning(cls, order):
        """
        Calculates and credits earning to tailor's wallet when order is completed.
        Formula: (Fabric + Stitching + Express) - System Fee
        """
        if not order.tailor:
            return None
        
        # Avoid duplicate credits for the same order
        if WalletTransaction.objects.filter(order=order, transaction_type='credit').exists():
            return None

        # Calculate Earning
        # Note: We use subtotal (fabric), stitching_price, and express_fee
        fabric_price = order.subtotal
        stitching_price = order.stitching_price
        express_fee = order.express_fee
        system_fee = order.system_fee

        net_earning = (fabric_price + stitching_price + express_fee) - system_fee

        wallet = cls.get_or_create_wallet(order.tailor)

        # Create Transaction Entry (The Ledger)
        transaction_entry = WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type='credit',
            source='order',
            amount=net_earning,
            order=order,
            description=f"Earnings for Order {order.order_number} (Fabric: {fabric_price}, Stitching: {stitching_price}, Express: {express_fee}, Fee: -{system_fee})",
            running_balance=wallet.available_balance + net_earning
        )

        # Update Wallet Balances
        wallet.available_balance += net_earning
        wallet.total_earned += net_earning
        wallet.save()

        return transaction_entry

    @classmethod
    @transaction.atomic
    def process_payout(cls, payout_request, admin_user, reference_number, notes=""):
        """
        Processes a payout request, marking it as paid and deducting from wallet.
        """
        if payout_request.status == 'paid':
            return None

        wallet = cls.get_or_create_wallet(payout_request.tailor)

        # Create Debit Transaction
        transaction_entry = WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type='debit',
            source='payout',
            amount=payout_request.amount,
            payout_request=payout_request,
            description=f"Payout processed. Ref: {reference_number}",
            running_balance=wallet.available_balance - payout_request.amount
        )

        # Update Wallet
        wallet.available_balance -= payout_request.amount
        wallet.total_withdrawn += payout_request.amount
        wallet.save()

        # Update Payout Request
        payout_request.status = 'paid'
        payout_request.payment_reference = reference_number
        payout_request.admin_notes = notes
        payout_request.processed_at = timezone.now()
        payout_request.processed_by = admin_user
        payout_request.save()

        return transaction_entry
