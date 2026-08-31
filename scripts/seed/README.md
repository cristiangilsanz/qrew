# Seed the Database

Use the database seed command to populate the local database with a catalogue of fixtures covering all supported product states.

Run:

    just db-seed

This creates the following accounts, which between them cover every state a real one can be in:

| Email | Platform role | Organisation | Identity check |
|---|---|---|---|
| `admin@qrew.dev` | Administrator | Owner of org-a | Approved |
| `manager@qrew.dev` | User | Manager of org-a, owner of org-b | Approved |
| `member@qrew.dev` | User | Member of org-a | Approved |
| `user-a@qrew.dev` | User | — | Approved |
| `user-b@qrew.dev` | User | — | Approved |
| `user-c@qrew.dev` | User | — | Never submitted, email and phone unverified |
| `user-d@qrew.dev` | User | — | Waiting for review |
| `user-e@qrew.dev` | User | — | Rejected, carries a foreign document |

All seeded accounts use the same password:

    Password1!

> Note: These credentials are intended for local development and testing only.

## Reset the Database

To remove the seeded data and truncate the database, run:

    just db-truncate
