"""
Order creation lives here (not in the view) so it can be unit-tested directly
and reused. Runs in a transaction; snapshots prices; decrements stock atomically.
"""
from django.db import transaction

from apps.shipping.models import quote
from .models import Order, OrderItem


@transaction.atomic
def create_order_from_cart(cart, form_order: Order) -> Order:
    """
    `form_order` is an unsaved Order built by CheckoutForm.save(commit=False).
    We attach the user, compute shipping, persist items, and decrement stock.
    """
    if cart.is_empty:
        raise ValueError("Cart is empty")

    subtotal = cart.subtotal
    form_order.shipping_cost = quote(form_order.shipping_method, form_order.region, subtotal)
    form_order.save()

    items = []
    for entry in cart:
        product = entry["product"]
        qty = entry["quantity"]
        # Lock the row to avoid overselling under concurrency.
        locked = product.__class__.objects.select_for_update().get(pk=product.pk)
        if locked.stock < qty:
            raise ValueError(f"Недостаточно товара: {locked.title_ru}")
        locked.stock -= qty
        locked.save(update_fields=["stock"])
        items.append(OrderItem(
            order=form_order, product=product, title=product.title_ru,
            size=product.size, unit_price=product.price, quantity=qty,
        ))
    OrderItem.objects.bulk_create(items)
    cart.clear()
    return form_order
