"""
Catalog domain. Bilingual fields use the `_ru` / `_en` suffix pattern.
A helper `localized()` picks the active language with RU as the fallback,
matching the "Russian default, English fallback" requirement.
The design is generic enough to add more product categories later.
"""
from decimal import Decimal

from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _


def pick(ru: str, en: str) -> str:
    """Return EN only when the active language is English AND it's filled."""
    if get_language() == "en" and en:
        return en
    return ru or en


# Cyrillic -> Latin so slugify() of a Russian name yields a non-empty, ASCII slug
# (the <slug:...> URL converter only matches ASCII; allow_unicode would break it).
_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh",
    "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "", "э": "e",
    "ю": "yu", "я": "ya",
}


def make_slug(value: str) -> str:
    """Transliterate then slugify (e.g. 'Зенит' -> 'zenit')."""
    translit = "".join(_TRANSLIT.get(ch.lower(), ch) for ch in (value or ""))
    return slugify(translit, allow_unicode=False)


def unique_slug(model, base: str, *, pk=None, fallback: str = "item") -> str:
    """Return a slug unique for `model`, appending -2, -3, … on collision."""
    base = base or fallback
    qs = model._default_manager.all()
    if pk:
        qs = qs.exclude(pk=pk)
    slug, i = base, 2
    while qs.filter(slug=slug).exists():
        slug, i = f"{base}-{i}", i + 1
    return slug


class League(models.Model):
    name_ru = models.CharField(_("Лига (RU)"), max_length=120)
    name_en = models.CharField(_("Лига (EN)"), max_length=120, blank=True)
    slug = models.SlugField(unique=True, blank=True)

    class Meta:
        verbose_name = _("Лига")
        verbose_name_plural = _("Лиги")
        ordering = ["name_ru"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(League, make_slug(self.name_en or self.name_ru),
                                    pk=self.pk, fallback="league")
        super().save(*args, **kwargs)

    @property
    def name(self):
        return pick(self.name_ru, self.name_en)

    def __str__(self):
        return self.name_ru


class Team(models.Model):
    name_ru = models.CharField(_("Команда (RU)"), max_length=120)
    name_en = models.CharField(_("Команда (EN)"), max_length=120, blank=True)
    league = models.ForeignKey(League, on_delete=models.SET_NULL, null=True, related_name="teams")
    slug = models.SlugField(unique=True, blank=True)

    class Meta:
        verbose_name = _("Команда")
        verbose_name_plural = _("Команды")
        ordering = ["name_ru"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(Team, make_slug(self.name_en or self.name_ru),
                                    pk=self.pk, fallback="team")
        super().save(*args, **kwargs)

    @property
    def name(self):
        return pick(self.name_ru, self.name_en)

    def __str__(self):
        return self.name_ru


class Category(models.TextChoices):
    """Top-level split shown on the home page."""
    CLUB = "club", _("Клубные")       # team / club jerseys
    COUNTRY = "country", _("Сборные")  # national-team / country jerseys


class Size(models.TextChoices):
    XS = "XS", "XS"
    S = "S", "S"
    M = "M", "M"
    L = "L", "L"
    XL = "XL", "XL"
    XXL = "XXL", "XXL"


class Product(models.Model):
    title_ru = models.CharField(_("Название (RU)"), max_length=200)
    title_en = models.CharField(_("Название (EN)"), max_length=200, blank=True)
    slug = models.SlugField(unique=True, blank=True, max_length=220)

    category = models.CharField(
        _("Категория"), max_length=10, choices=Category.choices, default=Category.CLUB,
        help_text=_("Клубная джерси или джерси сборной"),
    )
    # Nullable: country (national-team) jerseys have neither a club nor a league.
    team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name="products",
                             null=True, blank=True)
    league = models.ForeignKey(League, on_delete=models.PROTECT, related_name="products",
                               null=True, blank=True)
    # Used for country (national-team) jerseys instead of team/league.
    country_ru = models.CharField(_("Сборная/страна (RU)"), max_length=120, blank=True)
    country_en = models.CharField(_("Сборная/страна (EN)"), max_length=120, blank=True)

    season = models.CharField(_("Сезон"), max_length=20, help_text="например 2024/25")
    size = models.CharField(_("Размер"), max_length=4, choices=Size.choices)

    description_ru = models.TextField(_("Описание (RU)"), blank=True)
    description_en = models.TextField(_("Описание (EN)"), blank=True)

    # DecimalField (not float) — money must be exact. In RUB.
    price = models.DecimalField(_("Цена, ₽"), max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(_("Остаток"), default=0)
    is_active = models.BooleanField(_("Активен"), default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Джерси")
        verbose_name_plural = _("Джерси")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["team", "league", "size"]),
            models.Index(fields=["category"]),
            models.Index(fields=["price"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = make_slug(f"{self.title_en or self.title_ru}-{self.season}-{self.size}")
            self.slug = unique_slug(Product, base, pk=self.pk, fallback="jersey")
        super().save(*args, **kwargs)

    @property
    def title(self):
        return pick(self.title_ru, self.title_en)

    @property
    def description(self):
        return pick(self.description_ru, self.description_en)

    @property
    def country(self):
        return pick(self.country_ru, self.country_en)

    @property
    def origin(self):
        """Display label: club name for club jerseys, country for country jerseys."""
        if self.team:
            return self.team.name
        return self.country

    @property
    def in_stock(self) -> bool:
        return self.stock > 0

    @property
    def main_image(self):
        img = self.images.first()
        return img.image.url if img else None

    def get_absolute_url(self):
        return reverse("catalog:product_detail", args=[self.slug])

    def __str__(self):
        return f"{self.title_ru} ({self.season}, {self.size})"


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/%Y/%m/")
    alt_ru = models.CharField(max_length=150, blank=True)
    alt_en = models.CharField(max_length=150, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    @property
    def alt(self):
        return pick(self.alt_ru, self.alt_en)

    def __str__(self):
        return f"Image #{self.pk} for {self.product_id}"
