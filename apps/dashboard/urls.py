from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.analytics, name="analytics"),
    path("products/", views.product_list, name="product_list"),
    path("products/new/", views.product_create, name="product_create"),
    path("products/<int:pk>/edit/", views.product_edit, name="product_edit"),
    path("products/<int:pk>/delete/", views.product_delete, name="product_delete"),
    path("orders/", views.order_list, name="order_list"),
    path("orders/<int:pk>/", views.order_manage, name="order_manage"),
]
