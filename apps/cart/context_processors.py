"""Expose the cart to every template (for the header badge & totals)."""
from .cart import Cart


def cart(request):
    return {"cart": Cart(request)}
