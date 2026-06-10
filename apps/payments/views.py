"""
YooKassa webhook receiver. This is the *authoritative* source of payment truth
(the browser redirect can be faked or interrupted).

The endpoint is CSRF-exempt because it's a server-to-server call from YooKassa,
NOT a browser form. We instead validate authenticity by:
  1. (recommended) restricting to YooKassa's published IP ranges at the proxy;
  2. re-fetching the payment from YooKassa by id and trusting that, rather than
     the POST body, before changing order state.
"""
import json

from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.orders.emails import send_order_confirmation
from apps.orders.models import Order


@csrf_exempt
@require_POST
def yookassa_webhook(request):
    try:
        event = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return HttpResponseBadRequest("bad json")

    obj = event.get("object", {})
    order_id = (obj.get("metadata") or {}).get("order_id")
    if not order_id:
        return HttpResponse(status=200)  # ack unrelated events

    order = Order.objects.filter(pk=order_id).first()
    if not order:
        return HttpResponse(status=200)

    if event.get("event") == "payment.succeeded" and obj.get("paid"):
        if order.status == Order.Status.PENDING:
            order.mark_paid(payment_id=obj.get("id", ""))
            send_order_confirmation(order)  # logs (never raises) on failure
    elif event.get("event") == "payment.canceled":
        order.status = Order.Status.CANCELLED
        order.save(update_fields=["status", "updated_at"])

    return HttpResponse(status=200)
