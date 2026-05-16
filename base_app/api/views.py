# Third-party
from django.apps import apps
from django.db.models import Avg
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

# Local
from profiles_app.models import UserProfile


def _get_review_stats():
    """Return (review_count, average_rating) or safe defaults if reviews_app is unavailable."""
    try:
        Review = apps.get_model('reviews_app', 'Review')
        review_count = Review.objects.count()
        avg = Review.objects.aggregate(avg=Avg('rating'))['avg']
        return review_count, round(avg, 1) if avg is not None else 0.0
    except LookupError:
        return 0, 0.0


def _get_offer_count():
    """Return total offer count, or 0 if offers_app is unavailable."""
    try:
        Offer = apps.get_model('offers_app', 'Offer')
        return Offer.objects.count()
    except LookupError:
        return 0


class BaseInfoView(APIView):
    """GET /api/base-info/ — public platform statistics, no authentication required."""

    permission_classes = [AllowAny]

    def get(self, request):
        business_profile_count = UserProfile.objects.filter(type='business').count()
        review_count, average_rating = _get_review_stats()
        offer_count = _get_offer_count()
        return Response({
            'review_count': review_count,
            'average_rating': average_rating,
            'business_profile_count': business_profile_count,
            'offer_count': offer_count,
        })
