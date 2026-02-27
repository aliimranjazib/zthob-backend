from django.dispatch import receiver
from django.conf import settings
from django.db.models.signals import post_save, post_delete
from django.db.models import Avg, Count
from apps.tailors.models import TailorProfile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_tailor_profile(sender, instance, created, **kwargs):
    if created and getattr(instance, 'role', '') == 'TAILOR':
        TailorProfile.objects.get_or_create(user=instance)


def _update_tailor_rating_aggregates(tailor_profile):
    """Recalculate and cache rating aggregates on TailorProfile."""
    # Import here to avoid circular imports at module load time
    from apps.tailors.models.rating import TailorRating
    agg = TailorRating.objects.filter(tailor=tailor_profile).aggregate(
        avg_s=Avg('stitching_quality'),
        avg_d=Avg('on_time_delivery'),
        avg_o=Avg('overall_satisfaction'),
        count=Count('id'),
    )
    tailor_profile.avg_stitching_quality = agg['avg_s'] or 0
    tailor_profile.avg_on_time_delivery = agg['avg_d'] or 0
    tailor_profile.avg_overall_satisfaction = agg['avg_o'] or 0
    tailor_profile.rating_count = agg['count'] or 0
    tailor_profile.save(update_fields=[
        'avg_stitching_quality',
        'avg_on_time_delivery',
        'avg_overall_satisfaction',
        'rating_count',
    ])


@receiver(post_save, sender='tailors.TailorRating')
def on_rating_saved(sender, instance, **kwargs):
    """Update tailor aggregates when a rating is created or updated."""
    _update_tailor_rating_aggregates(instance.tailor)


@receiver(post_delete, sender='tailors.TailorRating')
def on_rating_deleted(sender, instance, **kwargs):
    """Update tailor aggregates when a rating is deleted."""
    _update_tailor_rating_aggregates(instance.tailor)