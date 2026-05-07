# Third-party
from rest_framework.permissions import BasePermission


class IsBusinessUser(BasePermission):
    """Allow access only to authenticated users with a business profile."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, 'profile')
            and request.user.profile.type == 'business'
        )


class IsOfferOwner(BasePermission):
    """Allow write access only to the offer creator."""

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user
