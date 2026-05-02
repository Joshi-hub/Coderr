# Third-party
from django.contrib import admin

# Local
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin view for user profiles."""

    list_display = ['user', 'type', 'location', 'created_at']
    list_filter = ['type']
    search_fields = ['user__username', 'user__email']
