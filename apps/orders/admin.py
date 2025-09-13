from django.contrib import admin
from .models import Order

# Register your models here.
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id']
    # Note: The Order model is incomplete - only has choices defined but no actual fields
    # This admin is registered but will show minimal information until the model is completed
