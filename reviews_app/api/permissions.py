from rest_framework.permissions import BasePermission


class IsCustomerUser(BasePermission):
    """Allow access only to authenticated users with a customer profile."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, 'profile')
            and request.user.profile.type == 'customer'
        )


class IsReviewOwner(BasePermission):
    """Allow write access only to the reviewer who created the review."""

    def has_object_permission(self, request, view, obj):
        return obj.reviewer == request.user
