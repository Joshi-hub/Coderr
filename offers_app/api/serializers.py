# Third-party
from rest_framework import serializers

# Local
from offers_app.models import Offer, OfferDetail


def _apply_detail_update(instance, detail_data):
    """Update a single OfferDetail matched by offer_type; silently skips unknown types."""
    offer_type = detail_data.get('offer_type')
    try:
        detail = instance.details.get(offer_type=offer_type)
        for attr, value in detail_data.items():
            setattr(detail, attr, value)
        detail.save()
    except OfferDetail.DoesNotExist:
        pass


class OfferDetailFullSerializer(serializers.ModelSerializer):
    """Full detail fields — used for POST/PATCH bodies, responses, and GET /offerdetails/{id}/."""

    class Meta:
        model = OfferDetail
        fields = ['id', 'title', 'revisions', 'delivery_time_in_days', 'price', 'features', 'offer_type']
        read_only_fields = ['id']


class OfferDetailURLSerializer(serializers.ModelSerializer):
    """Compact detail — id + absolute URL — used in list and single-offer GET responses."""

    url = serializers.SerializerMethodField()

    class Meta:
        model = OfferDetail
        fields = ['id', 'url']

    def get_url(self, obj):
        request = self.context.get('request')
        path = f'/api/offerdetails/{obj.id}/'
        return request.build_absolute_uri(path) if request else path


class OfferListSerializer(serializers.ModelSerializer):
    """Read-only serializer for GET /api/offers/ — includes user_details, min_price, min_delivery_time."""

    details = OfferDetailURLSerializer(many=True, read_only=True)
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    min_delivery_time = serializers.IntegerField(read_only=True)
    user_details = serializers.SerializerMethodField()

    class Meta:
        model = Offer
        fields = [
            'id', 'user', 'title', 'image', 'description',
            'created_at', 'updated_at', 'details',
            'min_price', 'min_delivery_time', 'user_details',
        ]

    def get_user_details(self, obj):
        profile = getattr(obj.user, 'profile', None)
        return {
            'first_name': profile.first_name if profile else '',
            'last_name': profile.last_name if profile else '',
            'username': obj.user.username,
        }


class OfferRetrieveSerializer(serializers.ModelSerializer):
    """Read-only serializer for GET /api/offers/{id}/ — URL-based details, min_price, min_delivery_time."""

    details = OfferDetailURLSerializer(many=True, read_only=True)
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    min_delivery_time = serializers.IntegerField(read_only=True)

    class Meta:
        model = Offer
        fields = [
            'id', 'user', 'title', 'image', 'description',
            'created_at', 'updated_at', 'details',
            'min_price', 'min_delivery_time',
        ]


class OfferCreateSerializer(serializers.ModelSerializer):
    """Write + read serializer for POST /api/offers/ — enforces exactly 3 typed details."""

    details = OfferDetailFullSerializer(many=True)

    class Meta:
        model = Offer
        fields = ['id', 'title', 'image', 'description', 'details']
        read_only_fields = ['id']

    def validate_details(self, value):
        if len(value) != 3:
            raise serializers.ValidationError('An offer must have exactly 3 details.')
        types = {d['offer_type'] for d in value}
        if types != {'basic', 'standard', 'premium'}:
            raise serializers.ValidationError(
                'Details must include exactly one basic, one standard, and one premium entry.'
            )
        return value

    def create(self, validated_data):
        details_data = validated_data.pop('details')
        offer = Offer.objects.create(**validated_data)
        for detail_data in details_data:
            OfferDetail.objects.create(offer=offer, **detail_data)
        return offer


class OfferPatchSerializer(serializers.ModelSerializer):
    """Write + read serializer for PATCH /api/offers/{id}/ — updates details by offer_type."""

    details = OfferDetailFullSerializer(many=True, required=False)

    class Meta:
        model = Offer
        fields = ['id', 'title', 'image', 'description', 'details']
        read_only_fields = ['id']

    def validate_details(self, value):
        for detail in value:
            if 'offer_type' not in detail:
                raise serializers.ValidationError('Each detail must include offer_type.')
        return value

    def update(self, instance, validated_data):
        details_data = validated_data.pop('details', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if details_data:
            for detail_data in details_data:
                _apply_detail_update(instance, detail_data)
        return instance
