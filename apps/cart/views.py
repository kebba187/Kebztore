"""
Cart endpoints. Mutating actions are POST-only and CSRF-protected (the JS in
static/js/main.js sends the X-CSRFToken header). They return JSON so the page
can update the cart badge without a full reload.
"""
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.catalog.models import Product
from apps.shipping.models import ShippingMethod, quote
from .cart import Cart


def _parse_qty(request, default=1):
    """Safely read a quantity from POST (a malformed value must not 500)."""
    try:
        return int(request.POST.get("quantity", default))
    except (TypeError, ValueError):
        return default


def _cart_payload(cart: Cart):
    return {
        "count": len(cart),
        "subtotal": str(cart.subtotal),
        "items": [
            {"id": i["product"].id, "title": i["product"].title,
             "quantity": i["quantity"], "line_total": str(i["line_total"])}
            for i in cart
        ],
    }


@require_POST
def add(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    if not product.in_stock:
        return JsonResponse({"error": "Нет в наличии"}, status=400)
    cart = Cart(request)
    cart.add(product, _parse_qty(request))
    return JsonResponse(_cart_payload(cart))


@require_POST
def update(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    quantity = _parse_qty(request)
    cart = Cart(request)
    if quantity <= 0:
        cart.remove(product)
    else:
        cart.add(product, quantity, replace=True)
    return JsonResponse(_cart_payload(cart))


@require_POST
def remove(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = Cart(request)
    cart.remove(product)
    return JsonResponse(_cart_payload(cart))


def detail(request):
    """Cart page with a live delivery-cost estimate (cheapest active method)."""
    cart = Cart(request)
    methods = ShippingMethod.objects.filter(is_active=True).prefetch_related("rules")
    estimates = [
        {"method": m, "cost": quote(m, request.GET.get("region", ""), cart.subtotal)}
        for m in methods
    ]
    return render(request, "cart/detail.html", {"cart": cart, "estimates": estimates})
