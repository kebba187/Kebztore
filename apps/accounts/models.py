"""
Custom user model: email is the login (no separate username).
Password is hashed by Django (PBKDF2 by default) — we never store plaintext.
PII is minimized: only what we need to fulfil and ship an order.
"""
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Manager that creates users by email instead of username."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        if not email:
            raise ValueError(_("Требуется email"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra)
        user.set_password(password)  # hashes the password
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra)


class User(AbstractUser):
    username = None  # drop username; use email instead
    email = models.EmailField(_("Email"), unique=True)
    phone = models.CharField(_("Телефон"), max_length=20, blank=True)
    full_name = models.CharField(_("ФИО"), max_length=150, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # email + password is enough for createsuperuser

    objects = UserManager()

    class Meta:
        verbose_name = _("Пользователь")
        verbose_name_plural = _("Пользователи")

    def __str__(self):
        return self.email
