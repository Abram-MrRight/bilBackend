from rest_framework import serializers

from django.conf import settings
from .models import Announcement, ChargeRule, Country, Currency, Transaction, UploadProofStep, User, Proof, Agent, CompanyInfo, StatusUpdate, WhatsAppContact
from django.contrib.auth import authenticate
from .models import Proof, ProofRead, User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'fullname', 'email', 'phone_number', 'role', 'location', 'profile_image']


# Registration Serializer

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['fullname', 'email', 'phone_number', 'password', 'location']

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            fullname=validated_data['fullname'],
            password=validated_data['password'],
            phone_number=validated_data.get('phone_number'),
            location=validated_data.get('location'),
            role='client'
        )
        return user


# Login Serializer

class LoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        phone_number = data.get('phone_number', '').lstrip('+')  # remove +
        password = data.get('password')

        try:
            user = User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            raise serializers.ValidationError("Phone number not found")

        if not user.check_password(password):
            raise serializers.ValidationError("Incorrect password")

        data['user'] = user
        return data

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['fullname', 'email', 'phone_number', 'location', 'profile_image', 'role']
        extra_kwargs = {
            'role': {'required': False},
            'profile_image': {'required': False},
        }

    def update(self, instance, validated_data):
        request_user = self.context['request'].user

        # Only super_admin can change role
        if 'role' in validated_data and request_user.role != 'super_admin':
            validated_data.pop('role')

        # Handle profile image upload
        profile_image = validated_data.pop('profile_image', None)
        if profile_image:
            instance.profile_image = profile_image

        return super().update(instance, validated_data)




class ProofSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    
    # Add this so the API can accept country_id on POST
    country_id = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(),
        write_only=True,
        source='country'  # maps country_id to the country foreign key
    )
    
    # Optional: for GET, serialize country as nested object
    country = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Proof
        fields = [
            'id', 'user', 'user_id', 'image', 'sender_name', 'receiver_name','receiver_email',
            'receiver_contact', 'amount', 'currency', 'country', 'country_id', 
            'status', 'status_note', 'notes', 'created_at', 'updated_at'
        ]

class ProofStatusUpdateSerializer(serializers.ModelSerializer):
    charge_rule = serializers.PrimaryKeyRelatedField(
        queryset=ChargeRule.objects.all(),
        required=False, allow_null=True
    )

    class Meta:
        model = Proof
        fields = ['status', 'status_note', 'charge_rule']


class ProofReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProofRead
        fields = ['proof', 'user', 'is_read', 'read_at']

class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ['id', 'name', 'code']

class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ['id', 'name', 'code', 'symbol']

class ChargeRuleSerializer(serializers.ModelSerializer):
    country_name = serializers.CharField(source='country.name', read_only=True)
    currency = serializers.CharField(source='currency.code', read_only=True)

    class Meta:
        model = ChargeRule
        fields = ['id', 'country_name', 'currency', 'min_amount', 'max_amount', 'charge_amount', 'charge_percentage']

class AnnouncementSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = ['id', 'title', 'description', 'image', 'image_url', 'created_by', 'is_active', 'start_at', 'end_at', 'created_at', 'updated_at']
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'image_url']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image:
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None
    
class AgentSerializer(serializers.ModelSerializer):
    full_logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Agent
        fields = ['id', 'name', 'account_name', 'phone', 'email', 'logo_image', 'notes', 'full_logo_url']

    def get_full_logo_url(self, obj):
        if obj.logo_image:
            return f"{settings.MEDIA_URL}{obj.logo_image}"
        return f"{settings.STATIC_URL}images/logo.png"
    

class CompanyInfoSerializer(serializers.ModelSerializer):
    full_logo_url = serializers.SerializerMethodField()

    class Meta:
        model = CompanyInfo
        fields = ['id', 'type', 'title', 'content', 'icon', 'color', 'logo_image', 'full_logo_url']

    def get_full_logo_url(self, obj):
        if obj.logo_image:
            return f"{settings.MEDIA_URL}{obj.logo_image.name}"
        return None
    
class UploadProofStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadProofStep
        fields = ['step_number', 'title', 'description', 'icon', 'color']

class WhatsAppContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsAppContact
        fields = ['id', 'name', 'phone_number', 'created_at', 'updated_at']

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'