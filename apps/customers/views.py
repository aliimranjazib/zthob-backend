from django.shortcuts import render
from rest_framework.views import APIView
from django.template.context_processors import request
from django.contrib.auth.models import User
from rest_framework import serializers, status
from apps.customers.models import Address, CustomerProfile, FamilyMember
from apps.customers.serializers import AddressSerializer, CustomerProfileSerializer, FabricCatalogSerializer, FamilyMemberSerializer
from apps.tailors.models import Fabric
from zthob.utils import api_response
from drf_spectacular.views import extend_schema


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
        
   @extend_schema(operation_id="customers_family_create")
   def post(self, request):
       print("data is valid===============")
       serializers = FamilyMemberSerializer(data=request.data, context={'user': request.user})
       if serializers.is_valid():
           print("data is valid===============")
           serializers.save()
           return api_response(success=True, message='family member added successfully',
                           data=serializers.data,
                           status_code=status.HTTP_200_OK
                           )
       return api_response(success=False, message='family member added failed',
                           errors=serializers.errors,
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
           serializers = FamilyMemberSerializer(data=request.data, instance=family, partial=True)
           if serializers.is_valid():
               serializers.save()
               return api_response(success=True, message='family member update successfully',
                               data=serializers.data, status_code=status.HTTP_200_OK
                               )
           return api_response(success=False,
                                   message='family member update failed',
                                   errors=serializers.errors,
                                   status_code=status.HTTP_200_OK
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
    serializer_class = AddressSerializer

    @extend_schema(operation_id="address_list")
    def get(self, request):
        address = Address.objects.filter(user=request.user)
        serializers = AddressSerializer(address, many=True)
        return api_response(success=True, message='address fetch successfully',
                            data=serializers.data,
                            status_code=status.HTTP_200_OK
                            )


class AddressCreateView(APIView):
    serializer_class = AddressSerializer

    @extend_schema(operation_id="address_create")
    def post(self, request):
        serializers = AddressSerializer(data=request.data)
        if serializers.is_valid():
            serializers.save(user=request.user)
            return api_response(success=True, message='address created successfully',
                            data=serializers.data,
                            status_code=status.HTTP_200_OK
                            )
        return api_response(success=False, message='address creation failed',
                            errors=serializers.errors,
                            status_code=status.HTTP_400_BAD_REQUEST
                            )


class AddressDetailView(APIView):
    serializer_class = AddressSerializer

    def get(self, request, pk):
        address = Address.objects.filter(pk=pk, user=request.user).first()
        if address:
            serializers = AddressSerializer(address)
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
            serializers = AddressSerializer(data=request.data, instance=address, partial=True)
            if serializers.is_valid():
                serializers.save()
                return api_response(success=True,
                                    message='Address updated successfully',
                                    data=serializers.data,
                                    status_code=status.HTTP_200_OK
                                    )
            return api_response(success=False,
                                    message='Address update failed',
                                    errors=serializers.errors,
                                    status_code=status.HTTP_200_OK
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
         
         
        