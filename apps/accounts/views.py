from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext as _

from apps.cart.cart import Cart
from apps.orders.models import Order
from .forms import EmailAuthenticationForm, RegisterForm


def register(request):
    if request.user.is_authenticated:
        return redirect("catalog:product_list")
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            Cart(request).merge_on_login(user)  # keep anonymous cart after signup
            return redirect("catalog:product_list")
    else:
        form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form})


class KebzLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = EmailAuthenticationForm

    def form_valid(self, form):
        response = super().form_valid(form)
        Cart(self.request).merge_on_login(self.request.user)
        return response


class KebzLogoutView(LogoutView):
    next_page = reverse_lazy("catalog:product_list")


@login_required
def profile(request):
    orders = (
        Order.objects.filter(user=request.user)
        .select_related("shipping_method")
        .prefetch_related("items")
        .order_by("-created_at")
    )
    return render(request, "accounts/profile.html", {"orders": orders})
