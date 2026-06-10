"""
Populate the store with demo leagues, teams, jerseys and shipping rules.
Run:  python manage.py seed_demo
"""
from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.catalog.models import Category, League, Product, Size, Team
from apps.shipping.models import ShippingMethod, ShippingRule


class Command(BaseCommand):
    help = "Seed demo catalog and shipping data"

    def handle(self, *args, **options):
        rpl, _ = League.objects.get_or_create(name_ru="РПЛ", defaults={"name_en": "RPL"})
        epl, _ = League.objects.get_or_create(name_ru="АПЛ", defaults={"name_en": "Premier League"})

        zenit, _ = Team.objects.get_or_create(name_ru="Зенит", defaults={"name_en": "Zenit", "league": rpl})
        spartak, _ = Team.objects.get_or_create(name_ru="Спартак", defaults={"name_en": "Spartak", "league": rpl})
        city, _ = Team.objects.get_or_create(name_ru="Манчестер Сити", defaults={"name_en": "Man City", "league": epl})

        C, N = Category.CLUB, Category.COUNTRY
        # Club jerseys: have team + league. Country jerseys: have country, no team.
        demo = [
            dict(category=C, team=zenit, league=rpl, ru="Домашняя джерси Зенит 2024/25", en="Zenit Home Jersey 2024/25", size=Size.L, price=6990, stock=8),
            dict(category=C, team=zenit, league=rpl, ru="Гостевая джерси Зенит 2024/25", en="Zenit Away Jersey 2024/25", size=Size.M, price=6990, stock=5),
            dict(category=C, team=spartak, league=rpl, ru="Домашняя джерси Спартак 2024/25", en="Spartak Home Jersey 2024/25", size=Size.XL, price=6490, stock=3),
            dict(category=C, team=city, league=epl, ru="Домашняя джерси Ман Сити 2024/25", en="Man City Home Jersey 2024/25", size=Size.M, price=8990, stock=10),
            dict(category=N, country_ru="Россия", country_en="Russia", ru="Джерси сборной России 2024", en="Russia National Jersey 2024", size=Size.L, price=7490, stock=12),
            dict(category=N, country_ru="Бразилия", country_en="Brazil", ru="Джерси сборной Бразилии 2024", en="Brazil National Jersey 2024", size=Size.M, price=7990, stock=7),
        ]
        for d in demo:
            Product.objects.get_or_create(
                title_ru=d["ru"],
                defaults=dict(
                    title_en=d["en"], category=d["category"],
                    team=d.get("team"), league=d.get("league"),
                    country_ru=d.get("country_ru", ""), country_en=d.get("country_en", ""),
                    season="2024/25", size=d["size"], price=Decimal(d["price"]), stock=d["stock"],
                    description_ru="Оригинальная футбольная джерси. Дышащая ткань.",
                    description_en="Original football jersey. Breathable fabric."),
            )

        rules = [
            ("russian_post", "Почта России", 1, 5, 14, 300, 8000),
            ("cdek", "СДЭК", 1, 2, 5, 400, 8000),
            ("boxberry", "Boxberry", 2, 2, 6, 350, 8000),
            ("yandex", "Яндекс.Доставка", 1, 1, 3, 500, 10000),
        ]
        for code, name, eta_min_extra, eta_min, eta_max, cost, free in rules:
            method, _ = ShippingMethod.objects.get_or_create(
                code=code, defaults=dict(name_ru=name, eta_days_min=eta_min, eta_days_max=eta_max))
            ShippingRule.objects.get_or_create(
                method=method, region="",
                defaults=dict(cost=Decimal(cost), free_above=Decimal(free)))

        self.stdout.write(self.style.SUCCESS("Demo data seeded."))
