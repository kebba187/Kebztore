"""
Configurable flat-rate shipping (no live carrier API by design choice).

ShippingMethod  -> a carrier the store offers (Почта России, СДЭК, Boxberry, ...).
ShippingRule    -> per-method, per-region cost + a free-shipping threshold.

cost = matched rule's `cost`, unless the cart subtotal >= `free_above` (then 0).
The most specific matching rule wins (region match beats the wildcard default).
"""
from decimal import Decimal

from django.db import models
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _


class ShippingMethod(models.Model):
    CODE_CHOICES = [
        ("russian_post", "Почта России"),
        ("cdek", "СДЭК"),
        ("boxberry", "Boxberry"),
        ("yandex", "Яндекс.Доставка"),
        ("pony", "Pony Express"),
        ("dellin", "Деловые Линии"),
    ]
    code = models.CharField(max_length=32, choices=CODE_CHOICES, unique=True)
    name_ru = models.CharField(_("Название (RU)"), max_length=80)
    name_en = models.CharField(_("Название (EN)"), max_length=80, blank=True)
    eta_days_min = models.PositiveSmallIntegerField(_("Срок, дней (от)"), default=2)
    eta_days_max = models.PositiveSmallIntegerField(_("Срок, дней (до)"), default=7)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Способ доставки")
        verbose_name_plural = _("Способы доставки")
        ordering = ["name_ru"]

    @property
    def name(self):
        if get_language() == "en" and self.name_en:
            return self.name_en
        return self.name_ru

    @property
    def eta_label(self):
        return _("%(a)s–%(b)s дней") % {"a": self.eta_days_min, "b": self.eta_days_max}

    def __str__(self):
        return self.name_ru


class ShippingRule(models.Model):
    """A flat cost for a method, optionally scoped to a region (blank = default)."""

    method = models.ForeignKey(ShippingMethod, on_delete=models.CASCADE, related_name="rules")
    region = models.CharField(
        _("Регион"), max_length=120, blank=True,
        help_text=_("Пусто = правило по умолчанию для всех регионов"),
    )
    cost = models.DecimalField(_("Стоимость, ₽"), max_digits=8, decimal_places=2)
    free_above = models.DecimalField(
        _("Бесплатно при сумме от, ₽"), max_digits=10, decimal_places=2,
        null=True, blank=True,
    )

    class Meta:
        verbose_name = _("Тариф доставки")
        verbose_name_plural = _("Тарифы доставки")
        unique_together = ("method", "region")

    def cost_for(self, subtotal: Decimal) -> Decimal:
        if self.free_above is not None and subtotal >= self.free_above:
            return Decimal("0.00")
        return self.cost

    def __str__(self):
        return f"{self.method.code} / {self.region or 'default'} = {self.cost}₽"


def get_rule(method: ShippingMethod, region: str) -> "ShippingRule | None":
    """Most specific rule wins: exact region match, else the default (blank) rule."""
    region = (region or "").strip()
    if region:
        exact = method.rules.filter(region__iexact=region).first()
        if exact:
            return exact
    return method.rules.filter(region="").first()


def quote(method: ShippingMethod, region: str, subtotal: Decimal) -> Decimal:
    rule = get_rule(method, region)
    if rule is None:
        return Decimal("0.00")
    return rule.cost_for(subtotal)
