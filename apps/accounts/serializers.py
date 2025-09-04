from .models import CustomUser
from rest_framework import serializers



class UserRegisterSerializer(serializers.ModelSerializer):
    password=serializers.CharField(write_only=True)
    confirm_password=serializers.CharField(write_only=True)
    
    class Meta:
        model=CustomUser
        fields=['first_name','last_name','username','email','password','confirm_password','role']
        extra_kwargs={'username':{'help_text':'username must be unique and between 3-100 character'},
             'email':{'help_text':'Valid email address required'},
             'role':{'help_text':'Choose Role : User, Rider, Tailor '}  
        }
        
    def validate(self,attr):
        if(attr['password']!=attr['confirm_password']):
            raise serializers.ValidationError("Password do not match")
        return attr
    def validate_username(self,value):
        if len(value)<3:
            raise serializers.ValidationError('username must be atleast 3 character long')
        if CustomUser.objects.filter(username=value).exists():
            raise serializers.ValidationError('username already exists')
        return value
    def validate_email(self,value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError('email must be unique')
        return value
            
    def create(self,validate_data):
        validate_data.pop('confirm_password')
        user=CustomUser.objects.create_user(**validate_data)
        return user
        
class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model=CustomUser
        fields = [
            'id', 'username', 'email', 'role', 'phone', 'first_name', 'last_name',
        ]
        read_only_fields = ['id', 'username', 'email', 'role', 'date_joined']

class UserLoginSerializer(serializers.Serializer):
    username=serializers.CharField()
    password=serializers.CharField()
    
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField()
    confirm_new_password = serializers.CharField()
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_new_password']:
            raise serializers.ValidationError("New passwords don't match")
        return attrs
    

    