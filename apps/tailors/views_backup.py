from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated,AllowAny
from apps.tailors.permissions import IsTailor
from apps.tailors.serializers import (
    FabricCategorySerializer, FabricTagSerializer, FabricTypeSerializer, 
    TailorProfileSerializer, TailorProfileUpdateSerializer, 
    FabricSerializer, FabricCreateSerializer, FabricUpdateSerializer
)
from zthob.utils import api_response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from .models import (
    FabricCategory, 
    FabricImage, 
    FabricTag, 
    FabricType, 
    TailorProfile, 
    Fabric,
    TailorProfileReview
)
# Create your views here.

@extend_schema(
    description="Fabric type management operations",
    request=FabricTypeSerializer,
    responses={
        201: FabricTypeSerializer,  
        200: FabricTypeSerializer(many=True),
    },
    tags=["Fabric Types"]
)

class TailorFabricTypeListCreateView(generics.ListCreateAPIView):
    queryset=FabricType.objects.all()
    serializer_class=FabricTypeSerializer
    permission_classes=[AllowAny]
    
    @extend_schema(
        description="Get all available fabric types",
        responses={200: FabricTypeSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        description="Create a new fabric type",
        request=FabricTypeSerializer,
        responses={201: FabricTypeSerializer}
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
@extend_schema(
    tags=["Fabric Types"],
    description="Fabric type detail operations (get, update, delete)",
    request=FabricTypeSerializer,
    responses={
        200: FabricTypeSerializer,
        201: FabricTypeSerializer,
        204: {"description": "Fabric type deleted successfully"},
        404: {"description": "Fabric type not found"}
    }
)
class TailorFabricTypeRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset=FabricType.objects.all()
    serializer_class=FabricTypeSerializer
    permission_classes=[AllowAny]
    lookup_field = 'pk'
    
    @extend_schema(
        description="Get fabric type details by ID",
        responses={200: FabricTypeSerializer, 404: {"description": "Fabric type not found"}}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        description="Update fabric type completely",
        request=FabricTypeSerializer,
        responses={200: FabricTypeSerializer, 404: {"description": "Fabric type not found"}}
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)
    
    @extend_schema(
        description="Update fabric type partially",
        request=FabricTypeSerializer,
        responses={200: FabricTypeSerializer, 404: {"description": "Fabric type not found"}}
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)
    
    @extend_schema(
        description="Delete fabric type",
        responses={204: {"description": "Fabric type deleted successfully"}, 404: {"description": "Fabric type not found"}}
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)

@extend_schema(
    tags=["Fabric Categories"],
    description="Fabric category management operations"
)

class TailorFabricTagsListCreateView(generics.ListCreateAPIView):
    queryset=FabricTag.objects.all()
    serializer_class=FabricTagSerializer
    permission_classes=[AllowAny]
    
    @extend_schema(
        tags=["Fabric Tags"],
        description="Get all fabric tags",
        operation_id="fabric_tags_list",
        responses={200: FabricTagSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        tags=["Fabric Tags"],
        description="Create a new fabric tag",
        operation_id="fabric_tags_create",
        request=FabricTagSerializer,
        responses={201: FabricTagSerializer}
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class TailorFabricTagsRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset=FabricTag.objects.all()
    serializer_class=FabricTagSerializer
    permission_classes=[AllowAny]
    lookup_field = 'pk'
    
    @extend_schema(
        tags=["Fabric Tags"],
        description="Get fabric tag by ID",
        operation_id="fabric_tags_retrieve",
        responses={200: FabricTagSerializer, 404: {"description": "Fabric tag not found"}}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        tags=["Fabric Tags"],
        description="Update fabric tag completely",
        operation_id="fabric_tags_update",
        request=FabricTagSerializer,
        responses={200: FabricTagSerializer, 404: {"description": "Fabric tag not found"}}
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)
    
    @extend_schema(
        tags=["Fabric Tags"],
        description="Update fabric tag partially",
        operation_id="fabric_tags_partial_update",
        request=FabricTagSerializer,
        responses={200: FabricTagSerializer, 404: {"description": "Fabric tag not found"}}
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)
    
    @extend_schema(
        tags=["Fabric Tags"],
        description="Delete fabric tag",
        operation_id="fabric_tags_destroy",
        responses={204: {"description": "Fabric tag deleted successfully"}, 404: {"description": "Fabric tag not found"}}
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


@extend_schema(
    tags=["Fabric Categories"],
    description="Fabric category management operations"
)
class TailorFabricCategoryListCreateView(APIView):
    serializer_class = FabricCategorySerializer
    permission_classes=[AllowAny]
    
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


@extend_schema(
    tags=["Fabric Categories"],
    description="Fabric category detail operations"
)
class TailorFabricCategoryDetailView(APIView):
    serializer_class = FabricCategorySerializer
    permission_classes=[AllowAny]
    def delete(self,request,pk):
        category = FabricCategory.objects.get(pk=pk)
        category.delete()
        return api_response(success=True, message="Fabric category deleted", data=None, status_code=status.HTTP_200_OK)
@extend_schema(
    tags=["Tailor Profile"],
    description="Tailor profile management operations"
)
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


@extend_schema(
    tags=["Fabric Management"],
    description="Individual fabric operations (get, update, delete)"
)
class TailorFabricDetailView(APIView):
    """View for handling individual fabric operations (GET, PUT, PATCH, DELETE)."""
    
    permission_classes = [IsAuthenticated, IsTailor]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_object(self, pk, user):
        """Get fabric that belongs to the authenticated tailor."""
        try:
            return Fabric.objects.get(pk=pk, tailor__user=user)
        except Fabric.DoesNotExist:
            return None
    
    @extend_schema(
        responses={200: FabricSerializer, 404: {"description": "Fabric not found"}},
        description="Get single fabric details by ID"
    )
    def get(self, request, pk):
        """Get single fabric details."""
        fabric = self.get_object(pk, request.user)
        if not fabric:
            return api_response(
                success=False, 
                message="Fabric not found", 
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        serializer = FabricSerializer(fabric, context={'request': request})
        return api_response(
            success=True, 
            message="Fabric details fetched", 
            data=serializer.data, 
            status_code=status.HTTP_200_OK
        )
    
    @extend_schema(
        request=FabricUpdateSerializer,
        responses={200: FabricSerializer, 400: {"description": "Validation failed"}, 404: {"description": "Fabric not found"}},
        description="Update fabric completely (all fields required)"
    )
    def put(self, request, pk):
        """Update fabric (full update)."""
        fabric = self.get_object(pk, request.user)
        if not fabric:
            return api_response(
                success=False, 
                message="Fabric not found", 
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        serializer = FabricUpdateSerializer(fabric, data=request.data, partial=False)
        if serializer.is_valid():
            updated_fabric = serializer.save()
            response_serializer = FabricSerializer(updated_fabric, context={'request': request})
            return api_response(
                success=True, 
                message="Fabric updated successfully", 
                data=response_serializer.data, 
                status_code=status.HTTP_200_OK
            )
        
        return api_response(
            success=False, 
            message="Validation failed", 
            errors=serializer.errors, 
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    @extend_schema(
        request=FabricUpdateSerializer,
        responses={200: FabricSerializer, 400: {"description": "Validation failed"}, 404: {"description": "Fabric not found"}},
        description="Update fabric partially (only provided fields)"
    )
    def patch(self, request, pk):
        """Update fabric (partial update)."""
        fabric = self.get_object(pk, request.user)
        if not fabric:
            return api_response(
                success=False, 
                message="Fabric not found", 
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        serializer = FabricUpdateSerializer(fabric, data=request.data, partial=True)
        if serializer.is_valid():
            updated_fabric = serializer.save()
            response_serializer = FabricSerializer(updated_fabric, context={'request': request})
            return api_response(
                success=True, 
                message="Fabric updated successfully", 
                data=response_serializer.data, 
                status_code=status.HTTP_200_OK
            )
        
        return api_response(
            success=False, 
            message="Validation failed", 
            errors=serializer.errors, 
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    @extend_schema(
        responses={200: {"description": "Fabric deleted successfully"}, 404: {"description": "Fabric not found"}},
        description="Delete fabric permanently"
    )
    def delete(self, request, pk):
        """Delete fabric."""
        fabric = self.get_object(pk, request.user)
        if not fabric:
            return api_response(
                success=False, 
                message="Fabric not found", 
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        fabric_name = fabric.name
        fabric.delete()
        return api_response(
            success=True, 
            message=f"Fabric '{fabric_name}' deleted successfully", 
            status_code=status.HTTP_200_OK
        )


@extend_schema(
    tags=["Fabric Images"],
    description="Fabric image management operations"
)
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


@extend_schema(
    tags=["Fabric Management"],
    description="Fabric list and creation operations"
)
class TailorFabricView(APIView):
    serializer_class = FabricSerializer
    
    permission_classes = [IsAuthenticated, IsTailor]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        responses={200: FabricSerializer(many=True)},
        description="Get all fabrics for the authenticated tailor"
    )
    def get(self, request):
        queryset = Fabric.objects.filter(tailor__user=request.user).order_by("-created_at")
        data = FabricSerializer(queryset, many=True, context={'request': request}).data
        return api_response(success=True, message="Fabrics fetched", data=data, status_code=status.HTTP_200_OK)

    @extend_schema(
        request=FabricCreateSerializer,
        responses={201: FabricSerializer},
        description="Create a new fabric with multiple images and metadata"
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


@extend_schema(
    tags=["Fabric Images"],
    description="Fabric image deletion operations"
)
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