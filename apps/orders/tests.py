from decimal import Decimal

from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase

from apps.cart.cart import Cart
from apps.catalog.models import League, Product, Size, Team
from apps.shipping.models import ShippingMethod, ShippingRule
from .models import Order
from .services import create_order_from_cart


class _Anon:
    is_authenticated = False


def _request_with_session():
    request = RequestFactory().get("/")
    SessionMiddleware(lambda r: None).process_request(request)
    request.session.save()
    request.user = _Anon()
    return request


class OrderCreationTests(TestCase):
    def setUp(self):
        league = League.objects.create(name_ru="РПЛ")
        team = Team.objects.create(name_ru="ЦСКА", league=league)
        self.product = Product.objects.create(title_ru="J", team=team, league=league,
                                              season="2024/25", size=Size.M, price=Decimal("4000"), stock=5)
        self.method = ShippingMethod.objects.create(code="cdek", name_ru="СДЭК")
        ShippingRule.objects.create(method=self.method, region="", cost=Decimal("300"),
                                    free_above=Decimal("10000"))

    def _make_order(self):
        return Order(
            full_name="Иван Иванов", email="i@example.com", phone="+79991234567",
            region="Москва", city="Москва", street="Тверская", building="1",
            postal_code="101000", shipping_method=self.method,
        )

    def test_order_created_with_snapshot_and_stock_decremented(self):
        request = _request_with_session()
        cart = Cart(request)
        cart.add(self.product, 2)

        order = create_order_from_cart(cart, self._make_order())

        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.items.count(), 1)
        item = order.items.first()
        self.assertEqual(item.unit_price, Decimal("4000"))  # snapshot
        self.assertEqual(item.quantity, 2)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)             # 5 - 2
        self.assertTrue(cart.is_empty)                       # cart cleared

    def test_shipping_cost_applied(self):
        request = _request_with_session()
        cart = Cart(request)
        cart.add(self.product, 1)                            # subtotal 4000 < free_above
        order = create_order_from_cart(cart, self._make_order())
        self.assertEqual(order.shipping_cost, Decimal("300"))
        self.assertEqual(order.grand_total, Decimal("4300"))

    def test_free_shipping_above_threshold(self):
        request = _request_with_session()
        cart = Cart(request)
        cart.add(self.product, 3)                            # subtotal 12000 >= 10000
        order = create_order_from_cart(cart, self._make_order())
        self.assertEqual(order.shipping_cost, Decimal("0.00"))

    def test_empty_cart_rejected(self):
        request = _request_with_session()
        cart = Cart(request)
        with self.assertRaises(ValueError):
            create_order_from_cart(cart, self._make_order())
