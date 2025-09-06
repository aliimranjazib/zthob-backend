from django.shortcuts import render
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from apps.customers.serializers import FabricCatalogSerializer
from apps.tailors.models import Fabric
from zthob.utils import api_response
# Create your views here.
class FabricCatalogView(APIView):
    @swagger_auto_schema(
        tags=['Customers'],
        responses={200: FabricCatalogSerializer}
    )
    def get(self,request):
        fabrics=Fabric.objects.all()
        serialzers=FabricCatalogSerializer(fabrics, many=True,context={"request": request})
        return api_response(success=True, message="Fabrics fetched successfully",
                            data=serialzers.data,
                            status_code=status.HTTP_200_OK)
        