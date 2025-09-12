from .models import CustomUser
from rest_framework import serializers



class UserRegisterSerializer(serializers.ModelSerializer):
    name = serializers.CharField(write_only=True)
    password=serializers.CharField(write_only=True)
    confirm_password=serializers.CharField(write_only=True)
    
    class Meta:
        model=CustomUser
        fields=['name','email','password','confirm_password','role']
        extra_kwargs = {
            "email": {"help_text": "Valid email address required"},
            "phone": {"help_text": "Valid Saudi phone number (05xxxxxxxx)"},
        }
        
    def validate(self,attr):
        if(attr['password']!=attr['confirm_password']):
            raise serializers.ValidationError("Password do not match")
        return attr
    def validate_email(self,value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError('email must be unique')
        return value
            
    # def create(self,validate_data):
    #     validate_data.pop('confirm_password')
    #     user=CustomUser.objects.create_user(**validate_data)
    #     return user
    def create(self, validated_data):
        name = validated_data.pop("name")
        password = validated_data.pop("password")
        validated_data.pop('confirm_password')

        # Split name into first_name and last_name
        first_name, *last_name = name.split(" ", 1)
        validated_data["first_name"] = first_name
        validated_data["last_name"] = last_name[0] if last_name else ""

        # Set username = email
        validated_data["username"] = validated_data["email"]

        # Create user
        user = CustomUser.objects.create_user(password=password, **validated_data)
        return user
        
class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model=CustomUser
        fields = [
            'id',
            'username',
            'email',
            'role',
            'phone',
            'first_name',
            'last_name',
            'date_joined',
        ]
        read_only_fields = [
            'id',
            'username',
            'email',
            'role',
            'date_joined',
        ]

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
    

    