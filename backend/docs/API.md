# Telegram Store API (v1)

Base URL: `/api/v1` (dev: `http://localhost:8000/api/v1`)

Authentication: `Authorization: Bearer <JWT>` on every endpoint except
`/auth/*`, `/health` and the payment webhook. Obtain a token with
`POST /auth/dev-login` (development) or `POST /auth/telegram-login`
(Telegram Login Widget payload).

All paginated endpoints return:

```json
{
  "items": [],
  "meta": { "total": 0, "page": 1, "page_size": 20, "total_pages": 0 }
}
```

`page` starts at 1. Query params not mentioned are optional.

## Auth

| Method | Path | Permission | Body / Notes |
| --- | --- | --- | --- |
| POST | `/auth/dev-login` | public (dev) | `{ "telegram_id": 123456789 }` → `TokenResponse` |
| POST | `/auth/telegram-login` | public | `{ id, first_name?, last_name?, username?, photo_url?, auth_date, hash }` → `TokenResponse` |
| GET | `/auth/me` | authenticated | → `AdminProfile` (includes `permissions[]`) |
| POST | `/auth/logout` | authenticated | → `{ message, success }` |

`TokenResponse`: `{ access_token, token_type: "bearer", expires_in, admin: AdminProfile }`

## Health

`GET /health` → `{ status, app, version, environment, database, cache, payment_provider, bot_configured }`

## Dashboard & reports

| Method | Path | Permission | Notes |
| --- | --- | --- | --- |
| GET | `/stats/dashboard` | dashboard.view | `DashboardStats` (revenue totals/today/month, counts, series, top products, recent orders) |
| GET | `/analytics?days=30` | analytics.view | `AnalyticsResponse` (7–365 days) |
| GET | `/reports/revenue?period=month&start_date&end_date` | reports.view | period = today\|week\|month\|year\|all |

## Categories

| Method | Path | Permission |
| --- | --- | --- |
| GET | `/categories?active_only&search` | categories.manage |
| POST | `/categories` | categories.manage |
| PATCH | `/categories/{id}` | categories.manage |
| DELETE | `/categories/{id}` | categories.manage |

Category body: `{ slug, name_id, name_en, description_id?, description_en?, icon, sort_order, is_active }`.
Response adds `id`, `product_count`, `created_at`.

## Products

| Method | Path | Permission |
| --- | --- | --- |
| GET | `/products?category_id&active_only&featured&search&page&page_size` | products.manage |
| GET | `/products/{id}` | products.manage |
| POST | `/products` | products.manage |
| PATCH | `/products/{id}` | products.manage |
| DELETE | `/products/{id}` | products.manage |
| POST | `/products/bulk-delete` | products.manage |

Product body: `{ category_id?, sku?, name_id, name_en, description_id?, description_en?, price, compare_price?, currency, delivery_type: AUTO|MANUAL, image_url?, min_quantity, max_quantity, is_active, is_featured, sort_order, delivery_instructions?, stock?: string[] }`.
Response adds `id`, `sold_count`, `stock_available`, `stock_sold`, `category_name`, timestamps.

## Stock

| Method | Path | Permission | Notes |
| --- | --- | --- | --- |
| GET | `/stock/summary` | stock.manage | `StockSummary[]` with `low_stock` |
| GET | `/stock?product_id&used&search&page&page_size` | stock.manage | `Page<StockItemOut>` |
| POST | `/stock` | stock.manage | `{ product_id, lines: string[], label?, deduplicate }` → `StockImportResult` |
| POST | `/stock/import` | stock.manage | multipart: `product_id`, `file` (.txt/.csv), `deduplicate`, `label` |
| GET | `/stock/export?product_id&used` | stock.manage | CSV download |
| PATCH | `/stock/{id}` | stock.manage | `{ content?, label? }` |
| DELETE | `/stock/{id}` | stock.manage | unused only |
| POST | `/stock/bulk-delete` | stock.manage | `{ ids: number[] }` |

## Orders & transactions

| Method | Path | Permission | Notes |
| --- | --- | --- | --- |
| GET | `/orders?status&customer_id&product_id&search&page&page_size` | orders.manage | `Page<OrderOut>` |
| GET | `/orders/{id}` | orders.manage | `OrderOut` incl. `invoice`, `delivery` |
| PATCH | `/orders/{id}/note` | orders.manage | `{ admin_note }` |
| PATCH | `/orders/{id}/status` | orders.manage | `{ status, note? }` |
| POST | `/orders/{id}/cancel` | orders.manage | unpaid only |
| POST | `/orders/{id}/mark-paid` | orders.manage | manual settlement + delivery |
| POST | `/orders/{id}/invoice/refresh` | orders.manage | re-check gateway |
| POST | `/orders/{id}/invoice/recreate` | orders.manage | unpaid only |
| GET | `/transactions?status&search&page&page_size` | transactions.view | `Page<TransactionOut>` |

Order statuses: `PENDING_PAYMENT, PAID, DELIVERED, COMPLETED, EXPIRED, CANCELLED, FAILED, REFUNDED`.
Delivery statuses: `PENDING, PROCESSING, DELIVERED, FAILED, NOT_REQUIRED`.

## Deliveries

| Method | Path | Permission | Notes |
| --- | --- | --- | --- |
| GET | `/deliveries/queue` | delivery.manage | paid manual orders awaiting fulfilment |
| GET | `/deliveries?status&mode&page&page_size` | delivery.manage | `Page<DeliveryOut>` |
| GET | `/deliveries/failed` | delivery.manage | max 200 |
| GET | `/deliveries/types` | delivery.manage | `["AUTO","MANUAL"]` |
| POST | `/deliveries/{id}/retry` | delivery.manage | max 5 attempts |
| POST | `/orders/{id}/deliver` | delivery.manage | `{ content, note?, mark_completed }` |

## Payments

| Method | Path | Permission | Notes |
| --- | --- | --- | --- |
| GET | `/payments/invoices?status&provider&order_id&page&page_size` | payments.view | `Page<PaymentInvoiceOut>` |
| GET | `/payments/invoices/{id}` | payments.view | |
| POST | `/payments/invoices/{id}/check` | payments.view | refresh from gateway |
| POST | `/payments/invoices/{id}/manual` | payments.view | `{ tx_hash?, note?, paid_amount? }` |
| GET | `/payments/webhook-events?processed&page&page_size` | payments.view | audit + dedupe trail |
| POST | `/payments/webhook/{provider}` | public | Cryptomus callback, HMAC validated |
| GET | `/payments/provider` | payments.view | `ProviderStatus` |
| POST | `/payments/provider-check` | payments.view | `ProviderCheckResponse` |
| GET | `/payments/mock/{order_code}/pay` | dev only | simulate mock payment |

Invoice statuses: `PENDING, CONFIRMING, PAID, UNDERPAID, OVERPAID, EXPIRED, FAILED, CANCELLED`.

## Vouchers

| Method | Path | Permission |
| --- | --- | --- |
| GET | `/vouchers?active&search&page&page_size` | vouchers.manage |
| POST | `/vouchers` | vouchers.manage |
| PATCH | `/vouchers/{id}` | vouchers.manage |
| DELETE | `/vouchers/{id}` | vouchers.manage |
| GET | `/vouchers/{id}/redemptions` | vouchers.manage |
| POST | `/vouchers/validate` | vouchers.manage |

Body: `{ code, description?, type: PERCENT|FIXED, value, min_purchase, max_discount?, usage_limit, per_customer_limit, valid_from?, valid_until?, is_active }`.
Validate body: `{ code, subtotal }` → `{ valid, discount, total, message }`.

## Broadcasts

| Method | Path | Permission | Notes |
| --- | --- | --- | --- |
| GET | `/broadcasts?page&page_size` | broadcast.manage | |
| POST | `/broadcasts` | broadcast.manage | `{ title, message, audience: ALL|BUYERS|ACTIVE, send_now }` |
| POST | `/broadcasts/{id}/run` | broadcast.manage | send now |
| DELETE | `/broadcasts/{id}` | broadcast.manage | not while sending |

## Customers

| Method | Path | Permission | Notes |
| --- | --- | --- | --- |
| GET | `/customers?search&blocked&page&page_size` | customers.manage | search by name/username/telegram id |
| GET | `/customers/{id}` | customers.manage | `CustomerDetail` + `recent_orders`, `open_tickets` |
| PATCH | `/customers/{id}` | customers.manage | `{ is_blocked?, notes?, language? }` |

## Support tickets

| Method | Path | Permission | Notes |
| --- | --- | --- | --- |
| GET | `/tickets?status&search&customer_id&page&page_size` | tickets.manage | status = OPEN\|PENDING\|ANSWERED\|CLOSED |
| GET | `/tickets/{id}` | tickets.manage | `TicketDetail.messages[]` |
| POST | `/tickets/{id}/reply` | tickets.manage | `{ message }` (notifies customer in Telegram) |
| PATCH | `/tickets/{id}/status` | tickets.manage | `{ status, priority? }` |

## Settings

| Method | Path | Permission | Notes |
| --- | --- | --- | --- |
| GET | `/settings` | settings.manage | `SettingOut[]`, secret values masked as `********` |
| PATCH | `/settings` | settings.manage | `{ values: { "key": "value" } }` |
| GET | `/settings/api-config` | settings.manage | `ApiConfigOut` |
| GET | `/settings/templates` | settings.manage | notification templates |
| PATCH | `/settings/templates/{id}` | settings.manage | `{ title?, body?, is_active? }` |

## Admin management (Owner only, logs need `logs.view`)

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/admins?page&page_size` | `Page<AdminOut>` |
| GET | `/admins/roles` | role + permission list |
| GET | `/permissions` | all known permission keys |
| POST | `/admins` | `{ telegram_id, username?, first_name?, last_name?, role, is_active, notes? }` |
| PATCH | `/admins/{id}` | `{ role?, is_active?, notes? }` |
| DELETE | `/admins/{id}` | deactivate (cannot target self) |
| GET | `/logs?action&admin_id&page&page_size` | audit trail |

Roles: `OWNER, SUPER_ADMIN, PRODUCT_ADMIN, ORDER_ADMIN, FINANCE_ADMIN, SUPPORT_ADMIN`.

## Backups (Owner only)

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/backups` | `BackupResult[]` |
| POST | `/backups` | create JSON snapshot |
| GET | `/backups/{filename}` | download |

## Error format

```json
{ "detail": "Pesan kesalahan", "code": "not_found" }
```

`code` may be one of `not_found, validation_error, conflict, unauthorized, forbidden,
product_unavailable, order_state_error, payment_error, invalid_webhook_signature, out_of_stock`.
