"""
Transactional email for orders. Sending must never break the caller (e.g. the
YooKassa webhook must still return 200 even if SMTP is down), so failures are
logged, not raised.
"""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def _send(order, subject, template_base, extra_context=None) -> bool:
    """Render `<template_base>.txt/.html` and email the customer. Never raises."""
    if not order.email:
        return False
    context = {"order": order, "items": list(order.items.all()), **(extra_context or {})}
    text_body = render_to_string(f"{template_base}.txt", context)
    html_body = render_to_string(f"{template_base}.html", context)
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "noreply@kebztore.ru"
    try:
        msg = EmailMultiAlternatives(subject, text_body, from_email, [order.email])
        msg.attach_alternative(html_body, "text/html")
        msg.send()
        return True
    except Exception:  # noqa: BLE001 - never let email break order processing
        logger.exception("Email '%s' failed for order #%s", subject, order.id)
        return False


def send_order_confirmation(order) -> bool:
    """Send the 'order paid' confirmation to the customer."""
    return _send(order, f"Кебзtore — заказ №{order.id} оплачен",
                 "orders/email/order_confirmation")


def send_order_shipped(order) -> bool:
    """Send the 'order shipped' notice with the tracking number."""
    return _send(order, f"Кебзtore — заказ №{order.id} отправлен",
                 "orders/email/order_shipped")
