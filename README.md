# Kvitto Payments API

REST API для приёма платежей онлайн-школы через тарифы, промокод и рассрочку. Проект выполнен на FastAPI с SQLite и синхронным SQLAlchemy 2.0.

## Технологии

- Python 3.11+
- FastAPI
- Pydantic v2
- SQLAlchemy 2.0
- SQLite
- pytest + httpx

## Установка

### Windows PowerShell

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

### Установка зависимостей

```bash
pip install -r requirements.txt
```

## Запуск приложения

```bash
uvicorn app.main:app --reload
```

Приложение будет доступно по адресу `http://127.0.0.1:8000`.

Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

При старте приложение создаёт SQLite-базу `payments.db`, таблицы и начальные тарифы: `basic`, `standard`, `premium`.

## Запуск тестов

```bash
python -m pytest -v
```

## API

### `GET /tariffs`

Возвращает список доступных тарифов.

```bash
curl http://127.0.0.1:8000/tariffs
```

Ответ: `200 OK`

```json
[
  {"id": 1, "title": "basic", "price": 990000},
  {"id": 2, "title": "standard", "price": 1990000},
  {"id": 3, "title": "premium", "price": 2990000}
]
```

### `POST /payments`

Создаёт платёж. Тело запроса:

- `tariff_id` — ID тарифа;
- `email` — email плательщика;
- `method` — `card`, `sbp` или `installment`;
- `installment_months` — обязательно для `installment`: `3`, `6` или `12`;
- `promo_code` — необязательный промокод.

Заголовок `Idempotency-Key` необязателен. Повторный запрос с тем же ключом возвращает исходный платёж с кодом `200`, не создавая дубликат.

```bash
curl -X POST http://127.0.0.1:8000/payments \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: payment-key-1" \
  -d '{"tariff_id": 1, "email": "user@example.com", "method": "card", "promo_code": "KVITTO10"}'
```

Ответ при создании: `201 Created`

```json
{
  "id": 1,
  "status": "pending",
  "tariff_id": 1,
  "amount": 891000,
  "discount": 99000,
  "method": "card",
  "installment_months": null,
  "schedule": null,
  "email": "user@example.com",
  "created_at": "2026-10-15T12:00:00"
}
```

### `GET /payments/{id}`

Возвращает платёж по ID. Для рассрочки поле `schedule` содержит список сумм в копейках; для обычной оплаты — `null`.

```bash
curl http://127.0.0.1:8000/payments/1
```

Ответ: `200 OK` или `404 Not Found`, если платежа нет.

### `POST /webhooks/bank`

Обрабатывает уведомление банка о смене статуса платежа.

```bash
curl -X POST http://127.0.0.1:8000/webhooks/bank \
  -H "Content-Type: application/json" \
  -d '{"payment_id": 1, "status": "succeeded"}'
```

Ответ при успехе: `200 OK`

```json
{"result": "ok"}
```

При запрещённом переходе статуса возвращается `409 Conflict`:

```json
{"error": "invalid_transition"}
```

## Бизнес-правила

- Все денежные суммы хранятся и передаются в копейках целыми числами.
- Промокод `KVITTO10` даёт скидку 10%; регистр не важен. Неизвестный промокод возвращает `422`.
- Для `installment` поле `installment_months` обязательно и может быть только `3`, `6` или `12`.
- График рассрочки делит итоговую сумму на копейки без `float`; остаток распределяется по первым платежам.
- Новый платёж создаётся со статусом `pending`.
- Разрешённые переходы статусов:
  - `pending` → `succeeded`;
  - `pending` → `failed`;
  - `succeeded` → `refunded`.
- Все остальные переходы возвращают `409` и не изменяют статус.
