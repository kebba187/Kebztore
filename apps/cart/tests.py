from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase

from apps.catalog.models import League, Product, Size, Team
from .cart import Cart

User = get_user_model()


def _request_with_session(user=None):
    """Build a request with a real (anonymous) session for cart tests."""
    request = RequestFactory().get("/")
    SessionMiddleware(lambda r: None).process_request(request)
    request.session.save()
    request.user = user if user else _Anon()
    return request


class _Anon:
    is_authenticated = False


class CartTests(TestCase):
    def setUp(self):
        league = League.objects.create(name_ru="РПЛ")
        team = Team.objects.create(name_ru="Спартак", league=league)
        self.p1 = Product.objects.create(title_ru="J1", team=team, league=league,
                                         season="2024/25", size=Size.M, price=Decimal("5000"), stock=10)
        self.p2 = Product.objects.create(title_ru="J2", team=team, league=league,
                                         season="2024/25", size=Size.L, price=Decimal("3000"), stock=2)

    def test_add_and_subtotal_anonymous(self):
        cart = Cart(_request_with_session())
        cart.add(self.p1, 2)
        cart.add(self.p2, 1)
        self.assertEqual(len(cart), 3)
        self.assertEqual(cart.subtotal, Decimal("13000"))

    def test_quantity_clamped_to_stock(self):
        cart = Cart(_request_with_session())
        cart.add(self.p2, 99)  # only 2 in stock
        self.assertEqual(len(cart), 2)

    def test_update_and_remove(self):
        request = _request_with_session()
        cart = Cart(request)
        cart.add(self.p1, 1)
        cart.add(self.p1, 3)              # accumulates -> 4
        self.assertEqual(len(cart), 4)
        cart.remove(self.p1)
        self.assertTrue(cart.is_empty)

    def test_user_cart_is_persistent(self):
        user = User.objects.create_user(email="u@example.com", password="x12345678")
        cart = Cart(_request_with_session(user))
        cart.add(self.p1, 2)
        # New Cart for same user reads from DB.
        again = Cart(_request_with_session(user))
        self.assertEqual(len(again), 2)
