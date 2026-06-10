from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("checkout/", views.checkout, name="checkout"),
    path("payment/return/", views.payment_return, name="payment_return"),
    path("<int:pk>/", views.order_detail, name="detail"),
]
