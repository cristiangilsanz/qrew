# Scenario view

> [!NOTE]
> The scenario view illustrates key system behaviours end to end, demonstrating how the architectural layers collaborate under realistic conditions.

The following situations present representative sequences that illustrate how the architectural layers collaborate under realistic conditions, covering the 3 core flows of the system. Every step traces a call that exists in the code, and every subject named is one from the [subject registry](../apps/api/messaging/subjects.md). Where a service publishes a domain event, it does not touch the broker inside the request: it writes a row into its `<schema>.event_outbox` table in the same transaction as the change, and a cron job on the matching arq worker publishes it a minute later at the latest. Audit records and the WebSocket fanout are the exception, and go straight to NATS.

**User Registration**

The following sequence traces the full account creation flow, from the initial client request through external verification, the notification queue and the outbox that announces the new account. Two things are worth reading closely. The verification email and the phone OTP are not domain events: they are rows in `identity.notifications` written in their own transaction, enqueued straight onto the arq queue in Redis, and delivered later by `notification.deliver`. They are therefore already committed and queued before the user row itself commits. And the audit record, published directly rather than through the outbox, drags a `ws.fanout.v1` message with it addressed to `me.{user_id}`, a channel the brand new account has nobody connected to yet.

<div align="center">

```mermaid
sequenceDiagram
    autonumber
    participant App as Mobile App
    participant GW as API Gateway
    participant ID as Identity
    participant TS as Cloudflare Turnstile
    participant HI as HIBP
    participant PG as PostgreSQL
    participant RE as Redis
    participant NA as NATS JetStream
    participant IW as Identity Arq Worker
    participant SM as SMTP
    participant TW as Twilio
    participant SW as Sales Worker

    App->>GW: POST /api/identity/v1/auth/registration/
    GW->>ID: Forward, matched as a public route
    ID->>TS: siteverify the challenge token with the caller's IP
    TS-->>ID: success flag
    ID->>PG: Reject if the email or the phone number is taken
    ID->>HI: GET /range/{SHA-1 prefix} with Add-Padding
    HI-->>ID: Padded suffix list
    ID->>ID: Reject if the SHA-1 suffix appears in the list
    ID->>PG: Insert the user with the Argon2id hash and the hashed email token and OTP
    ID->>PG: Insert the two notification rows in their own transaction
    ID->>RE: Enqueue notification.deliver twice onto qrew:jobs:identity
    ID->>NA: Publish audit.events.v1 (REGISTER) and ws.fanout.v1 on me.{user_id}
    ID->>PG: Record identity.user.registered.v1 in identity.event_outbox
    ID-->>GW: 201 Created, committing the user and the outbox row together
    GW-->>App: 201 Created
    RE-->>IW: notification.deliver
    IW->>SM: Send the account verification email
    IW->>TW: Send the phone verification OTP
    IW->>PG: identity.event_outbox.drain claims the pending rows
    IW->>NA: Publish identity.user.registered.v1
    NA-->>SW: Project the account age for the fraud engine
```

</div>

**Ticket Purchase**

The following sequence traces the full purchase flow, from the reservation through holder naming, the PaymentIntent, the Stripe webhook and the issuance of the tickets. There is no order resource and no hosted Stripe Checkout page: the buyer confirms the intent in the app with the Payment Element and the client secret Payments returns. Capacity is not defended by the Redis lock, which is scoped per user and per event, but by a `SELECT ... FOR UPDATE NOWAIT` on each ticket type inventory row. The tickets themselves are created empty on the reservation and only transition to `issued` once the payment settles, so the chain from webhook to issued ticket crosses two outboxes and three workers. Nothing is pushed to the buyer at the end: the app has to poll.

<div align="center">

```mermaid
sequenceDiagram
    autonumber
    participant App as Mobile App
    participant GW as API Gateway
    participant SA as Sales
    participant PG as PostgreSQL
    participant RE as Redis
    participant SD as Sales Arq Worker
    participant NA as NATS JetStream
    participant TW as Ticketing Worker
    participant PA as Payments
    participant ST as Stripe
    participant PD as Payments Worker
    participant SW as Sales Worker

    App->>GW: POST /api/sales/v1/events/{event_id}/reserve
    GW->>SA: Forward with x-authenticated-user-id
    SA->>PG: Score the purchase against the fraud signals
    SA->>RE: Acquire redlock event:{event_id}:reserve:{user_id}
    SA->>PG: Lock each ticket type inventory row FOR UPDATE NOWAIT
    SA->>PG: Insert the reservation and its items, draw down the reserved counts
    SA->>NA: Publish audit.events.v1 (RESERVATION_CREATED)
    SA->>PG: Record sales.reservation.created.v1 in sales.event_outbox
    SA-->>App: 201 Created with the reservation id and its expiry
    SD->>PG: sales.outbox.drain claims the row
    SD->>NA: Publish sales.reservation.created.v1
    NA-->>TW: ticketing-sales-handler consumes it
    TW->>PG: Create one ticket per seat in state reserved
    App->>GW: PUT /api/sales/v1/reservations/{id}/holders with a name and DNI per seat
    GW->>SA: Upsert the holders against the open reservation
    App->>GW: POST /api/payments/v1/reservations/{id}/payment
    GW->>PA: Forward with x-authenticated-user-id
    PA->>SA: POST /v1/billing/reservations/{id}/charge with X-Internal-Key
    SA-->>PA: amount_cents and currency, or 410 if the hold expired
    PA->>ST: Create the PaymentIntent, keyed reservation:{id}:{payment_id}
    ST-->>PA: Intent id and client secret
    PA->>PG: Store the payment with the client secret encrypted
    PA->>PG: Record payments.payment.initiated.v1 in payments.event_outbox
    PA-->>App: 201 Created with the client secret
    App->>ST: confirmPayment through the Stripe Payment Element
    ST->>GW: POST /api/payments/v1/payments/webhook (payment_intent.succeeded)
    GW->>PA: Forward, matched as a public route
    PA->>PA: Verify the signature with stripe.Webhook.construct_event
    PA->>RE: Claim the Stripe event id with SET NX, or answer duplicate
    PA->>PG: Mark the payment succeeded, record payments.payment.succeeded.v1
    PA-->>ST: 200 OK
    PD->>NA: payments.outbox.drain publishes payments.payment.succeeded.v1
    NA-->>SW: sales-payment-handler consumes it
    SW->>RE: Acquire redlock reservation:{id}:lifecycle
    SW->>PG: Mark the reservation paid, record sales.reservation.paid.v1 with its holders
    SD->>NA: sales.outbox.drain publishes sales.reservation.paid.v1
    NA-->>TW: ticketing-sales-handler consumes it
    TW->>RE: Acquire redlock reservation:{id}:tickets
    TW->>PG: Transition every reserved ticket to issued and attach its holder
    TW->>NA: Publish audit.events.v1 (TICKET_STATE_CHANGED) per ticket
    TW->>PG: Record ticketing.ticket.state_changed in ticketing.event_outbox
```

</div>

**Entry Scanning**

The following sequence traces the admission flow, starting one step earlier than the door: the holder's app mints a short-lived QR from Ticketing, which is where the gate checks live. The geofence is one of those checks, and it is enforced when the QR is minted, not when it is scanned. Entry itself validates the signed QR against its own projections, claims the `jti` in Redis to stop a replay, and then makes the one synchronous call it needs, asking Ticketing to mark the ticket used. Entry publishes no domain event, only an audit record and the fanout the Gateway forwards to the organiser console. The scan path reads only `ticket_contexts`. The other two projections, `event_contexts` and `organisation_member_contexts`, serve a different question and a different caller: they are what lets Entry decide whether the organiser asking for a scanner token belongs to the event, which is the check that used to be an HTTP call to Catalog.

<div align="center">

```mermaid
sequenceDiagram
    autonumber
    participant App as Holder App
    participant Scan as Scanner Device
    participant GW as API Gateway
    participant TI as Ticketing
    participant EN as Entry
    participant PG as PostgreSQL
    participant RE as Redis
    participant NA as NATS JetStream
    participant AW as Audit Worker
    participant Org as Organiser Console

    App->>GW: GET /api/ticketing/v1/tickets/{ticket_id}/qr with latitude and longitude
    GW->>TI: Forward with x-authenticated-user-id
    TI->>PG: Load the ticket, its venue context and the device context
    TI->>TI: Gate check on state, reassertion, attestation, geofence radius and time window
    TI->>PG: Move the ticket from issued to scanning, record ticketing.ticket.state_changed
    TI-->>App: ES256 QR token carrying ticket_id, event_id, venue_id, device_id and jti
    Scan->>GW: POST /api/entry/v1/entry/validate with the QR and a scanner bearer
    GW->>EN: Forward with x-authenticated-scanner-id
    EN->>PG: Load the scanner row
    EN->>EN: Verify the QR signature, audience and expiry
    EN->>EN: Match event_id and venue_id against the scanner token claims
    EN->>RE: SET entry:jti:{jti} NX, rejecting a replay
    EN->>PG: Read ticket_contexts, requiring state issued or scanning
    EN->>RE: Acquire redlock entry:scan:{ticket_id}
    EN->>TI: POST /v1/admission/{ticket_id}/use with X-Internal-Key
    TI->>PG: Transition the ticket to redeemed, record ticketing.ticket.state_changed
    TI-->>EN: 204 No Content
    EN->>NA: Publish audit.events.v1 (ENTRY_VALIDATED)
    EN->>NA: Publish ws.fanout.v1 on entry.{event_id}
    EN->>PG: Append the entry attempt row with its outcome and latency
    EN-->>GW: 200 OK with allowed, ticket id and holder
    GW-->>Scan: 200 OK
    NA-->>AW: audit-events-handler consumes the record
    AW->>PG: Append it to the hash chain under an advisory lock
    NA-->>GW: gateway-fanout-handler consumes the fanout message
    GW-->>Org: entry.validated over the WebSocket
```

</div>
