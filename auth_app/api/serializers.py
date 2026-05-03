# Third-party
from django.contrib.auth.models import User
from rest_framework import serializers

# Local
from profiles_app.models import UserProfile


class RegistrationSerializer(serializers.ModelSerializer):
    """Validates and creates a new user account."""

    password = serializers.CharField(write_only=True, min_length=8)
    repeated_password = serializers.CharField(write_only=True)
    type = serializers.ChoiceField(choices=['customer', 'business'], write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'repeated_password', 'type']

    def validate_email(self, value):
        """Ensure the email address is not already in use."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value

    def validate(self, data):
        """Ensure both passwords match."""
        if data['password'] != data['repeated_password']:
            raise serializers.ValidationError({'repeated_password': 'Passwords do not match.'})
        return data

    def create(self, validated_data):
        """Create a new user and their associated profile."""
        validated_data.pop('repeated_password')
        profile_type = validated_data.pop('type')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
        )
        UserProfile.objects.create(user=user, type=profile_type)
        return user


class LoginSerializer(serializers.Serializer):
    """Validates login credentials."""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
