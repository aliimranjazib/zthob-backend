from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Slider

# Cache keys
SLIDER_LIST_CACHE_KEY = 'slider_list_cache'

@receiver([post_save, post_delete], sender=Slider)
def clear_slider_cache(sender, instance, **kwargs):
    """
    Clear the slider list cache whenever a Slider is created, updated, or deleted.
    """
    cache.delete(SLIDER_LIST_CACHE_KEY)
