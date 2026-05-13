# Third-party
from rest_framework import serializers

# Local
from profiles_app.models import UserProfile
from reviews_app.models import Review


class ReviewSerializer(serializers.ModelSerializer):
    """Read-only serializer — used for list responses and as the response body after write operations."""

    class Meta:
        model = Review
        fields = ['id', 'business_user', 'reviewer', 'rating', 'description', 'created_at', 'updated_at']


class ReviewCreateSerializer(serializers.ModelSerializer):
    """Write serializer for POST /api/reviews/ — reviewer is set from the request user."""

    class Meta:
        model = Review
        fields = ['id', 'business_user', 'reviewer', 'rating', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'reviewer', 'created_at', 'updated_at']

    def validate_business_user(self, value):
        if not UserProfile.objects.filter(user=value, type='business').exists():
            raise serializers.ValidationError('The specified user is not a business user.')
        return value

    def validate(self, data):
        reviewer = self.context['request'].user
        business_user = data.get('business_user')
        if business_user and Review.objects.filter(reviewer=reviewer, business_user=business_user).exists():
            raise serializers.ValidationError('You have already reviewed this business user.')
        return data

    def create(self, validated_data):
        return Review.objects.create(reviewer=self.context['request'].user, **validated_data)


class ReviewPatchSerializer(serializers.ModelSerializer):
    """Write serializer for PATCH /api/reviews/{id}/ — only rating and description are editable."""

    class Meta:
        model = Review
        fields = ['id', 'business_user', 'reviewer', 'rating', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'business_user', 'reviewer', 'created_at', 'updated_at']
