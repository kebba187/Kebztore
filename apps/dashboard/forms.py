"""
Product create/edit form for the staff dashboard (server-side validated).

Team & league are entered as free text (not dropdowns) and auto-created on save.
They apply ONLY to club jerseys — for country (national-team) jerseys the fields
are hidden in the UI and ignored/cleared on the server.
"""
from django import forms
from django.utils.translation import gettext_lazy as _

from apps.catalog.models import Category, League, Product, ProductImage, Team
from apps.orders.models import Order


class OrderStatusForm(forms.ModelForm):
    """Staff updates order status and tracking number. Shipping requires a track №."""

    class Meta:
        model = Order
        fields = ["status", "tracking_number"]

    def clean(self):
        data = super().clean()
        if data.get("status") == Order.Status.SHIPPED and not (data.get("tracking_number") or "").strip():
            self.add_error("tracking_number",
                           _("Укажите трек-номер при отметке «Отправлен»."))
        return data


class ProductForm(forms.ModelForm):
    # Typed by hand instead of selecting existing rows.
    team_name = forms.CharField(
        label=_("Команда (клуб)"), max_length=120, required=False,
        widget=forms.TextInput(attrs={"placeholder": _("например, Зенит")}),
    )
    league_name = forms.CharField(
        label=_("Лига"), max_length=120, required=False,
        widget=forms.TextInput(attrs={"placeholder": _("например, РПЛ")}),
    )
    image = forms.ImageField(label=_("Изображение"), required=False)

    # Render order (mirrors the create-product card layout).
    field_order = [
        "category", "title_ru", "title_en",
        "team_name", "league_name", "country_ru", "country_en",
        "description_ru", "description_en", "price", "stock", "size", "season",
        "is_active", "image",
    ]

    class Meta:
        model = Product
        # team / league handled manually via the *_name fields above.
        fields = [
            "category", "title_ru", "title_en",
            "country_ru", "country_en",
            "season", "size",
            "description_ru", "description_en", "price", "stock", "is_active",
        ]
        widgets = {
            "description_ru": forms.Textarea(attrs={"rows": 3}),
            "description_en": forms.Textarea(attrs={"rows": 3}),
            "country_ru": forms.TextInput(attrs={"placeholder": _("например, Россия")}),
            "country_en": forms.TextInput(attrs={"placeholder": _("e.g. Russia")}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Prefill the text fields when editing an existing club jersey.
        if self.instance and self.instance.pk:
            if self.instance.team:
                self.fields["team_name"].initial = self.instance.team.name_ru
            if self.instance.league:
                self.fields["league_name"].initial = self.instance.league.name_ru

    def clean_price(self):
        price = self.cleaned_data["price"]
        if price <= 0:
            raise forms.ValidationError(_("Цена должна быть больше нуля."))
        return price

    def clean(self):
        data = super().clean()
        category = data.get("category")
        if category == Category.CLUB:
            # Club jerseys MUST have a team and a league.
            if not (data.get("team_name") or "").strip():
                self.add_error("team_name", _("Укажите команду для клубной джерси."))
            if not (data.get("league_name") or "").strip():
                self.add_error("league_name", _("Укажите лигу для клубной джерси."))
        elif category == Category.COUNTRY:
            # Country jerseys MUST name the national team / country.
            if not (data.get("country_ru") or "").strip():
                self.add_error("country_ru", _("Укажите сборную/страну."))
        return data

    def save(self, commit=True):
        product = super().save(commit=False)
        category = self.cleaned_data.get("category")

        if category == Category.CLUB:
            league_name = self.cleaned_data["league_name"].strip()
            team_name = self.cleaned_data["team_name"].strip()
            league, _created = League.objects.get_or_create(name_ru=league_name)
            team, _created = Team.objects.get_or_create(
                name_ru=team_name, defaults={"league": league})
            product.league = league
            product.team = team
            product.country_ru = ""   # not applicable to club jerseys
            product.country_en = ""
        else:
            # Country jerseys: no club / league; keep the country name.
            product.team = None
            product.league = None

        if commit:
            product.save()
            image = self.cleaned_data.get("image")
            if image:
                ProductImage.objects.create(product=product, image=image)
        return product
