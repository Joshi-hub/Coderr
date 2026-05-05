# Third-party
from django.contrib.auth.models import User
from rest_framework import serializers

# Local
from profiles_app.models import UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    """Detail serializer for GET and PATCH — includes writable email and created_at."""

    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', required=False)

    class Meta:
        model = UserProfile
        fields = [
            'user', 'username', 'first_name', 'last_name',
            'file', 'location', 'tel', 'description',
            'working_hours', 'type', 'email', 'created_at',
        ]
        read_only_fields = ['user', 'type', 'created_at']

    def validate_email(self, value):
        """Ensure the new email is not already in use by another user."""
        current_user = self.instance.user if self.instance else None
        qs = User.objects.filter(email=value)
        if current_user:
            qs = qs.exclude(pk=current_user.pk)
        if qs.exists():
            raise serializers.ValidationError('This email is already in use.')
        return value

    def update(self, instance, validated_data):
        """Update profile fields and propagate email changes to the User model."""
        user_data = validated_data.pop('user', {})
        if 'email' in user_data:
            instance.user.email = user_data['email']
            instance.user.save()
        return super().update(instance, validated_data)


class UserProfileListSerializer(serializers.ModelSerializer):
    """List serializer — excludes email and created_at."""

    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            'user', 'username', 'first_name', 'last_name',
            'file', 'location', 'tel', 'description',
            'working_hours', 'type',
        ]
        read_only_fields = ['user', 'type']
