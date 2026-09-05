# Payments Event Contracts

Published to stream `PAYMENTS`. All events wrap the [EventEnvelope](../../messaging/messaging.md#eventenvelope). Schemas live in [`packages/contracts/openapi/payments/events/`](../../../../../../packages/contracts/openapi/payments/events/).

A payment settles either a reservation or a resale assignment, so `reservation_id` and `market_assignment_id` are alternatives: whichever the payment is not about is absent from the payload. The same rule applies to `user_id`, which is absent when the payment has no user on file. A consumer must therefore read these fields as optional and never assume the key is there.


## `payments.payment.initiated.v1`

Emitted when a Stripe PaymentIntent is created and the client secret is returned to the frontend. No service subscribes to it.

| Field | Type | Description |
|---|---|---|
| `payment_id` | UUID | Internal payment record |
| `user_id` | UUID | Payer |
| `amount_cents` | int | Amount in smallest currency unit |
| `currency` | string | ISO 4217 currency code |
| `reservation_id` | UUID | Reservation being paid, on the reservation variant |
| `market_assignment_id` | UUID | Resale assignment being paid, on the market variant |


## `payments.payment.succeeded.v1`

Emitted when a Stripe webhook confirms payment. Sales confirms the reservation or the assignment. Identity logs the event.

| Field | Type | Description |
|---|---|---|
| `payment_id` | UUID | Internal payment record |
| `user_id` | UUID | Payer, absent when the payment has no user on file |
| `reservation_id` | UUID | Reservation paid, on the reservation variant |
| `market_assignment_id` | UUID | Resale assignment paid, on the market variant |
| `payment_intent_id` | string | Stripe PaymentIntent ID, only on the market variant |


## `payments.payment.failed.v1`

Emitted when Stripe reports a payment failure.

| Field | Type | Description |
|---|---|---|
| `payment_id` | UUID | Internal payment record |
| `user_id` | UUID | Payer, absent when the payment has no user on file |
| `reservation_id` | UUID | Reservation the payment belonged to, on the reservation variant |
| `market_assignment_id` | UUID | Resale assignment the payment belonged to, on the market variant |
| `failure_code` | string or null | Failure code from Stripe |
| `failure_message` | string or null | Failure message from Stripe |


## `payments.payment.refunded.v1`

Emitted on every refund Stripe reports, whether or not it covers the full amount. Sales cancels or flags the associated reservation.

| Field | Type | Description |
|---|---|---|
| `payment_id` | UUID | Internal payment record |
| `user_id` | UUID | Payer, absent when the payment has no user on file |
| `reservation_id` | UUID | Reservation the payment belonged to, on the reservation variant |
| `market_assignment_id` | UUID | Resale assignment the payment belonged to, on the market variant |
| `amount_refunded_cents` | int | Amount refunded |
| `amount_total_cents` | int | Original amount charged |
| `is_full_refund` | bool | Whether the refund covers the whole charge |


## `payments.chargeback.opened.v1`

Emitted when Stripe notifies of a chargeback dispute.

| Field | Type | Description |
|---|---|---|
| `payment_id` | UUID | Disputed payment |
| `user_id` | UUID | Payer, absent when the payment has no user on file |
| `reservation_id` | UUID | Reservation the payment belonged to, on the reservation variant |
| `market_assignment_id` | UUID | Resale assignment the payment belonged to, on the market variant |


## `payments.chargeback.closed.v1`

Emitted when a chargeback dispute is resolved.

| Field | Type | Description |
|---|---|---|
| `payment_id` | UUID | Disputed payment |
| `user_id` | UUID | Payer, absent when the payment has no user on file |
| `reservation_id` | UUID | Reservation the payment belonged to, on the reservation variant |
| `market_assignment_id` | UUID | Resale assignment the payment belonged to, on the market variant |
