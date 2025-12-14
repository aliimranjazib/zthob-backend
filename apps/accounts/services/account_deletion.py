"""
Account Deletion Service
Handles complete account deletion for Google Play compliance
"""
import logging
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)
User = get_user_model()


class AccountDeletionService:
    """Service to handle account deletion and related data cleanup"""
    
    @staticmethod
    @transaction.atomic
    def delete_user_account(user):
        """
        Permanently delete user account and all associated data.
        
        This method handles:
        - User account (hard delete)
        - Customer profile (CASCADE)
        - Addresses (CASCADE)
        - Family members (CASCADE)
        - Fabric favorites (CASCADE)
        - Orders (CASCADE - all orders where user is customer)
        - FCM device tokens (CASCADE)
        - Notification logs (CASCADE)
        - Phone verifications (CASCADE)
        
        Note: Orders where user is tailor or rider are handled by SET_NULL,
        so they won't be deleted, but the user reference will be set to NULL.
        
        Args:
            user: CustomUser instance to delete
            
        Returns:
            dict: Result with success status and message
        """
        try:
            user_id = user.id
            username = user.username
            phone = user.phone
            email = user.email
            
            # Log deletion request
            logger.info(f"Starting account deletion for user ID: {user_id}, username: {username}, phone: {phone}")
            
            # Count related data before deletion (for logging)
            from apps.customers.models import CustomerProfile, Address, FamilyMember, FabricFavorite
            from apps.orders.models import Order
            from apps.notifications.models import FCMDeviceToken, NotificationLog
            from apps.core.models import PhoneVerification
            
            related_counts = {
                'customer_profile': CustomerProfile.objects.filter(user=user).count(),
                'addresses': Address.objects.filter(user=user).count(),
                'family_members': FamilyMember.objects.filter(user=user).count(),
                'fabric_favorites': FabricFavorite.objects.filter(user=user).count(),
                'customer_orders': Order.objects.filter(customer=user).count(),
                'fcm_tokens': FCMDeviceToken.objects.filter(user=user).count(),
                'notification_logs': NotificationLog.objects.filter(user=user).count(),
                'phone_verifications': PhoneVerification.objects.filter(user=user).count(),
            }
            
            logger.info(f"Related data counts before deletion: {related_counts}")
            
            # Delete the user (CASCADE will handle related models)
            # Note: Orders where user is tailor/rider will have those fields set to NULL
            user.delete()
            
            logger.info(
                f"Account deletion completed successfully for user ID: {user_id}, "
                f"username: {username}, phone: {phone}. "
                f"Deleted: {related_counts}"
            )
            
            return {
                'success': True,
                'message': 'Account and all associated data have been permanently deleted.',
                'deleted_data': related_counts
            }
            
        except Exception as e:
            logger.error(f"Error deleting account for user {user.id if user else 'unknown'}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'Failed to delete account: {str(e)}',
                'error': str(e)
            }
    
    @staticmethod
    def find_user_by_phone_or_email(identifier):
        """
        Find user by phone number only.
        
        Args:
            identifier: Phone number
            
        Returns:
            User instance or None
        """
        # Normalize phone number
        from apps.core.services import PhoneVerificationService
        
        # Try normalized phone first
        try:
            normalized_phone = PhoneVerificationService.normalize_phone_to_local(identifier)
            user = User.objects.filter(phone=normalized_phone).first()
            if user:
                return user
        except Exception:
            pass
        
        # Try phone as-is (in case normalization didn't work)
        user = User.objects.filter(phone=identifier).first()
        if user:
            return user
        
        return None
    
    @staticmethod
    def verify_user_identity(user, phone_number, otp_code):
        """
        Verify user identity using phone OTP.
        
        Args:
            user: User instance
            phone_number: Phone number to verify
            otp_code: OTP code to verify
            
        Returns:
            tuple: (is_valid: bool, message: str)
        """
        from apps.core.services import PhoneVerificationService
        
        # Verify OTP
        is_valid, message, verified_user = PhoneVerificationService.verify_otp_for_phone(
            phone_number=phone_number,
            otp_code=otp_code
        )
        
        if not is_valid:
            return False, message or "Invalid or expired OTP code"
        
        # Check if verified user matches the user we're trying to delete
        if verified_user.id != user.id:
            return False, "OTP verification failed - user mismatch"
        
        return True, "Identity verified successfully"

