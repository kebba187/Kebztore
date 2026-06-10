# Развёртывание Кебзtore в продакшн (Россия)

Пошаговый гайд для запуска на российском хостинге. По 152-ФЗ база данных с
персональными данными граждан РФ **обязана** находиться на серверах в России
(Yandex.Cloud / SberCloud / Timeweb Cloud).

---

## 0. Перед запуском (чек-лист)

- [ ] `DJANGO_DEBUG=False`
- [ ] `DJANGO_SECRET_KEY` — длинный случайный ключ (50+ символов)
- [ ] `DJANGO_ALLOWED_HOSTS` — ваш домен
- [ ] `DJANGO_CSRF_TRUSTED_ORIGINS` — `https://домен` (со схемой)
- [ ] `DATABASE_URL` — PostgreSQL на сервере в РФ
- [ ] `YOOKASSA_SHOP_ID` / `YOOKASSA_SECRET_KEY` — боевые ключи
- [ ] `EMAIL_HOST*` — рабочий SMTP
- [ ] HTTPS-сертификат настроен (Let's Encrypt)
- [ ] Заполнены реквизиты в `templates/pages/offer.html`

Сгенерировать секретный ключ:
```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Проверить готовность настроек безопасности:
```bash
python manage.py check --deploy
```

---

## 1. Сервер (Ubuntu 22.04, пример)

```bash
sudo apt update && sudo apt install -y python3-venv python3-pip nginx postgresql-client git
git clone <ваш-репозиторий> /srv/kebztore && cd /srv/kebztore

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Переменные окружения

```bash
cp .env.example .env
nano .env      # заполнить РЕАЛЬНЫМИ значениями (см. чек-лист выше)
```

## 3. База данных, статика, админ

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
# python manage.py seed_demo   # только если нужны демо-товары
```

## 4. Запуск через Gunicorn + systemd

`/etc/systemd/system/kebztore.service`:
```ini
[Unit]
Description=Kebztore (gunicorn)
After=network.target

[Service]
User=www-data
WorkingDirectory=/srv/kebztore
EnvironmentFile=/srv/kebztore/.env
ExecStart=/srv/kebztore/.venv/bin/gunicorn config.wsgi:application \
          --bind 127.0.0.1:8001 --workers 3
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl enable --now kebztore
```

## 5. Nginx (reverse proxy + HTTPS + media/static)

`/etc/nginx/sites-available/kebztore`:
```nginx
server {
    server_name kebztore.ru www.kebztore.ru;

    location /static/ { alias /srv/kebztore/staticfiles/; }
    location /media/  { alias /srv/kebztore/media/; }

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;   # Django reads this for SSL
    }
}
```
```bash
sudo ln -s /etc/nginx/sites-available/kebztore /etc/nginx/sites-enabled/
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d kebztore.ru -d www.kebztore.ru   # выдаёт HTTPS-сертификат
sudo systemctl reload nginx
```

После HTTPS настройки `DEBUG=False` автоматически включает SSL-redirect, HSTS,
secure-cookies (см. `config/settings.py`).

---

## 6. YooKassa (боевой режим)

1. В личном кабинете ЮKassa получите боевые `shop_id` и `secret_key`, впишите в `.env`.
2. Настройте webhook (HTTP-уведомления) на:
   `https://kebztore.ru/payments/webhook/yookassa/`
   События: `payment.succeeded`, `payment.canceled`.
3. Webhook — это источник правды по оплате (см. `apps/payments/views.py`).

---

## 7. Хостинг-провайдеры (РФ)

| Провайдер       | Что использовать                                  |
|-----------------|---------------------------------------------------|
| **Timeweb Cloud** | VPS + Managed PostgreSQL — самый простой старт   |
| **Yandex.Cloud**  | Compute Cloud + Managed PostgreSQL               |
| **SberCloud**     | Evolution VPS + Managed PostgreSQL               |

Во всех случаях БД создавайте в российском регионе (152-ФЗ).

---

## 8. Письма и мониторинг

- **Письмо-подтверждение заказа** отправляется автоматически при оплате
  (webhook `payment.succeeded` -> `apps/orders/emails.py`). Нужен рабочий SMTP
  (`EMAIL_HOST*` в `.env`). Без SMTP письма выводятся в консоль (dev).
- **Sentry уже встроен** — просто задайте `SENTRY_DSN` в `.env`. Персональные
  данные в Sentry НЕ отправляются (`send_default_pii=False`). Для строгого
  соответствия 152-ФЗ разверните self-hosted Sentry на сервере в РФ.

> Примечание (Windows-разработка): консольный backend писем может ругаться на
> символ «₽» из-за кодировки cp1251 — это только локальная консоль, на боевом
> SMTP проблемы нет (письмо формируется корректно).

## 9. Обслуживание

- **Бэкапы БД:** ежедневный `pg_dump` (или managed-бэкапы провайдера).
- **Обновления:** `git pull && pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput && sudo systemctl restart kebztore`.
- **Логи:** `journalctl -u kebztore -f`.
