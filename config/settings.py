"""
Django settings for Кебзtore.

Security posture (see inline notes):
  * CSRF        -> django.middleware.csrf.CsrfViewMiddleware (enabled below);
                   every POST form uses {% csrf_token %}.
  * XSS         -> Django template auto-escaping is ON by default.
  * SQL inject  -> all DB access goes through the Django ORM (parameterized).
  * Passwords   -> Django PBKDF2 hasher by default (bcrypt available too).
  * 152-ФЗ      -> DB host MUST be located in Russia; we store the minimum PII.
"""
from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")  # read secrets from .env (gitignored)


def env(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key, default)


# ── Core ─────────────────────────────────────────────────────────────────────
SECRET_KEY = env("DJANGO_SECRET_KEY", "insecure-dev-key-change-me")
DEBUG = env("DJANGO_DEBUG", "False") == "True"
ALLOWED_HOSTS = [h for h in env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h]

# Required for HTTPS form POSTs in production (Django 4+). Must include the
# scheme, e.g. DJANGO_CSRF_TRUSTED_ORIGINS=https://kebztore.ru,https://www.kebztore.ru
CSRF_TRUSTED_ORIGINS = [o for o in env("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o]

# Custom user model (email as login). Must be set before the first migration.
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "catalog:product_list"
LOGOUT_REDIRECT_URL = "catalog:product_list"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # Project apps
    "apps.accounts",
    "apps.catalog",
    "apps.cart",
    "apps.orders",
    "apps.shipping",
    "apps.payments",
    "apps.pages",
    "apps.dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",        # static files in prod
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",          # i18n (RU default / EN)
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",          # CSRF protection
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.cart.context_processors.cart",       # cart badge in header
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# ── Database (PostgreSQL on a Russia-located host) ───────────────────────────
def parse_database_url(url: str) -> dict:
    """Minimal postgres://user:pass@host:port/name parser (no extra deps)."""
    from urllib.parse import urlparse

    p = urlparse(url)
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": p.path.lstrip("/"),
        "USER": p.username or "",
        "PASSWORD": p.password or "",
        "HOST": p.hostname or "localhost",
        "PORT": str(p.port or 5432),
    }


DATABASE_URL = env("DATABASE_URL")
if DATABASE_URL:
    DATABASES = {"default": parse_database_url(DATABASE_URL)}
else:
    # Fallback for first-run / tests without Postgres configured.
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}


# ── Passwords ────────────────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
# Django's default is PBKDF2. To prefer bcrypt, install `bcrypt` and uncomment:
# PASSWORD_HASHERS = [
#     "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
#     "django.contrib.auth.hashers.PBKDF2PasswordHasher",
# ]


# ── i18n / l10n (Russian default, English fallback) ──────────────────────────
LANGUAGE_CODE = "ru"
LANGUAGES = [("ru", "Русский"), ("en", "English")]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True


# ── Static & media ───────────────────────────────────────────────────────────
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ── Security hardening for production (active when DEBUG=False) ───────────────
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_COOKIE_HTTPONLY = False  # template forms read the token; JS uses header
X_FRAME_OPTIONS = "DENY"


# ── YooKassa (ЮKassa) — sandbox ──────────────────────────────────────────────
YOOKASSA_SHOP_ID = env("YOOKASSA_SHOP_ID", "")
YOOKASSA_SECRET_KEY = env("YOOKASSA_SECRET_KEY", "")
YOOKASSA_RETURN_URL = env("YOOKASSA_RETURN_URL", "http://localhost:8000/orders/payment/return/")


# ── Email ────────────────────────────────────────────────────────────────────
if env("EMAIL_HOST"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = env("EMAIL_HOST")
    EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
    EMAIL_PORT = int(env("EMAIL_PORT", "465"))
    EMAIL_USE_SSL = env("EMAIL_USE_SSL", "True") == "True"
else:
    # Dev/no-SMTP: emails are printed to the console instead of being sent.
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Sender for transactional mail (order confirmations, password reset).
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL") or env("EMAIL_HOST_USER") or "Кебзtore <noreply@kebztore.ru>"

MESSAGE_TAGS = {50: "danger"}  # map Django ERROR -> Bootstrap-style "danger"


# ── Error monitoring (Sentry) — opt-in via SENTRY_DSN ────────────────────────
# 152-ФЗ note: Sentry's servers may be outside Russia, so we DO NOT send PII
# (send_default_pii=False) — only stack traces/technical context leave the box.
# For strict compliance, self-host Sentry on a Russian server.
SENTRY_DSN = env("SENTRY_DSN", "")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=float(env("SENTRY_TRACES_SAMPLE_RATE", "0.0")),
        send_default_pii=False,
        environment=env("SENTRY_ENVIRONMENT", "production"),
    )
