"""
Static informational pages + the 152-ФЗ cookie-consent endpoint.

`save_consent` records the visitor's cookie choices in a first-party cookie.
The choice covers three categories: technical (always on), analytical,
advertising — matching the consent banner in the base template.
"""
import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST


def personal_data(request):
    """«Персональные данные» — what we collect, why, how stored, user rights."""
    return render(request, "pages/personal_data.html")


def offer(request):
    return render(request, "pages/offer.html")


@require_POST
def save_consent(request):
    """Persist cookie-category consent for ~180 days (CSRF-protected POST)."""
    try:
        prefs = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        prefs = {}
    value = json.dumps({
        "technical": True,  # always required for the site to work
        "analytical": bool(prefs.get("analytical")),
        "advertising": bool(prefs.get("advertising")),
    })
    response = JsonResponse({"ok": True})
    response.set_cookie(
        "cookie_consent", value, max_age=60 * 60 * 24 * 180,
        samesite="Lax", secure=not request.scheme == "http",
    )
    return response
