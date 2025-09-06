from django.urls import path

from apps.customers.views import FabricCatalogView

urlpatterns = [
    path('allfabrics/',FabricCatalogView.as_view(),name='all-fabrics')
]
