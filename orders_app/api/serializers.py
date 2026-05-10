# Third-party
from rest_framework import serializers

# Local
from orders_app.models import Order


class OrderSerializer(serializers.ModelSerializer):
    """
    Full order serializer.
    Only 'status' is writable — all other fields are set at creation time and are read-only.
    """

    class Meta:
        model = Order
        fields = [
            'id', 'customer_user', 'business_user', 'title', 'revisions',
            'delivery_time_in_days', 'price', 'features', 'offer_type',
            'status', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'customer_user', 'business_user', 'title', 'revisions',
            'delivery_time_in_days', 'price', 'features', 'offer_type',
            'created_at', 'updated_at',
        ]
