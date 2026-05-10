# Third-party
from rest_framework.permissions import BasePermission


class IsCustomerUser(BasePermission):
    """Allow access only to authenticated users with a customer profile."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, 'profile')
            and request.user.profile.type == 'customer'
        )


class IsOrderBusinessUser(BasePermission):
    """Allow write access only to the business_user of the specific order."""

    def has_object_permission(self, request, view, obj):
        return obj.business_user == request.user


class IsStaffUser(BasePermission):
    """Allow access only to staff/admin users."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_staff
