from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from apps.tailors.models import FabricCategory, TailorProfile, Fabric
from apps.tailors.permissions import IsTailor
from drf_yasg.utils import swagger_auto_schema
from apps.tailors.serializers import FabricCategorySerializer, TailorProfileSerializer, TailorProfileUpdateSerializer, FabricSerializer, FabricCreateSerializer
from zthob.utils import api_response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from drf_yasg import openapi
# Create your views here.


class TailorFabricCategoryListCreateView(APIView):
    
    @swagger_auto_schema(
        tags=['Tailors'],
        responses={200: FabricCategorySerializer(many=True)}
    )
    def get(self,request):
        queryset = FabricCategory.objects.filter(is_active=True).order_by("-created_at")
        data = FabricCategorySerializer(queryset, many=True).data
        return api_response(success=True, message="Fabric categories fetched", data=data, status_code=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=['Tailors'],
        request_body=FabricCategorySerializer,
        responses={201: FabricCategorySerializer}
    )
    def post(self,request):
        serializer = FabricCategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(success=True, message="Fabric category created", data=serializer.data, status_code=status.HTTP_201_CREATED)
        return api_response(success=False, message="Validation failed", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)


class TailorFabricCategoryDetailView(APIView):
    
    @swagger_auto_schema(
        tags=['Tailors'],
        responses={200: 'Deleted'}
    )
    def delete(self,request,pk):
        category = FabricCategory.objects.get(pk=pk)
        category.delete()
        return api_response(success=True, message="Fabric category deleted", data=None, status_code=status.HTTP_200_OK)
class TailorProfileView(APIView):
    permission_classes=[IsAuthenticated,IsTailor]
    
    @swagger_auto_schema(
        tags=['Tailors'],
        responses={200: TailorProfileSerializer}
    )
    def get(self,request):
        profile, _=TailorProfile.objects.get_or_create(user=request.user)
        data=TailorProfileSerializer(profile).data
        return api_response(success=True,message='Tailor profile fetched',
                            data=data, status_code=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        tags=['Tailors'],
        request_body=TailorProfileUpdateSerializer,
        responses={200: TailorProfileSerializer}
    )
    def put(self,request):
        profile, _ = TailorProfile.objects.get_or_create(user=request.user)
        serializer=TailorProfileUpdateSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return api_response(success=True, message="Tailor profile updated", data=serializer.data, status_code=status.HTTP_200_OK)
        return api_response(success=False, message="Validation failed", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)


class TailorFabricView(APIView):
    permission_classes = [IsAuthenticated, IsTailor]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        tags=["Tailors"],
        responses={200: FabricSerializer(many=True)}
    )
    def get(self, request):
        queryset = Fabric.objects.filter(tailor__user=request.user).order_by("-created_at")
        data = FabricSerializer(queryset, many=True).data
        return api_response(success=True, message="Fabrics fetched", data=data, status_code=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["Tailors"],
        consumes=['multipart/form-data'],
        manual_parameters=[
            openapi.Parameter('name', openapi.IN_FORM, description='Fabric name', type=openapi.TYPE_STRING, required=True),
            openapi.Parameter('price', openapi.IN_FORM, description='Price', type=openapi.TYPE_NUMBER, required=True),
            openapi.Parameter('stock', openapi.IN_FORM, description='Stock quantity', type=openapi.TYPE_INTEGER, required=True),
            openapi.Parameter('category', openapi.IN_FORM, description='Category ID', type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter('description', openapi.IN_FORM, description='Description', type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('is_active', openapi.IN_FORM, description='Is active', type=openapi.TYPE_BOOLEAN, required=False),
            openapi.Parameter('images', openapi.IN_FORM, description='Upload 1-4 images (repeat this field)', type=openapi.TYPE_FILE, required=True),
        ],
        responses={201: FabricSerializer}
    )
    def post(self, request):
        serializer = FabricCreateSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            fabric = serializer.save()
            data = FabricSerializer(fabric).data
            return api_response(success=True, message="Fabric created", data=data, status_code=status.HTTP_201_CREATED)
        return api_response(success=False, message="Validation failed", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)