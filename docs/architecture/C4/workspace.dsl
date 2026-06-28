workspace "Qrew" "Event ticketing platform." {

    model {

        user = person "User" "End user browsing events and purchasing tickets."
        scanner = person "Scanner Device" "Gate device operated at venue entry points." {
            tags "External"
        }

        stripe = softwareSystem "Stripe" "Third-party payment processor." {
            tags "External"
        }

        qrew = softwareSystem "Qrew" "Event ticketing platform handling authentication, catalog, sales, payments, ticketing, and gate entry." {

            gateway = container "Gateway" "Authenticates WebSocket connections and forwards NATS messages to clients." "Python / FastAPI" {
                gwApi      = component "HTTP API"       "WebSocket endpoint that accepts and authenticates incoming connections." "FastAPI"
                gwAuth     = component "Auth"           "Verifies user and scanner JWTs on connection establishment." "Python"
                gwChannels = component "Channel Handler" "Routes connections to named channels and resolves relevant NATS subjects." "Python"
                gwBridge   = component "NATS Bridge"    "Subscribes to NATS subjects on behalf of the client and forwards messages over WebSocket." "Python"
            }

            identity = container "Identity" "Authentication, users, devices, and KYC." "Python / FastAPI" {
                idApi    = component "HTTP API"      "REST endpoints for authentication, users, devices, and KYC." "FastAPI"
                idDomain = component "Domain"        "Business logic for authentication flows and token issuance." "Python"
                idOutbox = component "Outbox Table"  "Stores events atomically with business writes to guarantee delivery." "PostgreSQL"
                idWorker = component "Outbox Worker" "Drains the transactional outbox and publishes domain events to NATS." "arq"
            }

            catalog = container "Catalog" "Organisations, venues, events, and ticket types." "Python / FastAPI" {
                catApi    = component "HTTP API"     "REST endpoints for organisations, venues, events, and ticket types." "FastAPI"
                catDomain = component "Domain"       "Business logic for catalog management and event availability." "Python"
                catWorker = component "Event Worker" "Consumes identity events to maintain local user and organisation projections." "Python"
            }

            sales = container "Sales" "Reservations, queue management, and fraud detection." "Python / FastAPI" {
                salApi    = component "HTTP API"     "REST endpoints for reservations, queue management, and fraud signals." "FastAPI"
                salDomain = component "Domain"       "Business logic for reservation lifecycle, queue, and fraud scoring." "Python"
                salWorker = component "Event Worker" "Consumes payment and identity events to update reservation state." "Python"
            }

            ticketing = container "Ticketing" "Ticket lifecycle and QR code minting." "Python / FastAPI" {
                tktApi    = component "HTTP API"     "REST endpoints for ticket lifecycle and QR code streaming." "FastAPI"
                tktDomain = component "Domain"       "Business logic for ticket minting and QR code generation." "Python"
                tktWorker = component "Event Worker" "Consumes sales and identity events to mint tickets and update projections." "Python"
            }

            payments = container "Payments" "Stripe integration and payment lifecycle." "Python / FastAPI" {
                payApi    = component "HTTP API" "REST endpoints for initiating payments and receiving Stripe webhooks." "FastAPI"
                payDomain = component "Domain"   "Payment intent creation, webhook verification, and outcome processing." "Python"
            }

            entry = container "Entry" "Scanner registration and ticket validation." "Python / FastAPI" {
                entApi    = component "HTTP API"     "REST endpoints for scanner registration and ticket scan submission." "FastAPI"
                entDomain = component "Domain"       "Ticket validation against local projections and scan recording." "Python"
                entWorker = component "Event Worker" "Consumes ticketing events to maintain local ticket state projections." "Python"
            }

            audit = container "Audit" "Append only audit log and chain integrity." "Python / FastAPI" {
                audApi        = component "HTTP API"         "Internal REST endpoint for querying the audit log." "FastAPI"
                audDomain     = component "Domain"           "Audit record persistence and cryptographic chain management." "Python"
                audSubscriber = component "Event Subscriber" "Subscribes to audit.events.v1 and forwards records to the domain." "Python"
                audVerifier   = component "Chain Verifier"   "Periodically verifies the cryptographic integrity of the audit chain." "arq"
            }

            postgres = container "PostgreSQL" "Primary durable datastore. One database per service." "Database" {
                tags "Database"
            }

            redis = container "Redis" "Distributed locks, idempotency keys, and rate limiting." "Cache" {
                tags "Database"
            }

            nats = container "NATS JetStream" "At least once event streaming with durable consumers." "Message Broker"
        }

        # System context relationships
        user    -> qrew   "Uses"                                     "HTTPS / WebSocket"
        scanner -> qrew   "Validates tickets and receives feedback"   "HTTPS / WebSocket"
        qrew    -> stripe "Creates payment intents"                   "HTTPS"
        stripe  -> qrew   "Delivers payment webhooks"                 "HTTPS"

        # Container relationships
        user    -> gateway  "Receives live updates"   "WebSocket"
        user    -> identity "Authenticates"           "HTTPS"
        user    -> catalog  "Browses catalog"         "HTTPS"
        user    -> sales    "Creates reservations"    "HTTPS"
        user    -> payments "Initiates payments"      "HTTPS"
        user    -> ticketing "Manages tickets"        "HTTPS"

        scanner -> gateway "Receives scan feedback"  "WebSocket"
        scanner -> entry   "Validates tickets"       "HTTPS"

        gateway  -> nats    "Subscribes to client subjects"       "NATS core"
        gateway  -> redis   "Rate limiting"

        identity -> nats    "Publishes domain events"             "NATS JetStream"
        identity -> postgres "Reads and writes"                  "SQL"
        identity -> redis   "Idempotency and rate limiting"

        catalog  -> nats    "Publishes and consumes events"       "NATS JetStream"
        catalog  -> postgres "Reads and writes"                  "SQL"
        catalog  -> redis   "Idempotency and rate limiting"

        sales    -> nats    "Publishes and consumes events"       "NATS JetStream"
        sales    -> postgres "Reads and writes"                  "SQL"
        sales    -> redis   "Idempotency, locks, and rate limiting"

        ticketing -> nats   "Publishes and consumes events"       "NATS JetStream"
        ticketing -> postgres "Reads and writes"                 "SQL"
        ticketing -> redis  "Idempotency and rate limiting"

        payments -> nats    "Publishes domain events"             "NATS JetStream"
        payments -> postgres "Reads and writes"                  "SQL"
        payments -> redis   "Idempotency and rate limiting"
        payments -> stripe  "Creates payment intents"            "HTTPS"
        stripe   -> payments "Delivers payment webhooks"         "HTTPS"

        entry    -> nats    "Publishes and consumes events"       "NATS JetStream"
        entry    -> postgres "Reads and writes"                  "SQL"
        entry    -> redis   "Idempotency and rate limiting"

        audit    -> nats    "Consumes audit events"              "NATS core"
        audit    -> postgres "Appends audit records"             "SQL"
        audit    -> redis   "Idempotency and rate limiting"

        # Component relationships — Identity
        user     -> idApi    "Calls"                        "HTTPS"
        idApi    -> idDomain "Delegates to"
        idDomain -> idOutbox "Writes events atomically"
        idDomain -> postgres "Reads and writes"
        idDomain -> redis    "Idempotency and rate limiting"
        idWorker -> idOutbox "Polls and drains"
        idWorker -> nats     "Publishes domain events"

        # Component relationships — Catalog
        user      -> catApi    "Calls"                        "HTTPS"
        catApi    -> catDomain "Delegates to"
        catDomain -> postgres  "Reads and writes"
        catDomain -> nats      "Publishes domain events"
        catDomain -> redis     "Idempotency and rate limiting"
        catWorker -> nats      "Consumes identity events"
        catWorker -> postgres  "Updates local projections"

        # Component relationships — Sales
        user      -> salApi    "Calls"                              "HTTPS"
        salApi    -> salDomain "Delegates to"
        salDomain -> postgres  "Reads and writes"
        salDomain -> nats      "Publishes domain events"
        salDomain -> redis     "Idempotency, locks, and rate limiting"
        salWorker -> nats      "Consumes payment and identity events"
        salWorker -> postgres  "Updates reservation state and projections"

        # Component relationships — Ticketing
        user      -> tktApi    "Calls"                        "HTTPS"
        tktApi    -> tktDomain "Delegates to"
        tktDomain -> postgres  "Reads and writes"
        tktDomain -> nats      "Publishes domain events"
        tktDomain -> redis     "Idempotency and rate limiting"
        tktWorker -> nats      "Consumes sales and identity events"
        tktWorker -> postgres  "Mints tickets and updates projections"

        # Component relationships — Payments
        user      -> payApi    "Initiates payment"            "HTTPS"
        stripe    -> payApi    "Delivers payment webhook"     "HTTPS"
        payApi    -> payDomain "Delegates to"
        payDomain -> stripe    "Creates payment intents"      "HTTPS"
        payDomain -> postgres  "Reads and writes"
        payDomain -> nats      "Publishes payment domain events"
        payDomain -> redis     "Idempotency and rate limiting"

        # Component relationships — Entry
        scanner   -> entApi    "Submits scan"                            "HTTPS"
        entApi    -> entDomain "Delegates to"
        entDomain -> postgres  "Reads projections and writes scan records"
        entDomain -> nats      "Publishes scan events"
        entDomain -> redis     "Idempotency and rate limiting"
        entWorker -> nats      "Consumes ticketing events"
        entWorker -> postgres  "Updates local ticket projections"

        # Component relationships — Audit
        audApi        -> audDomain     "Delegates to"
        audSubscriber -> nats          "Subscribes to audit.events.v1"
        audSubscriber -> audDomain     "Forwards received records"
        audDomain     -> postgres      "Appends audit records"
        audDomain     -> redis         "Idempotency and rate limiting"
        audVerifier   -> postgres      "Reads and verifies audit chain"

        # Component relationships — Gateway
        user       -> gwApi      "Connects"                "WebSocket"
        scanner    -> gwApi      "Connects"                "WebSocket"
        gwApi      -> gwAuth     "Authenticates connection"
        gwAuth     -> gwChannels "Routes to channel"
        gwChannels -> gwBridge   "Passes resolved subjects"
        gwBridge   -> nats       "Subscribes to subjects"
        gwApi      -> redis      "Rate limiting"
    }

    views {

        systemContext qrew "SystemContext" "C4 Level 1 — System Context" {
            include *
            autoLayout lr
        }

        container qrew "Containers" "C4 Level 2 — Container" {
            include *
            autoLayout lr
        }

        component identity "IdentityComponents" "C4 Level 3 — Identity" {
            include *
            autoLayout lr
        }

        component catalog "CatalogComponents" "C4 Level 3 — Catalog" {
            include *
            autoLayout lr
        }

        component sales "SalesComponents" "C4 Level 3 — Sales" {
            include *
            autoLayout lr
        }

        component ticketing "TicketingComponents" "C4 Level 3 — Ticketing" {
            include *
            autoLayout lr
        }

        component payments "PaymentsComponents" "C4 Level 3 — Payments" {
            include *
            autoLayout lr
        }

        component entry "EntryComponents" "C4 Level 3 — Entry" {
            include *
            autoLayout lr
        }

        component audit "AuditComponents" "C4 Level 3 — Audit" {
            include *
            autoLayout lr
        }

        component gateway "GatewayComponents" "C4 Level 3 — Gateway" {
            include *
            autoLayout lr
        }

        styles {
            element "Person" {
                shape Person
                background #08427B
                color #ffffff
            }
            element "External" {
                background #999999
                color #ffffff
            }
            element "Software System" {
                background #1168BD
                color #ffffff
            }
            element "Container" {
                background #438DD5
                color #ffffff
            }
            element "Component" {
                background #85BBF0
                color #000000
            }
            element "Database" {
                shape Cylinder
                background #438DD5
                color #ffffff
            }
        }
    }
}
