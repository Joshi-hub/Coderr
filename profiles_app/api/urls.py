from django.urls import path

from .views import BusinessProfileListView, CustomerProfileListView, ProfileView

urlpatterns = [
    path('profile/<int:pk>/', ProfileView.as_view(), name='profile-detail'),
    path('profiles/business/', BusinessProfileListView.as_view(), name='business-profiles'),
    path('profiles/customer/', CustomerProfileListView.as_view(), name='customer-profiles'),
]
