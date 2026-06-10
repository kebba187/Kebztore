"""Checkout form — server-side validation is authoritative."""
import re

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.shipping.models import ShippingMethod
from .models import Order

PHONE_RE = re.compile(r"^\+?[0-9\s\-()]{10,20}$")
POSTAL_RE = re.compile(r"^\d{6}$")  # РФ postal index is 6 digits


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            "full_name", "email", "phone",
            "region", "city", "street", "building", "apartment", "postal_code",
            "shipping_method",
        ]
        widgets = {
            "shipping_method": forms.RadioSelect,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["shipping_method"].queryset = ShippingMethod.objects.filter(is_active=True)
        self.fields["apartment"].required = False

    def clean_phone(self):
        phone = self.cleaned_data["phone"]
        if not PHONE_RE.match(phone):
            raise forms.ValidationError(_("Введите корректный номер телефона."))
        return phone

    def clean_postal_code(self):
        code = self.cleaned_data["postal_code"]
        if not POSTAL_RE.match(code):
            raise forms.ValidationError(_("Почтовый индекс РФ состоит из 6 цифр."))
        return code
