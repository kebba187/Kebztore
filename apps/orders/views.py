from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _

from apps.cart.cart import Cart
from apps.payments.yookassa_gateway import create_payment
from .forms import CheckoutForm
from .models import Order
from .services import create_order_from_cart


def checkout(request):
    cart = Cart(request)
    if cart.is_empty:
        messages.info(request, _("Корзина пуста."))
        return redirect("catalog:product_list")

    initial = {}
    if request.user.is_authenticated:
        initial = {"full_name": request.user.full_name,
                   "email": request.user.email, "phone": request.user.phone}

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            if request.user.is_authenticated:
                order.user = request.user
            try:
                order = create_order_from_cart(cart, order)
            except ValueError as exc:
                messages.error(request, str(exc))
                return redirect("cart:detail")

            # Remember ownership so a guest (no account) can view *their* order
            # without exposing everyone else's by guessing IDs.
            owned = request.session.setdefault("my_orders", [])
            if order.id not in owned:
                owned.append(order.id)
                request.session.modified = True

            # Hand off to YooKassa; redirect to the confirmation page. Never let a
            # gateway hiccup 500 the checkout after the order is already saved.
            try:
                confirmation_url = create_payment(order, request)
            except Exception:
                messages.warning(request, _("Заказ создан, но платёж пока недоступен."))
                return redirect(f"{reverse('orders:payment_return')}?order={order.id}")
            return redirect(confirmation_url)
    else:
        form = CheckoutForm(initial=initial)

    return render(request, "orders/checkout.html", {"form": form, "cart": cart})


def _can_view_order(request, order) -> bool:
    """Staff, the authenticated owner, or a guest who created it this session.
    Guest orders (order.user is None) are gated by the session list so IDs
    can't be enumerated to read strangers' PII (152-ФЗ)."""
    if request.user.is_staff:
        return True
    if order.user_id and order.user_id == getattr(request.user, "id", None):
        return True
    return order.id in request.session.get("my_orders", [])


def order_detail(request, pk):
    order = get_object_or_404(Order.objects.prefetch_related("items"), pk=pk)
    if not _can_view_order(request, order):
        return redirect("catalog:product_list")
    return render(request, "orders/detail.html", {"order": order})


def payment_return(request):
    """User comes back from YooKassa. Final status is confirmed via webhook,
    but we show a friendly summary here."""
    order_id = request.GET.get("order")
    order = None
    if order_id:
        order = get_object_or_404(Order, pk=order_id)
        if not _can_view_order(request, order):
            order = None  # don't reveal anything about someone else's order
    return render(request, "orders/payment_return.html", {"order": order})
