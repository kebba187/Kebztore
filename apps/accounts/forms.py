"""
Auth forms. All validation runs server-side (Django Forms) — this is the
authoritative validation layer regardless of any client-side checks.
"""
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(label=_("Пароль"), widget=forms.PasswordInput, min_length=8)
    password2 = forms.CharField(label=_("Повтор пароля"), widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["email", "full_name", "phone"]

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_("Пользователь с таким email уже существует."))
        return email

    def clean(self):
        data = super().clean()
        if data.get("password1") != data.get("password2"):
            self.add_error("password2", _("Пароли не совпадают."))
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])  # hashed
        if commit:
            user.save()
        return user


class EmailAuthenticationForm(AuthenticationForm):
    """Login form keyed on email."""

    username = forms.EmailField(label=_("Email"), widget=forms.EmailInput)
