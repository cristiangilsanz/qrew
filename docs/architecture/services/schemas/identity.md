# Identity — Database Schema

```mermaid
erDiagram
    users {
        UUID id PK
        bytes full_name_ciphertext
        bytes email_ciphertext
        string email_hash UK
        bytes phone_number_ciphertext
        string phone_number_hash UK
        string hashed_password
        bool email_verified
        bool phone_number_verified
        string kyc_status
        bool is_active
        bool is_admin
        timestamp created_at
        timestamp updated_at
        timestamp deleted_at
    }

    sessions {
        UUID id PK
        UUID user_id FK
        string jti UK
        string ip_address
        text user_agent
        string device_fingerprint
        UUID device_id FK
        timestamp created_at
        timestamp last_used_at
        timestamp last_asserted_at
    }

    devices {
        UUID id PK
        UUID user_id FK
        string name
        bytes public_key UK
        string attestation_platform
        timestamp created_at
        timestamp last_seen_at
        timestamp revoked_at
        timestamp attested_at
    }

    device_fingerprints {
        UUID id PK
        UUID user_id FK
        string fingerprint_hash
        string ip_address
        text user_agent
        int account_count_at_seen
        timestamp seen_at
    }

    passkey_credentials {
        UUID id PK
        UUID user_id FK
        bytes credential_id UK
        bytes public_key
        int sign_count
        string aaguid
        string name
        timestamp last_used_at
        timestamp created_at
    }

    notifications {
        UUID id PK
        UUID user_id
        string channel
        string template_key
        bytes destination_ciphertext
        jsonb payload
        string status
        int attempt_count
        timestamp created_at
        timestamp sent_at
    }

    outbox {
        UUID id PK
        string aggregate_type
        string aggregate_id
        string job_name
        jsonb payload
        int attempt_count
        timestamp created_at
        timestamp dispatched_at
        timestamp next_attempt_at
        string dlq_reason
    }

    audit_events {
        UUID id PK
        UUID actor_id
        string action
        string entity_type
        string entity_id
        string ip_address
        jsonb payload
        bytes prev_hash
        bytes hash
        timestamp created_at
    }

    users ||--o{ sessions : "has"
    users ||--o{ devices : "has"
    users ||--o{ device_fingerprints : "tracks"
    users ||--o{ passkey_credentials : "has"
    users ||--o{ notifications : "receives"
    devices ||--o{ sessions : "linked to"
```
