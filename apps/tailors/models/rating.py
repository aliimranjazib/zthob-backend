# apps/tailors/models/rating.py
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.core.models import BaseModel


class TailorRating(BaseModel):
    """
    Customer rating for a tailor, scoped to a specific completed order.
    One rating per order (enforced via OneToOneField).
    
    Sub-ratings (each 1-5):
    - stitching_quality: How well was the garment stitched?
    - on_time_delivery: Was the order ready by the estimated date?
    - overall_satisfaction: General experience with the tailor
    """

    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='tailor_rating',
        help_text="The completed order this rating is for (one rating per order)"
    )
    tailor = models.ForeignKey(
        'TailorProfile',
        on_delete=models.CASCADE,
        related_name='ratings',
        help_text="The tailor being rated"
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tailor_ratings_given',
        help_text="The customer who submitted this rating"
    )

    stitching_quality = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Stitching quality rating (1-5)"
    )
    on_time_delivery = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="On-time delivery rating (1-5)"
    )
    overall_satisfaction = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Overall satisfaction rating (1-5)"
    )

    review = models.TextField(
        blank=True,
        null=True,
        help_text="Optional written review by the customer"
    )

    class Meta:
        verbose_name = "Tailor Rating"
        verbose_name_plural = "Tailor Ratings"
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"Rating for {self.tailor.shop_name or self.tailor.user.username} "
            f"by {self.customer.username} "
            f"(Order: {self.order.order_number})"
        )
