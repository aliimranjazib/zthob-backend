from django.db import models

# Create your models here.
class Order(models.Model):
    ORDER_STATUS_CHOIRCES=(
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("measuring", "Measuring"),
        ("cutting", "Cutting"),
        ("stitching", "Stitching"),
        ("ready_for_delivery", "Ready for Delivery"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    )
    PAYMENT_STATUS_CHOICES = (
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("refunded", "Refunded"),
    )
    PAYMENT_METHOD_CHOICES = (
        ("cod", "Cash on Delivery"),
        ("credit_card", "Credit Card"),
        ("bank_transfer", "Bank Transfer"),
    )
    
    # customer=models.ForeignKey(Cus)