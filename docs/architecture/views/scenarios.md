# Scenario view

> [!NOTE]
> The scenario view illustrates key system behaviours end to end, demonstrating how the architectural layers collaborate under realistic conditions.

The following situations present representative sequences that illustrate how the architectural layers collaborate under realistic conditions, covering the 3 core flows of the system.

**User Registration**

The following sequence traces an example of the full account creation flow, from the initial client request through external verification and asynchronous email dispatch.

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
    participant NA as NATS JetStream
    participant RE as Redis
    participant IW as Identity Worker
    participant TW as Twilio

    App->>GW: POST /auth/register (email, password, challenge token)
    GW->>ID: Forward registration request
    ID->>TS: Verify Turnstile challenge token
    TS-->>ID: Token valid
    ID->>HI: k-anonymity prefix check (SHA-1 prefix)
    HI-->>ID: Prefix match list
    ID->>ID: Reject if password hash suffix found in list
    ID->>PG: Hash password with Argon2id and persist account
    ID->>NA: Publish UserRegistered event
    ID-->>GW: 201 Created
    GW-->>App: 201 Created
    NA-->>IW: Consume UserRegistered event
    IW->>RE: Enqueue verification email job
    IW->>TW: Dispatch verification email
```

</div>

**Ticket Purchase**

The following sequence traces the full ticket purchase flow, from order submission through distributed lock acquisition, payment initiation, webhook confirmation, and asynchronous ticket issuance.

<div align="center">

```mermaid
sequenceDiagram
    autonumber
    participant App as Mobile App
    participant GW as API Gateway
    participant SA as Sales
    participant RE as Redis
    participant PG as PostgreSQL
    participant NA as NATS JetStream
    participant PW as Payments Worker
    participant ST as Stripe
    participant PA as Payments
    participant TW as Ticketing Worker

    App->>GW: POST /orders (tier ID, quantity)
    GW->>SA: Forward order request (with X-User-ID header)
    SA->>RE: Acquire distributed lock on tier capacity (Redlock)
    RE-->>SA: Lock acquired
    SA->>PG: Validate tier availability and create order record
    SA->>RE: Release distributed lock
    SA->>NA: Publish OrderCreated event
    SA-->>GW: 202 Accepted (order ID)
    GW-->>App: 202 Accepted (order ID)
    NA-->>PW: Consume OrderCreated event
    PW->>ST: Create Stripe checkout session
    ST-->>PW: Checkout session URL
    PW->>App: Push checkout URL via WebSocket
    App->>ST: Complete payment on Stripe-hosted page
    ST->>GW: POST /webhooks/stripe (PaymentIntent confirmed)
    GW->>PA: Forward webhook
    PA->>NA: Publish PaymentConfirmed event
    NA-->>TW: Consume PaymentConfirmed event
    TW->>PG: Generate QR code and persist ticket
    TW->>App: Push ticket issuance confirmation via WebSocket
```

</div>

**Entry Scanning**

The following sequence traces the admission flow, from QR code scan at the venue through capacity enforcement, event publishing, and real-time confirmation.

<div align="center">

```mermaid
sequenceDiagram
    autonumber
    participant Org as Organiser App
    participant GW as API Gateway
    participant EN as Entry
    participant RE as Redis
    participant PG as PostgreSQL
    participant NA as NATS JetStream
    participant AW as Audit Worker

    Org->>GW: POST /entry/scan (QR code payload)
    GW->>EN: Forward scan request (with X-User-ID header)
    EN->>PG: Validate ticket against local read model
    PG-->>EN: Ticket valid and not yet used
    EN->>RE: Acquire distributed lock on venue capacity (Redlock)
    RE-->>EN: Lock acquired
    EN->>PG: Increment venue capacity counter and persist EntryGranted record
    EN->>RE: Release distributed lock
    EN->>NA: Publish EntryGranted event
    EN-->>GW: 200 OK (admission result)
    GW-->>Org: 200 OK (admission result)
    NA-->>AW: Consume EntryGranted event
    AW->>PG: Append immutable audit log entry
```

</div>
