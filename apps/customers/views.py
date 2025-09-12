from django.shortcuts import render
from rest_framework.views import APIView
from django.template.context_processors import request
from django.contrib.auth.models import User
from rest_framework import serializers, status
from apps.customers.models import Address, CustomerProfile, FamilyMember
from apps.customers.serializers import AddressSerializer, CustomerProfileSerializer, FabricCatalogSerializer, FamilyMemberSerializer
from apps.tailors.models import Fabric
from zthob.utils import api_response


# Create your views here.
class FabricCatalogAPIView(APIView):
    serializer_class = FabricCatalogSerializer
    def get(self,request):
        fabrics=Fabric.objects.all()
        serialzers=FabricCatalogSerializer(fabrics, many=True,context={"request": request})
        return api_response(success=True, message="Fabrics fetched successfully",
                            data=serialzers.data,
                            status_code=status.HTTP_200_OK)
 
 
class FamilyMemberAPIView(APIView):
     serializer_class=FamilyMemberSerializer
     
     def get(self,request):
         family=FamilyMember.objects.filter(user=request.user)
         serializers=FamilyMemberSerializer(family,many=True)
         return api_response(success=True, message='family members fetech successfully',
                            data=serializers.data,
                            status_code=status.HTTP_200_OK
                            )
         
     def post(self,request):
         print("data is valid===============")
         serializers=FamilyMemberSerializer(data=request.data, context={'user':request.user})
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
         
     def put(self,request,pk):
        family=FamilyMember.objects.filter(pk=pk, user=request.user).first()
        if family:
            serializers=FamilyMemberSerializer(data=request.data, instance=family, partial=True)
            if serializers.is_valid():
                serializers.save()
                return api_response(success=True, message='family member update successfully',
                                data=serializers.data, status_code=status.HTTP_200_OK 
                                )
            return api_response(success=False,
                                    message='family member updated failed',
                                    errors=serializers.errors,
                                    status_code=status.HTTP_200_OK
           
                                 )
        else:
            return api_response(success=False,
                                    message='family member updated failed',
                                    errors='',
                                    status_code=status.HTTP_400_BAD_REQUEST
                                    )
         
         
             
            
class AddressListCreateAPIView(APIView):
    serializer_class = AddressSerializer
    def get(self, request):
        address=Address.objects.filter(user=request.user)
        serializers=AddressSerializer(address,many=True)
        return api_response(success=True, message='address fetech successfully',
                            data=serializers.data,
                            status_code=status.HTTP_200_OK
                            )
    def post(self,request):
        serializers=AddressSerializer(data=request.data)
        if serializers.is_valid():
            serializers.save(user=request.user)
            return api_response(success=True, message='address updated successfully',
                            data=serializers.data,
                            status_code=status.HTTP_200_OK
                            )
        return api_response(success=False, message='address updated failed',
                            errors=serializers.errors,
                            status_code=status.HTTP_400_BAD_REQUEST
                            )

    def put(self,request,pk):
        address=Address.objects.filter(pk=pk, user=request.user).first()
        if address:
            serializers=AddressSerializer(data=request.data,instance=address, partial=True)
            if serializers.is_valid():
                serializers.save()
                return api_response(success=True,
                                    message='Address updated successfully',
                                    data=serializers.data,
                                    status_code=status.HTTP_200_OK
                                    )
            return api_response(success=False,
                                    message='Address updated failed',
                                    errors=serializers.errors,
                                    status_code=status.HTTP_200_OK
                                    )
        else:
            return api_response(success=False,
                                    message='Address updated failed',
                                    errors='',
                                    status_code=status.HTTP_400_BAD_REQUEST
                                    )
    def delete(self, request, pk):
        address_qs = Address.objects.filter(pk=pk, user=request.user)  # also restrict to user if needed

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
         
         
        