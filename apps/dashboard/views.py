"""
Staff-only admin dashboard: create products, list products, view analytics.
Access is gated by `staff_required` (redirects non-staff to login).
"""
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.catalog.models import Product
from apps.orders.emails import send_order_shipped
from apps.orders.models import Order
from .forms import OrderStatusForm, ProductForm


def _category_page_url(product):
    """Catalog page filtered to the product's category (club / country)."""
    return f"{reverse('catalog:product_list')}?category={product.category}"

User = get_user_model()

# Orders that count as real "sales" for revenue/analytics.
SALE_STATUSES = [Order.Status.PAID, Order.Status.SHIPPED, Order.Status.DELIVERED]

# Decorator: only staff may reach the dashboard; others go to the login page.
staff_required = user_passes_test(lambda u: u.is_staff, login_url="accounts:login")


def _last_months(n):
    """Return [(year, month), ...] for the last n months, oldest first."""
    now = timezone.now()
    y, m, out = now.year, now.month, []
    for _ in range(n):
        out.append((y, m))
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return list(reversed(out))


def _aggregate_sales(orders):
    """Return (units_sold, revenue) for an iterable of orders."""
    units = sum(item.quantity for o in orders for item in o.items.all())
    revenue = sum((o.grand_total for o in orders), Decimal("0.00"))
    return units, revenue


@staff_required
def analytics(request):
    paid = list(Order.objects.filter(status__in=SALE_STATUSES).prefetch_related("items"))
    total_units, total_revenue = _aggregate_sales(paid)

    # Build monthly series for the chart (last 6 months).
    labels, sales_series, revenue_series = [], [], []
    for y, m in _last_months(6):
        bucket = [o for o in paid if o.created_at.year == y and o.created_at.month == m]
        units, revenue = _aggregate_sales(bucket)
        labels.append(f"{m:02d}.{y}")
        sales_series.append(units)
        revenue_series.append(float(revenue))

    context = {
        "active_tab": "analytics",
        "stats": {
            "users": User.objects.count(),
            "products": Product.objects.count(),
            "sales": total_units,
            "revenue": total_revenue,
        },
        "chart": {"labels": labels, "sales": sales_series, "revenue": revenue_series},
    }
    return render(request, "dashboard/analytics.html", context)


@staff_required
def product_list(request):
    products = Product.objects.select_related("team", "league").order_by("-created_at")
    return render(request, "dashboard/product_list.html",
                  {"active_tab": "products", "products": products})


@staff_required
def product_create(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            cat = product.get_category_display()
            messages.success(request, f"Товар «{product.title_ru}» создан и добавлен в категорию «{cat}».")
            # Go to the chosen category page so the admin sees it landed there.
            return redirect(_category_page_url(product))
    else:
        form = ProductForm()
    return render(request, "dashboard/product_form.html",
                  {"active_tab": "create", "form": form, "is_edit": False})


@staff_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save()
            messages.success(request, "Товар обновлён.")
            return redirect(_category_page_url(product))
    else:
        form = ProductForm(instance=product)
    return render(request, "dashboard/product_form.html",
                  {"active_tab": "products", "form": form, "is_edit": True, "product": product})


@staff_required
@require_POST
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    messages.success(request, "Товар удалён.")
    return redirect("dashboard:product_list")


# ── Orders ───────────────────────────────────────────────────────────────────
@staff_required
def order_list(request):
    orders = Order.objects.select_related("shipping_method").order_by("-created_at")
    status = request.GET.get("status")
    if status in Order.Status.values:
        orders = orders.filter(status=status)
    return render(request, "dashboard/order_list.html", {
        "active_tab": "orders", "orders": orders,
        "statuses": Order.Status.choices, "selected_status": status,
    })


@staff_required
def order_manage(request, pk):
    order = get_object_or_404(Order.objects.prefetch_related("items"), pk=pk)
    old_status = order.status  # capture before the form mutates the instance
    if request.method == "POST":
        form = OrderStatusForm(request.POST, instance=order)
        if form.is_valid():
            order = form.save()
            # Notify the customer only on the transition *into* shipped.
            if order.status == Order.Status.SHIPPED and old_status != Order.Status.SHIPPED:
                sent = send_order_shipped(order)
                messages.success(request, "Заказ отмечен «Отправлен»." +
                                 (" Покупателю отправлено письмо с трек-номером."
                                  if sent else " (письмо не отправлено — проверьте SMTP)"))
            else:
                messages.success(request, "Заказ обновлён.")
            return redirect("dashboard:order_list")
    else:
        form = OrderStatusForm(instance=order)
    return render(request, "dashboard/order_manage.html",
                  {"active_tab": "orders", "order": order, "form": form})
