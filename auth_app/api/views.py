# Third-party
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

# Local
from .serializers import LoginSerializer, RegistrationSerializer


def _build_auth_response(user, token):
    """Return the standard auth payload shared by login and registration."""
    return {
        'token': token.key,
        'username': user.username,
        'email': user.email,
        'user_id': user.id,
    }


class RegistrationView(APIView):
    """Creates a new user account and returns an auth token."""

    permission_classes = [AllowAny]
    serializer_class = RegistrationSerializer

    def post(self, request):
        """Validate input, create user, and return token."""
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response(_build_auth_response(user, token), status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """Authenticates an existing user and returns an auth token."""

    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        """Validate credentials and return token if correct."""
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user = authenticate(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password'],
        )
        if not user:
            return Response({'detail': 'Invalid credentials.'}, status=status.HTTP_400_BAD_REQUEST)
        token, _ = Token.objects.get_or_create(user=user)
        return Response(_build_auth_response(user, token))
