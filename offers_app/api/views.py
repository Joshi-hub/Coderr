# Third-party
from django.db.models import Min, Q
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated

# Local
from offers_app.models import Offer, OfferDetail
from .permissions import IsBusinessUser, IsOfferOwner
from .serializers import (
    OfferListSerializer, OfferCreateSerializer,
    OfferRetrieveSerializer, OfferPatchSerializer,
    OfferDetailFullSerializer,
)


class OfferPagination(PageNumberPagination):
    page_size = 6
    page_size_query_param = 'page_size'
    max_page_size = 100


def _base_offer_queryset():
    return (
        Offer.objects
        .select_related('user__profile')
        .prefetch_related('details')
        .annotate(
            min_price=Min('details__price'),
            min_delivery_time=Min('details__delivery_time_in_days'),
        )
        .order_by('-updated_at')
    )


def _apply_creator_filter(queryset, params):
    creator_id = params.get('creator_id')
    return queryset.filter(user_id=creator_id) if creator_id else queryset


def _apply_price_filter(queryset, params):
    min_price = params.get('min_price')
    if not min_price:
        return queryset
    try:
        return queryset.filter(min_price__gte=float(min_price))
    except ValueError:
        return queryset


def _apply_delivery_filter(queryset, params):
    max_delivery = params.get('max_delivery_time')
    if not max_delivery:
        return queryset
    try:
        return queryset.filter(min_delivery_time__lte=int(max_delivery))
    except ValueError:
        raise ValidationError({'max_delivery_time': 'Must be an integer.'})


def _apply_search_filter(queryset, params):
    search = params.get('search')
    if not search:
        return queryset
    return queryset.filter(Q(title__icontains=search) | Q(description__icontains=search))


def _apply_offer_ordering(queryset, params):
    ordering = params.get('ordering')
    if ordering in {'updated_at', '-updated_at', 'min_price', '-min_price'}:
        return queryset.order_by(ordering)
    return queryset


class OfferListCreateView(ListCreateAPIView):
    """
    GET  /api/offers/  — list all offers (filterable, orderable, paginated).
    POST /api/offers/  — create an offer (business user only).
    """

    pagination_class = OfferPagination

    def get_queryset(self):
        params = self.request.query_params
        qs = _base_offer_queryset()
        qs = _apply_creator_filter(qs, params)
        qs = _apply_price_filter(qs, params)
        qs = _apply_delivery_filter(qs, params)
        qs = _apply_search_filter(qs, params)
        return _apply_offer_ordering(qs, params)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return OfferCreateSerializer
        return OfferListSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsBusinessUser()]
        return [AllowAny()]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class OfferRetrieveUpdateDestroyView(RetrieveUpdateDestroyAPIView):
    """
    GET    /api/offers/{id}/ — retrieve a single offer.
    PATCH  /api/offers/{id}/ — update title, description, or details (owner only).
    DELETE /api/offers/{id}/ — delete an offer (owner only).
    """

    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return _base_offer_queryset()

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return OfferPatchSerializer
        return OfferRetrieveSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsOfferOwner()]


class OfferDetailRetrieveView(RetrieveAPIView):
    """GET /api/offerdetails/{id}/ — retrieve a single offer detail."""

    queryset = OfferDetail.objects.select_related('offer')
    serializer_class = OfferDetailFullSerializer
    permission_classes = [IsAuthenticated]
