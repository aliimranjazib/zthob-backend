from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from apps.tailors.models import FabricCategory, FabricImage, TailorProfile, Fabric
from apps.tailors.permissions import IsTailor
from apps.tailors.serializers import FabricCategorySerializer, TailorProfileSerializer, TailorProfileUpdateSerializer, FabricSerializer, FabricCreateSerializer
from zthob.utils import api_response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema
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


class FabricImagePrimaryView(APIView):
    """
    View to set an image as the primary image for a fabric
    """
    permission_classes = [IsAuthenticated, IsTailor]
    
    @extend_schema(
        description="Set an existing image as the primary image for a fabric",
        responses={
            200: FabricSerializer,
            404: {"description": "Image not found or doesn't belong to your fabrics"},
            403: {"description": "You don't have permission to modify this image"}
        }
    )
    def post(self, request, image_id):
        # Find the image
        try:
            image = FabricImage.objects.select_related('fabric', 'fabric__tailor').get(pk=image_id)
        except FabricImage.DoesNotExist:
            return api_response(success=False, message="Image not found", status_code=status.HTTP_404_NOT_FOUND)
        
        # Check permissions (only the tailor who owns the fabric can set a primary image)
        if image.fabric.tailor.user != request.user:
            return api_response(success=False, message="You don't have permission to modify this image",
                              status_code=status.HTTP_403_FORBIDDEN)
        
        # Set as primary
        image.is_primary = True
        image.save()  # This will unset any other primary images due to the save method override
        
        # Return the updated fabric
        fabric_serializer = FabricSerializer(image.fabric, context={'request': request})
        return api_response(success=True, message="Image set as primary", data=fabric_serializer.data,
                          status_code=status.HTTP_200_OK)


class TailorFabricView(APIView):
    serializer_class = FabricSerializer
    
    permission_classes = [IsAuthenticated, IsTailor]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        queryset = Fabric.objects.filter(tailor__user=request.user).order_by("-created_at")
        data = FabricSerializer(queryset, many=True, context={'request': request}).data
        return api_response(success=True, message="Fabrics fetched", data=data, status_code=status.HTTP_200_OK)

    @extend_schema(
        request=FabricCreateSerializer,
        responses={201: FabricSerializer},
        description="""
        Create a new fabric with multiple images and metadata.
        
        **Request Format:**
        ```json
        {
          "name": "Cotton Fabric",
          "description": "High-quality cotton",
          "price": 15.99,
          "stock": 100,
          "category": 1,
          "images": [
            {
              "image": [file1],
              "is_primary": true,
              "order": 0
            },
            {
              "image": [file2],
              "is_primary": false,
              "order": 1
            }
          ]
        }
        ```
        
        **Notes:**
        - At least one image is required, maximum 4 images allowed
        - Only one image can be marked as primary (if none is marked, the first one will be set as primary)
        - Each image must be jpg, jpeg, or png format and less than 5MB
        - The 'order' field determines the display order (0 is first)
        """
    )
    def post(self, request):
        # Process the form data to create the expected structure
        processed_data = request.POST.copy()
        processed_data.update(request.FILES)
        
        # Extract images and create the proper structure
        images_data = []
        i = 0
        while True:
            image_key = f'images[{i}][image]'
            is_primary_key = f'images[{i}][is_primary]'
            order_key = f'images[{i}][order]'
            
            if image_key in request.FILES:
                image_data = {
                    'image': request.FILES[image_key],
                    'is_primary': request.POST.get(is_primary_key, 'false').lower() == 'true',
                    'order': int(request.POST.get(order_key, '0'))
                }
                images_data.append(image_data)
                i += 1
            else:
                break
        
        # Add the processed images to the data (convert to regular dict to avoid QueryDict issues)
        processed_data = dict(processed_data)
        
        # Extract single values from lists for other fields
        for key, value in processed_data.items():
            if isinstance(value, list) and len(value) == 1 and key != 'images':
                processed_data[key] = value[0]
        
        processed_data['images'] = images_data
        
        serializer = FabricCreateSerializer(data=processed_data, context={"request": request})
        if serializer.is_valid():
            fabric = serializer.save()
            data = FabricSerializer(fabric, context={'request': request}).data
            return api_response(success=True, message="Fabric created", data=data, status_code=status.HTTP_201_CREATED)
        
        return api_response(success=False, message="Validation failed", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)


class FabricImageDeleteView(APIView):
    """
    View to delete an individual fabric image
    """
    permission_classes = [IsAuthenticated, IsTailor]
    
    @extend_schema(
        description="Delete a fabric image. If it's the primary image, the first remaining image will become primary.",
        responses={
            200: {"description": "Image deleted successfully"},
            404: {"description": "Image not found or doesn't belong to your fabrics"},
            403: {"description": "You don't have permission to delete this image"},
            400: {"description": "Cannot delete the last image of a fabric"}
        }
    )
    def delete(self, request, image_id):
        # Find the image
        try:
            image = FabricImage.objects.select_related('fabric', 'fabric__tailor').get(pk=image_id)
        except FabricImage.DoesNotExist:
            return api_response(success=False, message="Image not found", status_code=status.HTTP_404_NOT_FOUND)
        
        # Check permissions (only the tailor who owns the fabric can delete the image)
        if image.fabric.tailor.user != request.user:
            return api_response(success=False, message="You don't have permission to delete this image",
                              status_code=status.HTTP_403_FORBIDDEN)
        
        # Check if this is the last image
        total_images = image.fabric.gallery.count()
        if total_images <= 1:
            return api_response(success=False, message="Cannot delete the last image of a fabric",
                              status_code=status.HTTP_400_BAD_REQUEST)
        
        # If this is the primary image, set another image as primary
        if image.is_primary:
            remaining_images = image.fabric.gallery.exclude(pk=image_id)
            if remaining_images.exists():
                new_primary = remaining_images.first()
                new_primary.is_primary = True
                new_primary.save()
        
        # Delete the image
        image.delete()
        
        # Return the updated fabric
        fabric_serializer = FabricSerializer(image.fabric, context={'request': request})
        return api_response(success=True, message="Image deleted successfully", data=fabric_serializer.data,
                          status_code=status.HTTP_200_OK)