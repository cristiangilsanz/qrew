# UC07 — Scanner Registration

```mermaid
sequenceDiagram
    participant OP as Operator
    participant GW as Gateway
    participant ENT as Entry
    participant ID as Identity

    OP->>GW: POST /api/entry/v1/scanners (device name, venue id)
    GW->>GW: Verify JWT, inject X-Authenticated-User-Id
    GW->>ENT: Proxy POST /v1/scanners + X-Authenticated-User-Id
    ENT->>ENT: Create scanner record
    ENT->>ID: Request scanner JWT for device
    ID->>ID: Issue scanner-scoped JWT
    ID-->>ENT: Scanner token
    ENT-->>GW: Scanner details + token
    GW-->>OP: Scanner details + token

    Note over OP,ENT: Token provisioned to device
```
