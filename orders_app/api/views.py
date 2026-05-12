# Third-party
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.mixins import UpdateModelMixin, DestroyModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

# Local
from offers_app.models import OfferDetail
from orders_app.models import Order
from profiles_app.models import UserProfile
from .permissions import IsCustomerUser, IsOrderBusinessUser, IsStaffUser
from .serializers import OrderSerializer


def _resolve_offer_detail_id(data):
    """Parse and validate offer_detail_id from request data."""
    offer_detail_id = data.get('offer_detail_id')
    if offer_detail_id is None:
        raise ValidationError({'offer_detail_id': 'This field is required.'})
    try:
        return int(offer_detail_id)
    except (ValueError, TypeError):
        raise ValidationError({'offer_detail_id': 'A valid integer is required.'})


def _create_order_snapshot(customer, detail):
    """Create an Order as an immutable snapshot of the given OfferDetail."""
    return Order.objects.create(
        customer_user=customer,
        business_user=detail.offer.user,
        title=detail.title,
        revisions=detail.revisions,
        delivery_time_in_days=detail.delivery_time_in_days,
        price=detail.price,
        features=detail.features,
        offer_type=detail.offer_type,
    )


class OrderListCreateView(ListAPIView):
    """
    GET  /api/orders/  — returns all orders the user is involved in.
    POST /api/orders/  — creates an order from an offer_detail_id (customer only).
    """

    serializer_class = OrderSerializer
    pagination_class = None

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsCustomerUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        return Order.objects.filter(Q(customer_user=user) | Q(business_user=user))

    def post(self, request, *args, **kwargs):
        self.check_permissions(request)
        offer_detail_id = _resolve_offer_detail_id(request.data)
        detail = get_object_or_404(
            OfferDetail.objects.select_related('offer__user'),
            pk=offer_detail_id,
        )
        order = _create_order_snapshot(request.user, detail)
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class OrderUpdateDeleteView(UpdateModelMixin, DestroyModelMixin, GenericAPIView):
    """
    PATCH  /api/orders/{id}/  — update status (business_user of the order only).
    DELETE /api/orders/{id}/  — delete the order (staff only).
    """

    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    http_method_names = ['patch', 'delete', 'head', 'options']

    def get_permissions(self):
        if self.request.method == 'DELETE':
            return [IsAuthenticated(), IsStaffUser()]
        return [IsAuthenticated(), IsOrderBusinessUser()]

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)


class OrderCountView(APIView):
    """GET /api/order-count/{business_user_id}/ — in_progress order count for a business user."""

    permission_classes = [IsAuthenticated]

    def get(self, request, business_user_id):
        get_object_or_404(UserProfile, user_id=business_user_id, type='business')
        count = Order.objects.filter(business_user_id=business_user_id, status='in_progress').count()
        return Response({'order_count': count})


class CompletedOrderCountView(APIView):
    """GET /api/completed-order-count/{business_user_id}/ — completed order count for a business user."""

    permission_classes = [IsAuthenticated]

    def get(self, request, business_user_id):
        get_object_or_404(UserProfile, user_id=business_user_id, type='business')
        count = Order.objects.filter(business_user_id=business_user_id, status='completed').count()
        return Response({'completed_order_count': count})
