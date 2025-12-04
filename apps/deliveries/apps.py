from django.apps import AppConfig


class DeliveriesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.deliveries'
    verbose_name = 'Delivery Tracking'
    
    def ready(self):
        """Import signals when app is ready"""
        import apps.deliveries.signals  # noqa

