# Third-party
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrReadOnly(BasePermission):
    """Allow read access to any authenticated user; write only to the profile owner."""

    def has_object_permission(self, request, view, obj):
        """Permit GET/HEAD/OPTIONS for all; PATCH only for the profile owner."""
        if request.method in SAFE_METHODS:
            return True
        return obj.user == request.user
