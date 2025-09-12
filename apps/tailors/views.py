from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from apps.tailors.models import FabricCategory, TailorProfile, Fabric
from apps.tailors.permissions import IsTailor
from apps.tailors.serializers import FabricCategorySerializer, TailorProfileSerializer, TailorProfileUpdateSerializer, FabricSerializer, FabricCreateSerializer
from zthob.utils import api_response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
# Create your views here.


class TailorFabricCategoryListCreateView(APIView):
    serializer_class = FabricCategorySerializer
    
    def get(self,request):
        queryset = FabricCategory.objects.filter(is_active=True).order_by("-created_at")
        data = FabricCategorySerializer(queryset, many=True).data
        return api_response(success=True, message="Fabric categories fetched", data=data, status_code=status.HTTP_200_OK)
    def post(self,request):
        serializer = FabricCategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(success=True, message="Fabric category created", data=serializer.data, status_code=status.HTTP_201_CREATED)
        return api_response(success=False, message="Validation failed", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)


class TailorFabricCategoryDetailView(APIView):
    serializer_class = FabricCategorySerializer
    def delete(self,request,pk):
        category = FabricCategory.objects.get(pk=pk)
        category.delete()
        return api_response(success=True, message="Fabric category deleted", data=None, status_code=status.HTTP_200_OK)
class TailorProfileView(APIView):
    serializer_class = TailorProfileSerializer

    permission_classes=[IsAuthenticated,IsTailor]
    def get(self,request):
        profile, _=TailorProfile.objects.get_or_create(user=request.user)
        data=TailorProfileSerializer(profile).data
        return api_response(success=True,message='Tailor profile fetched',
                            data=data, status_code=status.HTTP_200_OK)
    
    def put(self,request):
        profile, _ = TailorProfile.objects.get_or_create(user=request.user)
        serializer=TailorProfileUpdateSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return api_response(success=True, message="Tailor profile updated", data=serializer.data, status_code=status.HTTP_200_OK)
        return api_response(success=False, message="Validation failed", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)


class TailorFabricView(APIView):
    serializer_class = FabricSerializer
    
    permission_classes = [IsAuthenticated, IsTailor]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        queryset = Fabric.objects.filter(tailor__user=request.user).order_by("-created_at")
        data = FabricSerializer(queryset, many=True).data
        return api_response(success=True, message="Fabrics fetched", data=data, status_code=status.HTTP_200_OK)

    def post(self, request):
        serializer = FabricCreateSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            fabric = serializer.save()
            data = FabricSerializer(fabric).data
            return api_response(success=True, message="Fabric created", data=data, status_code=status.HTTP_201_CREATED)
        return api_response(success=False, message="Validation failed", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)