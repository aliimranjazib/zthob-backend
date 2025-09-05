from django.dispatch import receiver
from django.conf import settings
from django.db.models.signals import post_save
from apps.tailors.models import TailorProfile



@receiver(post_save,sender=settings.AUTH_USER_MODEL)
def create_tailor_profile(sender,instance,created,**kwargs):
    if created and getattr(instance,'role','') == 'TAILOR':
        TailorProfile.objects.get_or_create(user=instance)
        