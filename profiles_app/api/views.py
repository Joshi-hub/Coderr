# Third-party
from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated

# Local
from profiles_app.models import UserProfile
from .permissions import IsOwnerOrReadOnly
from .serializers import UserProfileListSerializer, UserProfileSerializer


class ProfileView(RetrieveUpdateAPIView):
    """Retrieve or partially update a single user profile, looked up by user id."""

    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    http_method_names = ['get', 'patch', 'head', 'options']
    lookup_field = 'user'
    lookup_url_kwarg = 'pk'


class BusinessProfileListView(ListAPIView):
    """Return an unpaginated list of all business profiles."""

    queryset = UserProfile.objects.filter(type='business')
    serializer_class = UserProfileListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None


class CustomerProfileListView(ListAPIView):
    """Return an unpaginated list of all customer profiles."""

    queryset = UserProfile.objects.filter(type='customer')
    serializer_class = UserProfileListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
