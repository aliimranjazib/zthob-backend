import logging
from django.contrib.auth import get_user_model
from apps.customers.models import CustomerProfile
from apps.tailors.models import TailorProfile
from apps.riders.models import RiderProfile

logger = logging.getLogger(__name__)

class IdentityService:
    """Centralized service for managing user identities and profiles"""

    @staticmethod
    def ensure_profile(user, role):
        """
        Ensures that a user has the profile required for a specific role.
        Creates the profile if it doesn't exist.
        """
        created = False
        profile = None

        if role == 'USER' or role == 'CUSTOMER':
            profile, created = CustomerProfile.objects.get_or_create(user=user)
        elif role == 'TAILOR':
            profile, created = TailorProfile.objects.get_or_create(user=user)
        elif role == 'RIDER':
            profile, created = RiderProfile.objects.get_or_create(user=user)
        
        if created:
            logger.info(f"Created {role} profile for user {user.phone}")
            # Here you can add more initialization logic, like creating a wallet
            # or sending a welcome notification for that specific role.
            
        return profile, created

    @staticmethod
    def get_all_active_roles(user):
        """Returns a list of all roles the user has profiles for"""
        roles = []
        if hasattr(user, 'customer_profile'): roles.append('USER')
        if hasattr(user, 'tailor_profile'): roles.append('TAILOR')
        if hasattr(user, 'rider_profile'): roles.append('RIDER')
        if user.is_admin: roles.append('ADMIN')
        return roles
