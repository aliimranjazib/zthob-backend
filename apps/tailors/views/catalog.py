# apps/tailors/views/catalog.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import generics
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema
from zthob.utils import api_response
from rest_framework import status

from ..models import (
    FabricCategory, FabricImage, FabricTag, 
    FabricType, Fabric
)
from ..serializers import (
    FabricCategorySerializer, FabricTagSerializer, FabricTypeSerializer,
    FabricSerializer, FabricCreateSerializer, FabricUpdateSerializer
)
from ..permissions import IsTailor
from .base import BaseTailorAuthenticatedView

# Fabric Type Views
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
    queryset = FabricType.objects.all()
    serializer_class = FabricTypeSerializer
    permission_classes = [AllowAny]
    
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
    queryset = FabricType.objects.all()
    serializer_class = FabricTypeSerializer
    permission_classes = [AllowAny]
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

# Fabric Tag Views
@extend_schema(
    tags=["Fabric Tags"],
    description="Fabric tag management operations"
)
class TailorFabricTagsListCreateView(generics.ListCreateAPIView):
    queryset = FabricTag.objects.all()
    serializer_class = FabricTagSerializer
    permission_classes = [AllowAny]
    
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
    queryset = FabricTag.objects.all()
    serializer_class = FabricTagSerializer
    permission_classes = [AllowAny]
    lookup_field = 'pk'
    
    @extend_schema(
        tags=["Fabric Tags"],
        description="Get fabric tag details by ID",
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

# Fabric Category Views
@extend_schema(
    tags=["Fabric Categories"],
    description="Fabric category management operations"
)
class TailorFabricCategoryListCreateView(APIView):
    serializer_class = FabricCategorySerializer
    permission_classes = [AllowAny]
    
    def get(self, request):
        queryset = FabricCategory.objects.filter(is_active=True).order_by("-created_at")
        data = FabricCategorySerializer(queryset, many=True).data
        return api_response(
            success=True, 
            message="Fabric categories fetched", 
            data=data, 
            status_code=status.HTTP_200_OK
        )
    
    def post(self, request):
        serializer = FabricCategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                success=True, 
                message="Fabric category created", 
                data=serializer.data, 
                status_code=status.HTTP_201_CREATED
            )
        return api_response(
            success=False, 
            message="Validation failed", 
            errors=serializer.errors, 
            status_code=status.HTTP_400_BAD_REQUEST
        )

@extend_schema(
    tags=["Fabric Categories"],
    description="Fabric category detail operations"
)
class TailorFabricCategoryDetailView(APIView):
    serializer_class = FabricCategorySerializer
    permission_classes = [AllowAny]
    
    def delete(self, request, pk):
        category = FabricCategory.objects.get(pk=pk)
        category.delete()
        return api_response(
            success=True, 
            message="Fabric category deleted", 
            data=None, 
            status_code=status.HTTP_200_OK
        )

# Fabric Views
@extend_schema(
    tags=["Fabric Management"],
    description="Fabric list and creation operations"
)
class TailorFabricView(BaseTailorAuthenticatedView):
    serializer_class = FabricSerializer
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        responses={200: FabricSerializer(many=True)},
        description="Get all fabrics for the authenticated tailor"
    )
    def get(self, request):
        queryset = Fabric.objects.filter(tailor__user=request.user).order_by("-created_at")
        data = FabricSerializer(queryset, many=True, context={'request': request}).data
        return api_response(
            success=True, 
            message="Fabrics fetched", 
            data=data, 
            status_code=status.HTTP_200_OK
        )

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
            if isinstance(value, list) and len(value) == 1 and key not in ['images', 'tags']:
                processed_data[key] = value[0]
        
        processed_data['images'] = images_data
        
        # Handle tags data
        if 'tags' in processed_data:
            # Convert tags to list of integers if it's a string
            tags_data = processed_data['tags']
            if isinstance(tags_data, str):
                # Handle comma-separated string or single value
                if ',' in tags_data:
                    tags_data = [int(tag.strip()) for tag in tags_data.split(',') if tag.strip()]
                else:
                    tags_data = [int(tags_data)] if tags_data else []
            elif isinstance(tags_data, list):
                # Convert string values to integers
                tags_data = [int(tag) for tag in tags_data if str(tag).strip()]
            processed_data['tags'] = tags_data
        
        serializer = FabricCreateSerializer(data=processed_data, context={"request": request})
        if serializer.is_valid():
            fabric = serializer.save()
            data = FabricSerializer(fabric, context={'request': request}).data
            return api_response(
                success=True, 
                message="Fabric created", 
                data=data, 
                status_code=status.HTTP_201_CREATED
            )
        
        return api_response(
            success=False, 
            message="Validation failed", 
            errors=serializer.errors, 
            status_code=status.HTTP_400_BAD_REQUEST
        )

@extend_schema(
    tags=["Fabric Management"],
    description="Individual fabric operations (get, update, delete)"
)
class TailorFabricDetailView(BaseTailorAuthenticatedView):
    """View for handling individual fabric operations (GET, PUT, PATCH, DELETE)."""
    
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

# Fabric Image Views
@extend_schema(
    tags=["Fabric Images"],
    description="Fabric image management operations"
)
class FabricImagePrimaryView(BaseTailorAuthenticatedView):
    """
    View to set an image as the primary image for a fabric
    """
    
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
            return api_response(
                success=False, 
                message="Image not found", 
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Check permissions (only the tailor who owns the fabric can modify the image)
        if image.fabric.tailor.user != request.user:
            return api_response(
                success=False, 
                message="You don't have permission to modify this image",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Set this image as primary (this will automatically unset others due to the save method)
        image.is_primary = True
        image.save()
        
        # Return the updated fabric
        fabric_serializer = FabricSerializer(image.fabric, context={'request': request})
        return api_response(
            success=True, 
            message="Primary image updated successfully", 
            data=fabric_serializer.data,
            status_code=status.HTTP_200_OK
        )

@extend_schema(
    tags=["Fabric Images"],
    description="Fabric image deletion operations"
)
class FabricImageDeleteView(BaseTailorAuthenticatedView):
    """
    View to delete an individual fabric image
    """
    
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
            return api_response(
                success=False, 
                message="Image not found", 
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Check permissions (only the tailor who owns the fabric can delete the image)
        if image.fabric.tailor.user != request.user:
            return api_response(
                success=False, 
                message="You don't have permission to delete this image",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Check if this is the last image
        total_images = image.fabric.gallery.count()
        if total_images <= 1:
            return api_response(
                success=False, 
                message="Cannot delete the last image of a fabric",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Store fabric reference before deletion
        fabric = image.fabric
        
        # If this is the primary image, set another image as primary
        if image.is_primary:
            remaining_images = fabric.gallery.exclude(pk=image_id)
            if remaining_images.exists():
                new_primary = remaining_images.first()
                new_primary.is_primary = True
                new_primary.save()
        
        # Delete the image
        image.delete()
        
        # Refresh fabric from database to get updated gallery
        fabric.refresh_from_db()
        
        # Return the updated fabric
        fabric_serializer = FabricSerializer(fabric, context={'request': request})
        return api_response(
            success=True, 
            message="Image deleted successfully", 
            data=fabric_serializer.data,
            status_code=status.HTTP_200_OK
        )

@extend_schema(
    tags=["Fabric Images"],
    description="Add new images to an existing fabric"
)
class FabricImageAddView(BaseTailorAuthenticatedView):
    """
    View to add new images to an existing fabric
    """
    parser_classes = [MultiPartParser, FormParser]
    
    @extend_schema(
        description="Add one or more images to an existing fabric. Maximum 4 images total per fabric.",
        responses={
            200: FabricSerializer,
            400: {"description": "Validation failed - maximum images exceeded or invalid data"},
            404: {"description": "Fabric not found"},
            403: {"description": "You don't have permission to modify this fabric"}
        }
    )
    def post(self, request, fabric_id):
        # Get the fabric
        try:
            fabric = Fabric.objects.select_related('tailor').get(pk=fabric_id)
        except Fabric.DoesNotExist:
            return api_response(
                success=False,
                message="Fabric not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Check permissions
        if fabric.tailor.user != request.user:
            return api_response(
                success=False,
                message="You don't have permission to modify this fabric",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Check current image count
        current_image_count = fabric.gallery.count()
        
        # Extract images from request
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
                    'order': int(request.POST.get(order_key, str(current_image_count + i)))
                }
                images_data.append(image_data)
                i += 1
            else:
                break
        
        if not images_data:
            return api_response(
                success=False,
                message="No images provided",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Check total image count limit (max 4 images)
        total_images_after_add = current_image_count + len(images_data)
        if total_images_after_add > 4:
            return api_response(
                success=False,
                message=f"Maximum 4 images allowed per fabric. Currently have {current_image_count}, trying to add {len(images_data)}",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate images
        for img_data in images_data:
            image = img_data['image']
            # Check file size (5MB limit)
            if image.size > 5 * 1024 * 1024:
                return api_response(
                    success=False,
                    message=f"Image size exceeds 5MB limit: {image.name}",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            # Check file format
            allowed_extensions = ['jpg', 'jpeg', 'png']
            file_extension = image.name.split('.')[-1].lower()
            if file_extension not in allowed_extensions:
                return api_response(
                    success=False,
                    message=f"Invalid file format for {image.name}. Only JPG, JPEG, and PNG files are allowed.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        
        # Check if any image is marked as primary
        primary_images = [img for img in images_data if img.get('is_primary', False)]
        if len(primary_images) > 1:
            return api_response(
                success=False,
                message="Only one image can be marked as primary",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # If marking one as primary, unset existing primary
        if primary_images:
            fabric.gallery.filter(is_primary=True).update(is_primary=False)
        
        # Create new images
        for img_data in images_data:
            FabricImage.objects.create(
                fabric=fabric,
                image=img_data['image'],
                is_primary=img_data.get('is_primary', False),
                order=img_data.get('order', current_image_count),
            )
        
        # Refresh fabric to get updated gallery
        fabric.refresh_from_db()
        
        # Return the updated fabric
        fabric_serializer = FabricSerializer(fabric, context={'request': request})
        return api_response(
            success=True,
            message=f"Successfully added {len(images_data)} image(s) to fabric",
            data=fabric_serializer.data,
            status_code=status.HTTP_200_OK
        )

@extend_schema(
    tags=["Fabric Images"],
    description="Update or replace an existing fabric image"
)
class FabricImageUpdateView(BaseTailorAuthenticatedView):
    """
    View to update/replace an existing fabric image file
    """
    parser_classes = [MultiPartParser, FormParser]
    
    @extend_schema(
        description="Replace an existing fabric image file. Optionally update is_primary and order.",
        responses={
            200: FabricSerializer,
            400: {"description": "Validation failed"},
            404: {"description": "Image not found"},
            403: {"description": "You don't have permission to modify this image"}
        }
    )
    def patch(self, request, image_id):
        # Find the image
        try:
            image = FabricImage.objects.select_related('fabric', 'fabric__tailor').get(pk=image_id)
        except FabricImage.DoesNotExist:
            return api_response(
                success=False,
                message="Image not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Check permissions
        if image.fabric.tailor.user != request.user:
            return api_response(
                success=False,
                message="You don't have permission to modify this image",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Update image file if provided
        if 'image' in request.FILES:
            new_image = request.FILES['image']
            
            # Validate file size (5MB limit)
            if new_image.size > 5 * 1024 * 1024:
                return api_response(
                    success=False,
                    message=f"Image size exceeds 5MB limit: {new_image.name}",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate file format
            allowed_extensions = ['jpg', 'jpeg', 'png']
            file_extension = new_image.name.split('.')[-1].lower()
            if file_extension not in allowed_extensions:
                return api_response(
                    success=False,
                    message=f"Invalid file format for {new_image.name}. Only JPG, JPEG, and PNG files are allowed.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Delete old image file
            if image.image:
                image.image.delete(save=False)
            
            # Set new image
            image.image = new_image
        
        # Update is_primary if provided
        if 'is_primary' in request.POST:
            is_primary = request.POST.get('is_primary', 'false').lower() == 'true'
            if is_primary:
                # Unset other primary images
                image.fabric.gallery.filter(is_primary=True).exclude(pk=image_id).update(is_primary=False)
            image.is_primary = is_primary
        
        # Update order if provided
        if 'order' in request.POST:
            try:
                image.order = int(request.POST.get('order'))
            except ValueError:
                return api_response(
                    success=False,
                    message="Invalid order value",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        
        # Save the image
        image.save()
        
        # Refresh fabric to get updated gallery
        image.fabric.refresh_from_db()
        
        # Return the updated fabric
        fabric_serializer = FabricSerializer(image.fabric, context={'request': request})
        return api_response(
            success=True,
            message="Image updated successfully",
            data=fabric_serializer.data,
            status_code=status.HTTP_200_OK
        )
