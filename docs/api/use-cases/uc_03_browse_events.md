# UC03 — Browse Events

```mermaid
sequenceDiagram
    participant U as User
    participant CAT as Catalog

    U->>CAT: GET /organisations
    CAT-->>U: List of organisations

    U->>CAT: GET /organisations/{id}/venues
    CAT-->>U: List of venues

    U->>CAT: GET /venues/{id}/events
    CAT-->>U: List of events

    U->>CAT: GET /events/{id}
    CAT-->>U: Event details

    U->>CAT: GET /events/{id}/ticket-types
    CAT-->>U: Available ticket types and pricing
```
