# Кебзtore — магазин футбольных джерси

Bilingual (RU default / EN fallback) Django + PostgreSQL e‑commerce store for football
jerseys, built for the Russian market (RUB, 152‑ФЗ compliance, YooKassa payments,
Russian carriers). Server‑rendered templates + light vanilla JS.

## Stack
- **Backend:** Python 3.11+, Django 5
- **DB:** PostgreSQL (host in Russia: Yandex.Cloud / SberCloud / Timeweb)
- **Payments:** YooKassa (ЮKassa) — Mir, SberPay/Mir Pay, СБП(SBP) QR, YooMoney
- **Frontend:** Django templates + `static/js/main.js` (no framework)

## Project layout
```
jersey/
├─ manage.py
├─ requirements.txt
├─ .env.example            # copy to .env, fill secrets (gitignored)
├─ config/                 # project: settings, urls, wsgi/asgi
├─ apps/
│  ├─ accounts/            # custom email-login User, register/login/profile
│  ├─ catalog/             # League, Team, Product, ProductImage + listing/detail
│  ├─ cart/                # session + DB-backed cart, JSON endpoints
│  ├─ orders/             # Order, OrderItem, checkout, order service
│  ├─ shipping/           # ShippingMethod, ShippingRule (flat-rate)
│  ├─ payments/           # YooKassa gateway + webhook
│  └─ pages/              # 152-ФЗ personal-data page, consent endpoint
├─ templates/             # base + per-app templates (bilingual)
├─ static/                # css + js
└─ locale/                # translations (django.po) — generate with makemessages
```

## Setup (local)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

Copy-Item .env.example .env      # then edit .env with real values
# For a quick start WITHOUT Postgres, comment out DATABASE_URL in .env (uses SQLite).

python manage.py makemigrations
python manage.py migrate
python manage.py seed_demo        # demo jerseys + shipping rules
python manage.py createsuperuser  # email + password
python manage.py runserver
```
Open http://localhost:8000 (store) and http://localhost:8000/admin/ (back‑office).

## Tests
```powershell
python manage.py test
```
Covers: Product model (`apps/catalog/tests.py`), cart operations (`apps/cart/tests.py`),
order creation incl. shipping & stock (`apps/orders/tests.py`).

## Translations (RU default / EN fallback)
Static UI strings use `{% trans %}` / `gettext`. Generate catalogs:
```powershell
python manage.py makemessages -l en
python manage.py compilemessages
```
Per‑object content (product titles, descriptions) is stored in `_ru` / `_en` columns and
resolved by the active language with RU fallback.

## Production notes
- Set `DJANGO_DEBUG=False`, real `DJANGO_SECRET_KEY`, real `DJANGO_ALLOWED_HOSTS`.
- Run behind HTTPS (security cookies + HSTS turn on automatically when DEBUG is off).
- `python manage.py collectstatic`; serve via `gunicorn config.wsgi` + nginx.
- DB **must** be physically in Russia (152‑ФЗ). See deployment section in the answer.

## YooKassa
Put `YOOKASSA_SHOP_ID` / `YOOKASSA_SECRET_KEY` (test shop) in `.env`. Configure the webhook
URL in the YooKassa dashboard to `https://<host>/payments/webhook/yookassa/`.
