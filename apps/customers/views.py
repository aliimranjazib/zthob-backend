from django.shortcuts import render
from rest_framework.views import APIView
from django.template.context_processors import request
from django.contrib.auth.models import User
from rest_framework import serializers, status
from apps.customers.models import Address, CustomerProfile, FamilyMember
from apps.customers.serializers import AddressSerializer, AddressCreateSerializer, AddressResponseSerializer, CustomerProfileSerializer, FabricCatalogSerializer, FamilyMemberSerializer, FamilyMemberCreateSerializer, FamilyMemberSimpleResponseSerializer
from apps.tailors.models import Fabric
from zthob.utils import api_response
from drf_spectacular.utils import extend_schema, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from apps.tailors.models import TailorProfile
from apps.tailors.serializers import TailorProfileSerializer


# Create your views here.
class FabricCatalogAPIView(APIView):
    serializer_class = FabricCatalogSerializer
    def get(self,request):
        fabrics=Fabric.objects.select_related('category','fabric_type','tailor'
        ).prefetch_related('tags','gallery').all()
        serializers=FabricCatalogSerializer(fabrics, many=True,context={"request": request})
        return api_response(success=True, message="Fabrics fetched successfully",
                            data=serializers.data,
                            status_code=status.HTTP_200_OK)
 
 


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
         
         
class TailorListAPIView(APIView):

    serializer_class=TailorProfileSerializer

    @extend_schema(operation_id="customers_tailor_list")
    def get(self, request):
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

class TailorFabricsAPIView(APIView):
    """API view to fetch fabrics of a specific tailor for customers"""
    serializer_class = FabricCatalogSerializer
    
    @extend_schema(operation_id="customers_tailor_fabrics")
    def get(self, request, tailor_id):
        """
        Fetch all fabrics of a specific tailor
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