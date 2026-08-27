# Seed

Loads the local database with a catalogue of fixtures that reaches every state the product
supports. It is meant for development and for manual testing, never for a deployment.

```bash
just db-seed          # wipe and load
just db-seed-keep     # load without wiping
just db-truncate      # wipe only
```

## How it is built

| File | Responsibility |
|---|---|
| `dataset.py` | Declares the fixtures. This is the only file to touch to add a scenario |
| `writers/*.py` | One per schema, turns the declaration into rows |
| `clock.py` | Every timestamp hangs off the moment the seeder runs |
| `ids.py` | Identifiers derived from a fixed namespace, so two runs land on the same rows |
| `crypto.py` | Encryption, hashing and password derivation, mirroring the services |
| `reset.py` | Truncates every application table in the order the keys demand |

Because identifiers are deterministic and timestamps are relative, running it twice leaves
the database in the same shape with the deadlines always fresh: a reservation about to
expire still has minutes left, and an event that is on now still is.

## Accounts

All of them share the password `Password1!`.

| Account | Email | What it is for |
|---|---|---|
| Admin | `admin@qrew.test` | The account to test with. Owns Org A, holds tickets in every state, sells and buys on the market, and has a payment of each outcome |
| Manager | `manager@qrew.test` | Owns Org B, to check that an organisation only sees its own events |
| Member | `member@qrew.test` | Staff of Org A, registered the gate scanners |
| User A | `user-a@qrew.test` | Trades with Admin on the resale market |
| User B | `user-b@qrew.test` | Claims a listing and waits in the admission queue |
| User C | `user-c@qrew.test` | Fresh account, unverified and without KYC, for the empty states |

## Events

| Event | State | Why it exists |
|---|---|---|
| Event A | Published, on sale | The happy path, with a sold-out tier, a general tier and a VIP tier |
| Event B | Published, sale not open | The countdown before a sale opens |
| Event C | Ongoing | Validation at the gate, at Venue C |
| Event D | Draft | Visible only inside its organisation |
| Event E | Cancelled | Cancellation and its consequences |
| Event F | Published, queue required | The admission queue, opening in fifteen minutes |
| Event G | Finished | History, refunds and redeemed tickets |
