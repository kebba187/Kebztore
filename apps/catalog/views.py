"""
Product listing with filtering (team / league / size / price range) and detail.
All filters come from GET params and are applied through the ORM — values are
parameterized, so there is no SQL-injection surface here.
"""
from django.contrib.staticfiles import finders
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.templatetags.static import static
from django.utils.translation import gettext as _

from .models import Category, League, Product, Size, Team


def _curated_card_image(key):
    """Return the URL of a curated static category image if one is present.

    Drop a file named static/img/category-club.<ext> or category-country.<ext>
    (jpg/jpeg/png/webp) and it will be used as the card background.
    """
    for ext in ("jpg", "jpeg", "png", "webp"):
        rel = f"img/category-{key}.{ext}"
        if finders.find(rel):
            return static(rel)
    return None


def home(request):
    """Landing page: two category hero cards (Club / Country) + Featured."""
    cards = [
        {"key": Category.CLUB, "title": _("Клубные джерси"),
         "subtitle": _("Джерси футбольных клубов")},
        {"key": Category.COUNTRY, "title": _("Сборные"),
         "subtitle": _("Джерси национальных сборных")},
    ]
    for card in cards:
        # 1) Prefer a curated static image; 2) else newest in-category product image.
        image = _curated_card_image(card["key"])
        if not image:
            sample = (Product.objects.filter(category=card["key"], is_active=True,
                                             images__isnull=False)
                      .prefetch_related("images").first())
            image = sample.main_image if sample else None
        card["image"] = image

    featured = (Product.objects.filter(is_active=True)
                .select_related("team").prefetch_related("images")[:8])
    return render(request, "catalog/home.html", {"cards": cards, "featured": featured})


def product_list(request):
    qs = Product.objects.filter(is_active=True).select_related("team", "league").prefetch_related("images")

    category = request.GET.get("category")
    team = request.GET.get("team")
    league = request.GET.get("league")
    size = request.GET.get("size")
    price_min = request.GET.get("price_min")
    price_max = request.GET.get("price_max")

    if category in Category.values:
        qs = qs.filter(category=category)
    if team:
        qs = qs.filter(team__slug=team)
    if league:
        qs = qs.filter(league__slug=league)
    if size in Size.values:
        qs = qs.filter(size=size)
    # Guard numeric parsing — bad input is ignored rather than 500-ing.
    if price_min and price_min.isdigit():
        qs = qs.filter(price__gte=price_min)
    if price_max and price_max.isdigit():
        qs = qs.filter(price__lte=price_max)

    paginator = Paginator(qs, 12)
    page = paginator.get_page(request.GET.get("page"))

    # Preserve filters across pagination links.
    params = request.GET.copy()
    params.pop("page", None)

    context = {
        "page_obj": page,
        "leagues": League.objects.all(),
        "teams": Team.objects.select_related("league").all(),
        "sizes": Size.choices,
        "categories": Category.choices,
        "selected": {"team": team, "league": league, "size": size, "category": category,
                     "price_min": price_min, "price_max": price_max},
        "category_label": dict(Category.choices).get(category),
        "querystring": params.urlencode(),
    }
    return render(request, "catalog/product_list.html", context)


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related("team", "league").prefetch_related("images"),
        slug=slug, is_active=True,
    )
    return render(request, "catalog/product_detail.html", {"product": product})
