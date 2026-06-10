"""
YooKassa (ЮKassa) integration. The hosted payment page exposes Mir cards,
SberPay / Mir Pay, СБП (SBP/FPS) QR and YooMoney — we don't pick the method,
the customer does on YooKassa's side, so no card data ever touches our server.

Sandbox: set YOOKASSA_SHOP_ID / YOOKASSA_SECRET_KEY from the test shop.
Real keys go in `.env` only (never in code, never in git).
"""
from decimal import Decimal

from django.conf import settings
from django.urls import reverse

try:
    from yookassa import Configuration, Payment
except ImportError:  # SDK optional during tests without network
    Configuration = Payment = None


def _configure():
    if Configuration is None:
        raise RuntimeError("Установите пакет `yookassa` (pip install yookassa).")
    Configuration.account_id = settings.YOOKASSA_SHOP_ID
    Configuration.secret_key = settings.YOOKASSA_SECRET_KEY


def is_configured() -> bool:
    """True only when the SDK is installed AND sandbox/live keys are set."""
    return bool(Payment and settings.YOOKASSA_SHOP_ID and settings.YOOKASSA_SECRET_KEY)


def create_payment(order, request) -> str:
    """
    Create a YooKassa payment for `order` and return the confirmation URL the
    customer must be redirected to. The order is linked via metadata.order_id
    so the webhook can mark it paid.

    If YooKassa isn't configured (e.g. local dev without keys/SDK), we skip the
    gateway and send the customer straight to the return page; the order stays
    PENDING rather than crashing the checkout.
    """
    return_url = f"{request.build_absolute_uri(reverse('orders:payment_return'))}?order={order.id}"
    if not is_configured():
        return return_url

    _configure()

    payment = Payment.create({
        "amount": {"value": f"{order.grand_total:.2f}", "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": return_url},
        "capture": True,
        "description": f"Кебзtore — заказ №{order.id}",
        "metadata": {"order_id": str(order.id)},
        # No "payment_method_data" -> customer chooses Mir / SBP / SberPay / YooMoney.
    }, idempotency_key=f"order-{order.id}")

    order.payment_id = payment.id
    order.save(update_fields=["payment_id"])
    return payment.confirmation.confirmation_url
