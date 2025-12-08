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

class PhoneLoginSerializer(serializers.Serializer):
    """Serializer for phone login - sends OTP"""
    phone = serializers.CharField(max_length=15, required=True)
    
    def validate_phone(self, value):
        """Validate and normalize phone number - accepts Saudi Arabia and Pakistan formats"""
        # Remove any spaces or special characters except +
        phone = value.strip().replace(' ', '').replace('-', '')
        
        # Extract digits for validation
        digits = ''.join(filter(str.isdigit, phone))
        
        # Validate Saudi Arabia formats: +9665xxxxxxxx, 05xxxxxxxx, 5xxxxxxxx, 9665xxxxxxxx
        if phone.startswith('+9665') and len(digits) >= 12:
            # Saudi E.164 format: +9665xxxxxxxx
            pass
        elif digits.startswith('05') and len(digits) == 10:
            # Saudi format: 05xxxxxxxx
            pass
        elif digits.startswith('5') and len(digits) == 9:
            # Saudi format without leading 0: 5xxxxxxxx
            pass
        elif digits.startswith('9665') and len(digits) >= 12:
            # Saudi with country code: 9665xxxxxxxx
            pass
        # Validate Pakistan formats: +923xxxxxxxxx, 03xxxxxxxxx, 3xxxxxxxxx
        elif phone.startswith('+92') and len(digits) >= 12:
            # Pakistan E.164 format: +923xxxxxxxxx
            pass
        elif digits.startswith('03') and len(digits) == 11:
            # Pakistan format: 03xxxxxxxxx
            pass
        elif digits.startswith('3') and len(digits) == 10:
            # Pakistan format without leading 0: 3xxxxxxxxx
            pass
        elif digits.startswith('923') and len(digits) >= 12:
            # Pakistan with country code: 923xxxxxxxxx
            pass
        else:
            raise serializers.ValidationError('Phone number must be in Saudi Arabia format (05xxxxxxxx) or Pakistan format (03xxxxxxxxx)')
        
        return phone

class PhoneVerifySerializer(serializers.Serializer):
    """Serializer for OTP verification - completes login/registration"""
    phone = serializers.CharField(max_length=15, required=True)
    otp_code = serializers.CharField(max_length=6, required=True)
    name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=CustomUser.USER_ROLES, required=False, default='USER')
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    
    def validate_otp_code(self, value):
        """Validate OTP format"""
        if not value.isdigit() or len(value) != 6:
            raise serializers.ValidationError('OTP must be 6 digits')
        return value
    
    def validate_phone(self, value):
        """Validate and normalize phone number - accepts Saudi Arabia and Pakistan formats"""
        # Remove any spaces or special characters except +
        phone = value.strip().replace(' ', '').replace('-', '')
        
        # Extract digits for validation
        digits = ''.join(filter(str.isdigit, phone))
        
        # Validate Saudi Arabia formats: +9665xxxxxxxx, 05xxxxxxxx, 5xxxxxxxx, 9665xxxxxxxx
        if phone.startswith('+9665') and len(digits) >= 12:
            # Saudi E.164 format: +9665xxxxxxxx
            pass
        elif digits.startswith('05') and len(digits) == 10:
            # Saudi format: 05xxxxxxxx
            pass
        elif digits.startswith('5') and len(digits) == 9:
            # Saudi format without leading 0: 5xxxxxxxx
            pass
        elif digits.startswith('9665') and len(digits) >= 12:
            # Saudi with country code: 9665xxxxxxxx
            pass
        # Validate Pakistan formats: +923xxxxxxxxx, 03xxxxxxxxx, 3xxxxxxxxx
        elif phone.startswith('+92') and len(digits) >= 12:
            # Pakistan E.164 format: +923xxxxxxxxx
            pass
        elif digits.startswith('03') and len(digits) == 11:
            # Pakistan format: 03xxxxxxxxx
            pass
        elif digits.startswith('3') and len(digits) == 10:
            # Pakistan format without leading 0: 3xxxxxxxxx
            pass
        elif digits.startswith('923') and len(digits) >= 12:
            # Pakistan with country code: 923xxxxxxxxx
            pass
        else:
            raise serializers.ValidationError('Phone number must be in Saudi Arabia format (05xxxxxxxx) or Pakistan format (03xxxxxxxxx)')
        
        return phone

    