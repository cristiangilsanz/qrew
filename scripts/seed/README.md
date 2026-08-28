# Seed

Loads the local database with a catalogue of fixtures that reaches every state the product
supports.

```bash
just db-seed
just db-truncate
```

Identifiers derive from a fixed namespace and timestamps hang off the moment it runs, so
two runs leave the database in the same shape with the deadlines always fresh: a
reservation about to expire still has minutes left, and an event that is on now still is.

## Accounts

All of them share the password `Password1!`.

| Account | Email |
|---|---|
| Admin | `admin@qrew.test` |
| Manager | `manager@qrew.test` |
| Member | `member@qrew.test` |
| User A | `user-a@qrew.test` |
| User B | `user-b@qrew.test` |
| User C | `user-c@qrew.test` |

Admin owns Org A, holds tickets in every state, sells and buys on the market and carries a
payment of each outcome, so almost any screen can be reached without switching accounts.

## Events

| Event | State |
|---|---|
| Event A | Published, on sale |
| Event B | Published, sale not open |
| Event C | Ongoing |
| Event D | Draft |
| Event E | Cancelled |
| Event F | Published, queue required |
| Event G | Finished |
