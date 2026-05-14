# Third-party
from rest_framework import status
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.mixins import UpdateModelMixin, DestroyModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# Local
from reviews_app.models import Review
from .permissions import IsCustomerUser, IsReviewOwner
from .serializers import ReviewSerializer, ReviewCreateSerializer, ReviewPatchSerializer


def _apply_review_filters(queryset, params):
    """Apply business_user_id, reviewer_id, and ordering filters to the queryset."""
    business_user_id = params.get('business_user_id')
    if business_user_id:
        queryset = queryset.filter(business_user_id=business_user_id)
    reviewer_id = params.get('reviewer_id')
    if reviewer_id:
        queryset = queryset.filter(reviewer_id=reviewer_id)
    ordering = params.get('ordering')
    if ordering in {'updated_at', '-updated_at', 'rating', '-rating'}:
        queryset = queryset.order_by(ordering)
    return queryset


class ReviewListCreateView(ListAPIView):
    """
    GET  /api/reviews/  — list all reviews (filterable, orderable).
    POST /api/reviews/  — create a review (customer only, one per business user).
    """

    serializer_class = ReviewSerializer
    pagination_class = None

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsCustomerUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return _apply_review_filters(Review.objects.all(), self.request.query_params)

    def post(self, request, *args, **kwargs):
        self.check_permissions(request)
        serializer = ReviewCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)


class ReviewUpdateDeleteView(UpdateModelMixin, DestroyModelMixin, GenericAPIView):
    """
    PATCH  /api/reviews/{id}/  — update rating and description (reviewer only).
    DELETE /api/reviews/{id}/  — delete review (reviewer only), returns 204.
    """

    queryset = Review.objects.all()
    serializer_class = ReviewPatchSerializer
    permission_classes = [IsAuthenticated, IsReviewOwner]
    http_method_names = ['patch', 'delete', 'head', 'options']

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)
