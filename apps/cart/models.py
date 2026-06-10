"""
Persistent cart line for logged-in users (so the cart survives across sessions
and devices). Anonymous carts live only in the session — see cart.py.
"""
from django.conf import settings
from django.db import models

from apps.catalog.models import Product


class SavedCartItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("user", "product")

    def __str__(self):
        return f"{self.user_id}: {self.product_id} x{self.quantity}"
