# Payments Event Contracts

Published to stream `PAYMENTS`. All events wrap the [EventEnvelope](../README.md#eventenvelope).

---

## `payments.payment.initiated.v1`

Emitted when a Stripe PaymentIntent is created and the client secret is returned to the frontend.

| Field | Type | Description |
|---|---|---|
| `payment_id` | UUID | Internal payment record |
| `reservation_id` | UUID | Associated reservation |
| `amount_cents` | int | Amount in smallest currency unit |
| `currency` | string | ISO 4217 currency code |
| `stripe_intent_id` | string | Stripe PaymentIntent ID |

---

## `payments.payment.succeeded.v1`

Emitted when a Stripe webhook confirms payment. Sales confirms the reservation; Identity logs the event.

| Field | Type | Description |
|---|---|---|
| `payment_id` | UUID | Internal payment record |
| `reservation_id` | UUID | Associated reservation |
| `amount_cents` | int | Amount paid |
| `currency` | string | ISO 4217 currency code |

---

## `payments.payment.failed.v1`

Emitted when Stripe reports a payment failure.

| Field | Type | Description |
|---|---|---|
| `payment_id` | UUID | Internal payment record |
| `reservation_id` | UUID | Associated reservation |
| `reason` | string | Failure reason from Stripe |

---

## `payments.payment.refunded.v1`

Emitted when a refund is processed. Sales cancels or flags the associated reservation.

| Field | Type | Description |
|---|---|---|
| `payment_id` | UUID | Internal payment record |
| `reservation_id` | UUID | Associated reservation |
| `refund_cents` | int | Amount refunded |

---

## `payments.chargeback.opened.v1`

Emitted when Stripe notifies of a chargeback dispute.

| Field | Type | Description |
|---|---|---|
| `payment_id` | UUID | Disputed payment |
| `reservation_id` | UUID | Associated reservation |
| `dispute_id` | string | Stripe dispute ID |

---

## `payments.chargeback.closed.v1`

Emitted when a chargeback dispute is resolved.

| Field | Type | Description |
|---|---|---|
| `payment_id` | UUID | Disputed payment |
| `reservation_id` | UUID | Associated reservation |
| `dispute_id` | string | Stripe dispute ID |
