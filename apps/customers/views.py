from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.template.context_processors import request
from django.contrib.auth.models import User
from rest_framework import serializers, status
from apps.customers.models import Address, CustomerProfile, FamilyMember, FabricFavorite
from apps.customers.serializers import AddressSerializer, AddressCreateSerializer, AddressResponseSerializer, CustomerProfileSerializer, FabricCatalogSerializer, FamilyMemberSerializer, FamilyMemberCreateSerializer, FamilyMemberSimpleResponseSerializer, FabricFavoriteSerializer, CustomerMeasurementsListSerializer, FamilyMemberMeasurementsDetailSerializer
from apps.orders.models import Order
from apps.tailors.models import Fabric
from zthob.utils import api_response
from drf_spectacular.utils import extend_schema, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from apps.tailors.models import TailorProfile
from apps.tailors.serializers import TailorProfileSerializer


# Create your views here.
@extend_schema(
    tags=["Fabric Catalog"],
    description="Get all active fabrics (No authentication required)",
    responses={200: FabricCatalogSerializer(many=True)}
)
class FabricCatalogAPIView(APIView):
    serializer_class = FabricCatalogSerializer
    permission_classes = [AllowAny]  # Allow unauthenticated users to browse fabrics
    
    def get(self, request):
        """Get all active fabrics without authentication."""
        fabrics = Fabric.objects.filter(
            is_active=True
        ).select_related(
            'category', 'fabric_type', 'tailor'
        ).prefetch_related(
            'tags', 'gallery'
        ).order_by('-created_at')
        
        serializer = FabricCatalogSerializer(fabrics, many=True, context={"request": request})
        return api_response(
            success=True, 
            message="Fabrics fetched successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
 
 


class FamilyMemberListView(APIView):
   serializer_class = FamilyMemberSerializer
    
   @extend_schema(operation_id="customers_family_list")
   def get(self, request):
       family = FamilyMember.objects.filter(user=request.user)
       serializers = FamilyMemberSerializer(family, many=True)
       return api_response(success=True, message='family members fetch successfully',
                           data=serializers.data,
                           status_code=status.HTTP_200_OK
                           )
        
   @extend_schema(
       operation_id="customers_family_create",
       request=FamilyMemberCreateSerializer,
       responses={201: FamilyMemberSimpleResponseSerializer, 400: OpenApiTypes.OBJECT},
       examples=[
           OpenApiExample(
               'Create Family Member',
               value={'name': 'ahmad'},
               request_only=True,
           ),
           OpenApiExample(
               'Success Response',
               value={'id': 1, 'name': 'ahmad'},
               response_only=True,
           ),
       ]
   )
   def post(self, request):
       # Use simplified serializer for creation - only requires name
       serializer = FamilyMemberCreateSerializer(data=request.data, context={'user': request.user})
       if serializer.is_valid():
           family_member = serializer.save()
           # Return simplified response with only id and name
           response_serializer = FamilyMemberSimpleResponseSerializer(family_member)
           return api_response(success=True, message='family member added successfully',
                           data=response_serializer.data,
                           status_code=status.HTTP_201_CREATED
                           )
       return api_response(success=False, message='family member added failed',
                           errors=serializer.errors,
                           status_code=status.HTTP_400_BAD_REQUEST
                           )


class FamilyMemberDetailView(APIView):
   serializer_class = FamilyMemberSerializer

   @extend_schema(operation_id="customers_family_retrieve")
   def get(self, request, pk):
       family = FamilyMember.objects.filter(pk=pk, user=request.user).first()
       if family:
           serializers = FamilyMemberSerializer(family)
           return api_response(success=True, message='family member fetch successfully',
                               data=serializers.data,
                               status_code=status.HTTP_200_OK
                               )
       else:
           return api_response(success=False,
                                   message='family member not found',
                                   errors='',
                                   status_code=status.HTTP_404_NOT_FOUND
                                   )

   @extend_schema(operation_id="customers_family_update")
   def put(self, request, pk):
       family = FamilyMember.objects.filter(pk=pk, user=request.user).first()
       if family:
           serializers = FamilyMemberSerializer(data=request.data, instance=family, partial=True, context={'user': request.user, 'request': request})
           if serializers.is_valid():
               serializers.save()
               return api_response(success=True, message='family member update successfully',
                               data=serializers.data, status_code=status.HTTP_200_OK
                               )
           return api_response(success=False,
                                   message='family member update failed',
                                   errors=serializers.errors,
                                   status_code=status.HTTP_400_BAD_REQUEST
                                   )
       else:
           return api_response(success=False,
                                   message='family member not found',
                                   errors='',
                                   status_code=status.HTTP_404_NOT_FOUND
                                   )

   @extend_schema(operation_id="customers_family_destroy")
   def delete(self, request, pk):
       family_qs = FamilyMember.objects.filter(pk=pk, user=request.user)
       if family_qs.exists():
           family_qs.delete()
           return api_response(
               success=True,
               message='Family member deleted successfully',
               data=None,
               status_code=status.HTTP_200_OK
           )
       else:
           return api_response(
               success=False,
               message='Family member not found',
               data=None,
               status_code=status.HTTP_404_NOT_FOUND
           )
class AddressListView(APIView):
    serializer_class = AddressResponseSerializer

    @extend_schema(operation_id="address_list")
    def get(self, request):
        address = Address.objects.filter(user=request.user)
        serializers = AddressResponseSerializer(address, many=True)
        return api_response(success=True, message='address fetch successfully',
                            data=serializers.data,
                            status_code=status.HTTP_200_OK
                            )


class AddressCreateView(APIView):
    serializer_class = AddressCreateSerializer

    @extend_schema(operation_id="address_create")
    def post(self, request):
        serializer = AddressCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            address = serializer.save()
            # Return simplified response
            response_serializer = AddressResponseSerializer(address)
            return api_response(success=True, message='address created successfully',
                            data=response_serializer.data,
                            status_code=status.HTTP_201_CREATED
                            )
        return api_response(success=False, message='address creation failed',
                            errors=serializer.errors,
                            status_code=status.HTTP_400_BAD_REQUEST
                            )


class AddressDetailView(APIView):
    serializer_class = AddressResponseSerializer

    def get(self, request, pk):
        address = Address.objects.filter(pk=pk, user=request.user).first()
        if address:
            serializers = AddressResponseSerializer(address)
            return api_response(success=True, message='address fetch successfully',
                                data=serializers.data,
                                status_code=status.HTTP_200_OK
                                )
        else:
            return api_response(success=False,
                                    message='Address not found',
                                    errors='',
                                    status_code=status.HTTP_404_NOT_FOUND
                                    )

    @extend_schema(operation_id="customers_addresses_update")
    def put(self, request, pk):
        address = Address.objects.filter(pk=pk, user=request.user).first()
        if address:
            # Use AddressCreateSerializer for updates to maintain consistency
            serializer = AddressCreateSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                # Update the existing address
                address_data = serializer.validated_data
                address_text = address_data.pop('address')
                is_default = address_data.pop('is_default', address.is_default)
                
                address.street = address_text
                address.latitude = address_data.get('latitude', address.latitude)
                address.longitude = address_data.get('longitude', address.longitude)
                address.extra_info = address_data.get('extra_info', address.extra_info)
                address.address_tag = address_data.get('address_tag', address.address_tag)
                address.is_default = is_default
                
                # If this address is being set as default, make other addresses non-default
                if is_default:
                    Address.objects.filter(user=request.user, is_default=True).exclude(id=address.id).update(is_default=False)
                
                address.save()
                
                response_serializer = AddressResponseSerializer(address)
                return api_response(success=True,
                                    message='Address updated successfully',
                                    data=response_serializer.data,
                                    status_code=status.HTTP_200_OK
                                    )
            return api_response(success=False,
                                    message='Address update failed',
                                    errors=serializer.errors,
                                    status_code=status.HTTP_400_BAD_REQUEST
                                    )
        else:
            return api_response(success=False,
                                    message='Address not found',
                                    errors='',
                                    status_code=status.HTTP_400_BAD_REQUEST
                                    )

    @extend_schema(operation_id="customers_addresses_destroy")
    def delete(self, request, pk):
        address_qs = Address.objects.filter(pk=pk, user=request.user)

        if address_qs.exists():
            address_qs.delete()
            return api_response(
                success=True,
                message='Address deleted successfully',
                data=None,
                status_code=status.HTTP_200_OK
            )
        else:
            return api_response(
                success=False,
                message='Address not found',
                data=None,
                status_code=status.HTTP_404_NOT_FOUND
            )
class CustomerProfileAPIView(APIView):
     serializer_class = CustomerProfileSerializer

     def get(self,request):
         profile, created = CustomerProfile.objects.get_or_create(
            user=request.user,
            defaults={
                'gender': '',
                'date_of_birth': None,
                'default_address': None
            }
        )
         serializers=CustomerProfileSerializer(profile)
         return api_response(success=True, message='customer profile fetech successfully',
                            data=serializers.data,
                            status_code=status.HTTP_200_OK
                            )

     def put(self, request):
        profile, created = CustomerProfile.objects.get_or_create(user=request.user)
        serializers = CustomerProfileSerializer(profile, data=request.data, partial=True)
        
        if serializers.is_valid():
            serializers.save()
            return api_response(success=True, message='customer profile fetech successfully',
                            data=serializers.data,
                            status_code=status.HTTP_200_OK
                            )
        return api_response(success=True, message='customer profile failed',
                            errors=serializers.errors,
                            status_code=status.HTTP_400_BAD_REQUEST
                            )
         
         
@extend_schema(
    tags=["Tailor Profile"],
    description="Get all tailors (No authentication required)",
    responses={200: TailorProfileSerializer(many=True)}
)
class TailorListAPIView(APIView):
    serializer_class = TailorProfileSerializer
    permission_classes = [AllowAny]  # Allow unauthenticated users to browse tailors

    @extend_schema(operation_id="customers_tailor_list")
    def get(self, request):
        """Get all tailors without authentication."""
        # Fetch all tailor profiles with related data
        tailors = TailorProfile.objects.select_related('user').prefetch_related('review').all()
        
        # Serialize the data
        serializer = TailorProfileSerializer(tailors, many=True, context={'request': request})
        
        return api_response(
            success=True, 
            message="Tailors fetched successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )

@extend_schema(
    tags=["Fabric Catalog"],
    description="Get all active fabrics for a specific tailor (No authentication required)",
    responses={200: FabricCatalogSerializer(many=True), 404: {"description": "Tailor not found"}}
)
class TailorFabricsAPIView(APIView):
    """API view to fetch fabrics of a specific tailor for customers"""
    serializer_class = FabricCatalogSerializer
    permission_classes = [AllowAny]  # Allow unauthenticated users to browse tailor fabrics
    
    @extend_schema(operation_id="customers_tailor_fabrics")
    def get(self, request, tailor_id):
        """
        Fetch all active fabrics of a specific tailor without authentication.
        URL: /api/customers/tailors/{tailor_id}/fabrics/
        """
        try:
            # Get the tailor profile
            from apps.tailors.models import TailorProfile
            tailor = TailorProfile.objects.get(user__id=tailor_id)
            
            # Fetch all active fabrics for this tailor
            fabrics = Fabric.objects.filter(
                tailor=tailor,
                is_active=True  # Only show active fabrics to customers
            ).select_related(
                'category', 'fabric_type', 'tailor'
            ).prefetch_related(
                'tags', 'gallery'
            ).order_by('-created_at')
            
            # Serialize the data
            serializer = FabricCatalogSerializer(fabrics, many=True, context={'request': request})
            
            return api_response(
                success=True, 
                message=f"Fabrics for {tailor.shop_name or tailor.user.get_full_name()} fetched successfully",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
            
        except TailorProfile.DoesNotExist:
            return api_response(
                success=False,
                message="Tailor not found",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return api_response(
                success=False,
                message="Error fetching tailor fabrics",
                data=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(
    tags=["Tailor Profile"],
    description="Get a single tailor's profile details (No authentication required)",
    responses={200: TailorProfileSerializer, 404: {"description": "Tailor not found"}}
)
class TailorDetailAPIView(APIView):
    """API view to fetch a single tailor's profile details"""
    serializer_class = TailorProfileSerializer
    permission_classes = [AllowAny]  # Allow unauthenticated users to view tailor details
    
    @extend_schema(operation_id="customers_tailor_detail")
    def get(self, request, tailor_id):
        """
        Get a single tailor's profile details without authentication.
        URL: /api/customers/tailors/{tailor_id}/
        """
        try:
            # Get the tailor profile
            from apps.tailors.models import TailorProfile
            tailor = TailorProfile.objects.select_related('user').prefetch_related('review').get(user__id=tailor_id)
            
            # Serialize the data
            serializer = TailorProfileSerializer(tailor, context={'request': request})
            
            return api_response(
                success=True, 
                message="Tailor details fetched successfully",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
            
        except TailorProfile.DoesNotExist:
            return api_response(
                success=False,
                message="Tailor not found",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return api_response(
                success=False,
                message="Error fetching tailor details",
                data=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(
    tags=["Fabric Catalog"],
    description="Get a single fabric's details (No authentication required)",
    responses={200: FabricCatalogSerializer, 404: {"description": "Fabric not found"}}
)
class FabricDetailAPIView(APIView):
    """API view to fetch a single fabric's details"""
    serializer_class = FabricCatalogSerializer
    permission_classes = [AllowAny]  # Allow unauthenticated users to view fabric details
    
    @extend_schema(operation_id="customers_fabric_detail")
    def get(self, request, fabric_id):
        """
        Get a single fabric's details without authentication.
        URL: /api/customers/fabrics/{fabric_id}/
        """
        try:
            # Get the fabric - only show active fabrics
            fabric = Fabric.objects.filter(
                id=fabric_id,
                is_active=True
            ).select_related(
                'category', 'fabric_type', 'tailor'
            ).prefetch_related(
                'tags', 'gallery'
            ).first()
            
            if not fabric:
                return api_response(
                    success=False,
                    message="Fabric not found or not available",
                    data=None,
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            # Serialize the data
            serializer = FabricCatalogSerializer(fabric, context={'request': request})
            
            return api_response(
                success=True, 
                message="Fabric details fetched successfully",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
            
        except Exception as e:
            return api_response(
                success=False,
                message="Error fetching fabric details",
                data=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FabricFavoriteToggleView(APIView):
    """API view to toggle favorite status for a fabric."""
    permission_classes = [IsAuthenticated]
    serializer_class = FabricFavoriteSerializer
    
    @extend_schema(
        operation_id="customers_fabric_favorite_toggle",
        description="Toggle favorite status for a fabric. If fabric is not favorited, it will be added to favorites. If already favorited, it will be removed.",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "message": {"type": "string"},
                    "data": {
                        "type": "object",
                        "properties": {
                            "fabric_id": {"type": "integer"},
                            "is_favorited": {"type": "boolean"},
                            "favorited_at": {"type": "string", "format": "date-time"}
                        }
                    }
                }
            },
            404: {"description": "Fabric not found"},
        },
        tags=["Fabric Favorites"]
    )
    def post(self, request, fabric_id):
        """
        Toggle favorite status for a fabric.
        URL: /api/customers/fabrics/{fabric_id}/favorite/
        """
        try:
            fabric = Fabric.objects.get(pk=fabric_id, is_active=True)
        except Fabric.DoesNotExist:
            return api_response(
                success=False,
                message="Fabric not found or not available",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Check if already favorited
        favorite, created = FabricFavorite.objects.get_or_create(
            user=request.user,
            fabric=fabric
        )
        
        if not created:
            # Already favorited, remove it
            favorite.delete()
            is_favorited = False
            message = "Fabric removed from favorites"
            favorited_at = None
        else:
            # Newly favorited
            is_favorited = True
            message = "Fabric added to favorites"
            favorited_at = favorite.created_at
        
        return api_response(
            success=True,
            message=message,
            data={
                "fabric_id": fabric.id,
                "is_favorited": is_favorited,
                "favorited_at": favorited_at.isoformat() if favorited_at else None
            },
            status_code=status.HTTP_200_OK
        )


class FabricFavoriteListView(APIView):
    """API view to list all favorite fabrics for the authenticated user."""
    permission_classes = [IsAuthenticated]
    serializer_class = FabricFavoriteSerializer
    
    @extend_schema(
        operation_id="customers_favorites_list",
        description="Get all favorite fabrics for the authenticated user",
        responses={200: FabricFavoriteSerializer(many=True)},
        tags=["Fabric Favorites"]
    )
    def get(self, request):
        """
        Get all favorite fabrics for the authenticated user.
        URL: /api/customers/favorites/
        """
        favorites = FabricFavorite.objects.filter(
            user=request.user
        ).select_related(
            'fabric',
            'fabric__category',
            'fabric__fabric_type',
            'fabric__tailor',
            'fabric__tailor__user'
        ).prefetch_related(
            'fabric__tags',
            'fabric__gallery'
        ).order_by('-created_at')
        
        serializer = FabricFavoriteSerializer(favorites, many=True, context={'request': request})
        
        return api_response(
            success=True,
            message="Favorite fabrics fetched successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


# ============================================================================
# MEASUREMENT VIEWS
# ============================================================================

class CustomerMeasurementsListView(APIView):
    """List all measurements for customer and their family members"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Get all measurements",
        description="Retrieve all measurements for the authenticated customer and their family members. Supports filtering by family_member_id, recipient_type, and order_id.",
        tags=["Customer Measurements"],
        parameters=[
            {
                'name': 'family_member_id',
                'in': 'query',
                'description': 'Filter by specific family member ID',
                'required': False,
                'schema': {'type': 'integer'}
            },
            {
                'name': 'recipient_type',
                'in': 'query',
                'description': 'Filter by recipient type: customer or family_member',
                'required': False,
                'schema': {'type': 'string', 'enum': ['customer', 'family_member']}
            },
            {
                'name': 'order_id',
                'in': 'query',
                'description': 'Filter by specific order ID',
                'required': False,
                'schema': {'type': 'integer'}
            },
            {
                'name': 'include_stored',
                'in': 'query',
                'description': 'Include stored profile measurements (default: true)',
                'required': False,
                'schema': {'type': 'boolean', 'default': True}
            }
        ]
    )
    def get(self, request):
        if request.user.role != 'USER':
            return api_response(
                success=False,
                message="Only customers can access this endpoint",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Get query parameters
        family_member_id = request.query_params.get('family_member_id')
        recipient_type = request.query_params.get('recipient_type')
        order_id = request.query_params.get('order_id')
        include_stored = request.query_params.get('include_stored', 'true').lower() == 'true'
        
        # Get all orders with measurements for this customer
        orders_query = Order.objects.filter(
            customer=request.user,
            rider_status='measurement_taken',
            rider_measurements__isnull=False
        ).select_related(
            'customer',
            'family_member',
            'tailor',
            'rider'
        ).prefetch_related('tailor__tailor_profile')
        
        # Apply filters
        if order_id:
            orders_query = orders_query.filter(id=order_id)
        
        if family_member_id:
            orders_query = orders_query.filter(family_member_id=family_member_id)
        
        orders = orders_query.order_by('-measurement_taken_at', '-created_at').prefetch_related('order_items__family_member')
        
        # Separate customer and family member measurements
        customer_measurements = []
        family_member_measurements = []
        family_members_data = {}  # Track family members for summary
        
        processed_recipients_per_order = set() # Track (order_id, recipient_id) to avoid duplicates if multiple items for same person

        for order in orders:
            # Check order items for recipients and measurements
            for item in order.order_items.all():
                # Skip if no measurements for this item
                if not item.measurements and not order.rider_measurements:
                    continue
                
                recipient_id = item.family_member.id if item.family_member else request.user.id
                recipient_type_val = 'family_member' if item.family_member else 'customer'
                
                key = (order.id, recipient_id)
                if key in processed_recipients_per_order:
                    continue
                
                measurement_data = {
                    'order_id': order.id,
                    'order_number': order.order_number,
                    'order_type': order.order_type,
                    'measurements': item.measurements or order.rider_measurements,
                    'measurement_taken_at': order.measurement_taken_at.isoformat() if order.measurement_taken_at else None,
                    'order_status': order.status,
                    'rider_status': order.rider_status,
                    'order_created_at': order.created_at.isoformat() if order.created_at else None,
                }
                
                # Get tailor name if available
                try:
                    if order.tailor and hasattr(order.tailor, 'tailor_profile'):
                        measurement_data['tailor_name'] = order.tailor.tailor_profile.shop_name
                    else:
                        measurement_data['tailor_name'] = order.tailor.username if order.tailor else None
                except:
                    measurement_data['tailor_name'] = None

                if item.family_member:
                    # Family member recipient
                    if not recipient_type or recipient_type == 'family_member':
                        if not family_member_id or item.family_member.id == int(family_member_id):
                            measurement_data.update({
                                'recipient_type': 'family_member',
                                'recipient_id': item.family_member.id,
                                'recipient_name': item.family_member.name,
                                'recipient_relationship': item.family_member.relationship,
                                'recipient_gender': item.family_member.gender,
                            })
                            family_member_measurements.append(measurement_data)
                            
                            # Track for summary
                            fm_id = item.family_member.id
                            if fm_id not in family_members_data:
                                family_members_data[fm_id] = {
                                    'family_member_id': fm_id,
                                    'family_member_name': item.family_member.name,
                                    'relationship': item.family_member.relationship,
                                    'total_measurements': 0,
                                    'latest_measurement_date': None,
                                }
                            family_members_data[fm_id]['total_measurements'] += 1
                            if not family_members_data[fm_id]['latest_measurement_date'] or \
                               (order.measurement_taken_at and order.measurement_taken_at > family_members_data[fm_id]['latest_measurement_date']):
                                family_members_data[fm_id]['latest_measurement_date'] = order.measurement_taken_at
                else:
                    # Customer's own recipient
                    if not recipient_type or recipient_type == 'customer':
                        measurement_data.update({
                            'recipient_type': 'customer',
                            'recipient_id': request.user.id,
                            'recipient_name': request.user.get_full_name() or request.user.username,
                        })
                        customer_measurements.append(measurement_data)
                
                processed_recipients_per_order.add(key)
        
        # Get stored profile measurements
        stored_profile_measurements = []
        if include_stored:
            # Customer's own stored measurements
            try:
                if hasattr(request.user, 'customer_profile') and request.user.customer_profile.measurements:
                    stored_profile_measurements.append({
                        'recipient_type': 'customer',
                        'recipient_id': request.user.id,
                        'recipient_name': request.user.get_full_name() or request.user.username,
                        'measurements': request.user.customer_profile.measurements,
                        'last_updated': None,
                        'note': 'Stored customer profile measurements'
                    })
            except:
                pass

            # Family members' stored measurements
            family_members = FamilyMember.objects.filter(user=request.user)
            if family_member_id:
                family_members = family_members.filter(id=family_member_id)
            
            for fm in family_members:
                if fm.measurements:
                    stored_profile_measurements.append({
                        'recipient_type': 'family_member',
                        'recipient_id': fm.id,
                        'recipient_name': fm.name,
                        'recipient_relationship': fm.relationship,
                        'recipient_gender': fm.gender,
                        'measurements': fm.measurements,
                        'last_updated': None,  # FamilyMember doesn't have last_updated field
                        'note': 'Stored profile measurements (not tied to a specific order)'
                    })
                    
                    # Update summary
                    if fm.id not in family_members_data:
                        family_members_data[fm.id] = {
                            'family_member_id': fm.id,
                            'family_member_name': fm.name,
                            'relationship': fm.relationship,
                            'total_measurements': 0,
                            'latest_measurement_date': None,
                            'has_stored_measurements': True,
                        }
                    else:
                        family_members_data[fm.id]['has_stored_measurements'] = True
        
        # Build summary
        summary = {
            'total_customer_measurements': len(customer_measurements),
            'total_family_member_measurements': len(family_member_measurements),
            'total_family_members_with_measurements': len(family_members_data),
            'total_unique_recipients': len(customer_measurements) + len(family_members_data),
        }
        
        # Build response data
        response_data = {
            'customer_measurements': customer_measurements,
            'family_member_measurements': family_member_measurements,
            'family_members_summary': list(family_members_data.values()),
            'stored_profile_measurements': stored_profile_measurements,
            'summary': summary,
        }
        
        # If filtering by family_member_id, return simplified structure
        if family_member_id:
            try:
                fm = FamilyMember.objects.get(id=family_member_id, user=request.user)
                response_data = {
                    'family_member_info': {
                        'id': fm.id,
                        'name': fm.name,
                        'relationship': fm.relationship,
                        'gender': fm.gender,
                    },
                    'order_measurements': family_member_measurements,
                    'stored_profile_measurements': {
                        'measurements': fm.measurements if fm.measurements else None,
                        'last_updated': None,
                        'note': 'Stored profile measurements'
                    } if fm.measurements else None,
                    'summary': {
                        'total_order_measurements': len(family_member_measurements),
                        'has_stored_measurements': bool(fm.measurements),
                        'latest_measurement_date': family_members_data.get(fm.id, {}).get('latest_measurement_date').isoformat() if family_members_data.get(fm.id, {}).get('latest_measurement_date') else None,
                    }
                }
            except FamilyMember.DoesNotExist:
                return api_response(
                    success=False,
                    message="Family member not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )
        
        return api_response(
            success=True,
            message="Measurements retrieved successfully",
            data=response_data,
            status_code=status.HTTP_200_OK
        )


class FamilyMemberMeasurementsView(APIView):
    """Get all measurements for a specific family member"""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Get family member measurements",
        description="Retrieve all measurements for a specific family member across all orders",
        tags=["Customer Measurements"]
    )
    def get(self, request, family_member_id):
        if request.user.role != 'USER':
            return api_response(
                success=False,
                message="Only customers can access this endpoint",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Verify family member belongs to customer
        try:
            family_member = FamilyMember.objects.get(id=family_member_id, user=request.user)
        except FamilyMember.DoesNotExist:
            return api_response(
                success=False,
                message="Family member not found or you don't have access to this family member",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Get all orders with measurements for this family member
        # Search in both order-level family_member and item-level family_member
        from django.db.models import Q
        orders = Order.objects.filter(
            Q(family_member=family_member) | Q(order_items__family_member=family_member),
            customer=request.user,
            rider_status='measurement_taken'
        ).select_related(
            'customer',
            'family_member',
            'tailor',
            'rider'
        ).prefetch_related('tailor__tailor_profile', 'order_items__family_member').distinct().order_by('-measurement_taken_at', '-created_at')
        
        # Build order measurements list
        order_measurements = []
        for order in orders:
            # Look for measurements in items for this family member
            item_measurements = None
            for item in order.order_items.all():
                if item.family_member == family_member and item.measurements:
                    item_measurements = item.measurements
                    break
            
            # Fallback to order-level measurements
            measurements = item_measurements or order.rider_measurements
            
            if measurements:
                measurement_data = {
                    'order_id': order.id,
                    'order_number': order.order_number,
                    'order_type': order.order_type,
                    'measurements': measurements,
                    'measurement_taken_at': order.measurement_taken_at.isoformat() if order.measurement_taken_at else None,
                    'order_status': order.status,
                    'rider_status': order.rider_status,
                    'order_created_at': order.created_at.isoformat() if order.created_at else None,
                    'appointment_date': order.appointment_date.isoformat() if order.appointment_date else None,
                    'appointment_time': order.appointment_time.isoformat() if order.appointment_time else None,
                }
                
                # Get tailor name
                try:
                    if order.tailor and hasattr(order.tailor, 'tailor_profile'):
                        measurement_data['tailor_name'] = order.tailor.tailor_profile.shop_name
                    else:
                        measurement_data['tailor_name'] = order.tailor.username if order.tailor else None
                except:
                    measurement_data['tailor_name'] = None
                
                order_measurements.append(measurement_data)
        
        # Get stored profile measurements
        stored_profile_measurements = None
        if family_member.measurements:
            stored_profile_measurements = {
                'measurements': family_member.measurements,
                'last_updated': None,
                'note': 'Stored profile measurements (most recent from orders)'
            }
        
        # Build summary
        latest_date = None
        oldest_date = None
        if order_measurements:
            dates = [m['measurement_taken_at'] for m in order_measurements if m['measurement_taken_at']]
            if dates:
                latest_date = max(dates)
                oldest_date = min(dates)
        
        summary = {
            'total_order_measurements': len(order_measurements),
            'has_stored_measurements': bool(family_member.measurements),
            'latest_measurement_date': latest_date,
            'oldest_measurement_date': oldest_date,
            'measurement_history_count': len(order_measurements),
        }
        
        response_data = {
            'family_member': {
                'id': family_member.id,
                'name': family_member.name,
                'relationship': family_member.relationship,
                'gender': family_member.gender,
            },
            'order_measurements': order_measurements,
            'stored_profile_measurements': stored_profile_measurements,
            'summary': summary,
        }
        
        return api_response(
            success=True,
            message="Family member measurements retrieved successfully",
            data=response_data,
            status_code=status.HTTP_200_OK
        )