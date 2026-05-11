from django.urls import path

from .views import OrderListCreateView, OrderUpdateDeleteView

urlpatterns = [
    path('orders/', OrderListCreateView.as_view(), name='order-list-create'),
    path('orders/<int:pk>/', OrderUpdateDeleteView.as_view(), name='order-detail'),
]
