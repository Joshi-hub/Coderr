# Third-party
from django.contrib.auth.models import User
from django.db import models

TYPE_CHOICES = [('customer', 'Customer'), ('business', 'Business')]


class UserProfile(models.Model):
    """Stores extended profile information for every registered user."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    file = models.ImageField(upload_to='profiles/', blank=True, null=True)
    location = models.CharField(max_length=200, blank=True)
    tel = models.CharField(max_length=30, blank=True)
    description = models.TextField(blank=True)
    working_hours = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} ({self.type})'
