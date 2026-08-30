# Seed the Database

Use the database seed command to populate the local database with a catalogue of fixtures covering all supported product states.

Run:

    just db-seed

This creates the following test accounts:

| Role    | Email              |
|---------|--------------------|
| Admin   | admin@qrew.test    |
| Manager | manager@qrew.test  |
| Member  | member@qrew.test   |
| User A  | user-a@qrew.test   |
| User B  | user-b@qrew.test   |
| User C  | user-c@qrew.test   |

All seeded accounts use the same password:

    Password1!

> Note: These credentials are intended for local development and testing only.

## Reset the Database

To remove the seeded data and truncate the database, run:

    just db-truncate
