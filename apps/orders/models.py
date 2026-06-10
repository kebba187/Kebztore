"""
Orders. We snapshot the price and title onto each OrderItem so historical
orders stay correct even if the product later changes or is deleted.

PII note (152-ФЗ): we store only fulfilment data (name, phone, address).
We never store card numbers — payment is handled by YooKassa; we keep only
its opaque payment id and status.
"""
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.catalog.models import Product
from apps.shipping.models import ShippingMethod


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("Ожидает оплаты")
        PAID = "paid", _("Оплачен")
        SHIPPED = "shipped", _("Отправлен")
        DELIVERED = "delivered", _("Доставлен")
        CANCELLED = "cancelled", _("Отменён")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="orders",
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)

    # Customer / fulfilment PII
    full_name = models.CharField(_("ФИО"), max_length=150)
    email = models.EmailField(_("Email"))
    phone = models.CharField(_("Телефон"), max_length=20)

    # Shipping address (Russia)
    region = models.CharField(_("Регион"), max_length=120)
    city = models.CharField(_("Город"), max_length=120)
    street = models.CharField(_("Улица"), max_length=200)
    building = models.CharField(_("Дом"), max_length=30)
    apartment = models.CharField(_("Квартира"), max_length=30, blank=True)
    postal_code = models.CharField(_("Индекс"), max_length=10)

    shipping_method = models.ForeignKey(ShippingMethod, on_delete=models.PROTECT, null=True)
    shipping_cost = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    tracking_number = models.CharField(_("Трек-номер"), max_length=64, blank=True)

    # Payment (YooKassa) — no card data, just the gateway reference.
    payment_id = models.CharField(max_length=64, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Заказ")
        verbose_name_plural = _("Заказы")
        ordering = ["-created_at"]

    @property
    def items_total(self) -> Decimal:
        return sum((i.line_total for i in self.items.all()), Decimal("0.00"))

    @property
    def grand_total(self) -> Decimal:
        return self.items_total + self.shipping_cost

    def mark_paid(self, payment_id="", when=None):
        from django.utils import timezone
        self.status = self.Status.PAID
        self.payment_id = payment_id or self.payment_id
        self.paid_at = when or timezone.now()
        self.save(update_fields=["status", "payment_id", "paid_at", "updated_at"])

    def __str__(self):
        return f"Заказ #{self.pk} ({self.get_status_display()})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=200)        # snapshot
    size = models.CharField(max_length=4)           # snapshot
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)  # snapshot
    quantity = models.PositiveIntegerField(default=1)

    @property
    def line_total(self) -> Decimal:
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.title} x{self.quantity}"
