"""
Unified cart abstraction.

  * Anonymous user -> items kept in request.session["cart"] = {product_id: qty}.
  * Logged-in user -> items kept in the SavedCartItem table (write-through),
    so the cart is user-bound and persists across sessions.

A jersey's size is part of the Product, so a cart line is keyed by product id
only. Quantities are clamped to available stock. All money is Decimal.
"""
from decimal import Decimal

from apps.catalog.models import Product
from .models import SavedCartItem

SESSION_KEY = "cart"


class Cart:
    def __init__(self, request):
        self.request = request
        self.user = request.user if request.user.is_authenticated else None
        if self.user is None:
            self.session = request.session
            self._items = self.session.setdefault(SESSION_KEY, {})

    # ── mutations ────────────────────────────────────────────────────────────
    def add(self, product: Product, quantity: int = 1, *, replace: bool = False):
        quantity = max(1, int(quantity))
        if product.stock <= 0:
            return  # nothing to add for an out-of-stock product
        if self.user:
            # defaults quantity=0 so a brand-new row starts empty, not at the
            # model default of 1 (otherwise the first add would be off by one).
            item, _ = SavedCartItem.objects.get_or_create(
                user=self.user, product=product, defaults={"quantity": 0})
            item.quantity = quantity if replace else item.quantity + quantity
            item.quantity = min(item.quantity, product.stock)  # stock > 0 here, so >= 1
            item.save()
        else:
            pid = str(product.id)
            current = 0 if replace else self._items.get(pid, 0)
            self._items[pid] = min(current + quantity, product.stock)
            self._save_session()

    def remove(self, product: Product):
        if self.user:
            SavedCartItem.objects.filter(user=self.user, product=product).delete()
        else:
            self._items.pop(str(product.id), None)
            self._save_session()

    def clear(self):
        if self.user:
            SavedCartItem.objects.filter(user=self.user).delete()
        else:
            self.session[SESSION_KEY] = {}
            self._items = self.session[SESSION_KEY]
            self._save_session()

    def merge_on_login(self, user):
        """Fold the anonymous session cart into the user's persistent cart."""
        session_items = self.request.session.get(SESSION_KEY, {})
        for pid, qty in session_items.items():
            product = Product.objects.filter(id=pid, is_active=True).first()
            if product and product.stock > 0:
                item, _ = SavedCartItem.objects.get_or_create(
                    user=user, product=product, defaults={"quantity": 0})
                item.quantity = min(item.quantity + qty, product.stock)
                item.save()
        self.request.session[SESSION_KEY] = {}
        self.request.session.modified = True

    def _save_session(self):
        self.session[SESSION_KEY] = self._items
        self.session.modified = True

    # ── reads ────────────────────────────────────────────────────────────────
    def _raw(self):
        """Return [(product, qty), ...] from the active backend."""
        if self.user:
            return [(ci.product, ci.quantity)
                    for ci in SavedCartItem.objects.filter(user=self.user).select_related("product")]
        products = Product.objects.filter(id__in=self._items.keys())
        return [(p, self._items[str(p.id)]) for p in products]

    def __iter__(self):
        for product, qty in self._raw():
            yield {
                "product": product,
                "quantity": qty,
                "unit_price": product.price,
                "line_total": product.price * qty,
            }

    def __len__(self):
        return sum(qty for _, qty in self._raw())

    @property
    def subtotal(self) -> Decimal:
        return sum((p.price * qty for p, qty in self._raw()), Decimal("0.00"))

    @property
    def is_empty(self) -> bool:
        return len(self) == 0
