from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, UserProfile
from django.contrib.auth.password_validation import validate_password






class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'date_joined',
                  'is_email_verified']
        read_only_fields = ['id', 'is_email_verified', 'date_joined']


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'
        read_only_fields = ['user']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['email', 'password', 'password2', 'first_name', 'last_name']

    def validate(self, attrs):
        if attrs['password'] != attrs['passowrd2']:
            raise serializers.ValidationError({"password: Password fields didn't match."})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user
    

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data):
        user = authenticate(**data)
        if user and user.is_active:
            return user
        return serializers.ValidationError('Invalid credentials')    