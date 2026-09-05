# Decision Records

Every structural decision behind the system answers to a known pattern. They are listed from
the general to the particular, and each line says what the pattern does, not how QREW applies
it, which belongs to the document covering that area.


## Style & Decomposition

<div align="center">

| Pattern | Function |
|---|---|
| ***Microservices*** | Splits the system into independently deployable units, each owning its data and delimited by a business responsibility |
| ***Event-Driven Architecture*** | Relates those units by publishing what happens to them instead of calling one another |
| ***Choreography*** | Leaves the sequence without a central coordinator, so each unit reacts to what it receives |
| ***Layered Architecture*** | Orders the code in layers where each one rests only on the layer below |
| ***Bounded Context*** | Fixes the boundary within which a model and its vocabulary have a single meaning |
| ***Shared Library*** | Extracts into its own library whatever several units must solve the same way |
| ***Monorepo*** | Keeps all the code in one repository with a common version and release cycle |
| ***Thin Client*** | Leaves presentation to the device and every business rule to the server |
| ***Dependency Injection*** | Hands each piece its collaborators from outside instead of letting it build them |

</div>

## Communication & Integration

<div align="center">

| Pattern | Function |
|---|---|
| ***API Gateway*** | Concentrates entry from the outside in a single point that authenticates and routes |
| ***Publish–Subscribe Messaging*** | Delivers each message to every interested party without the sender knowing them |
| ***Transactional Outbox*** | Writes the message in the same transaction as the change so both commit together |
| ***Polling Publisher*** | Delivers pending messages by reading in batches the table where they are stored |
| ***Idempotent Receiver*** | Discards the repetition of a message that has already been processed |
| ***Competing Consumers*** | Shares the messages of a channel among several instances without duplicating work |
| ***Durable Subscriber*** | Keeps for an absent subscriber whatever was published while it was down |
| ***Dead Letter Queue*** | Sets aside the message that exhausts its retries so it can be reviewed separately |
| ***Saga*** | Resolves an operation spanning several units as a sequence of local steps |
| ***Compensating Transaction*** | Undoes with an inverse action what a previous step had committed |
| ***Anti-Corruption Layer*** | Translates the model of a foreign system so it does not contaminate the local one |
| ***Remote Procedure Invocation*** | Resolves in the same call whatever result is needed to carry on |
| ***Server-Sent Events*** | Keeps an open channel through which the server notifies without being asked |
| ***Retry with Exponential Backoff*** | Repeats a failed attempt, spacing each new try further than the last |
| ***Timeout*** | Abandons the wait for an answer once the fixed deadline has passed |

</div>

## Data & Consistency

<div align="center">

| Pattern | Function |
|---|---|
| ***Database per Service*** | Reserves for each unit its own store, out of reach of the others |
| ***Event-Carried State Transfer*** | Keeps in the receiver a copy of the foreign data it needs, fed by the messages it consumes |
| ***Eventual Consistency*** | Accepts that copies converge with delay instead of demanding immediate agreement |
| ***Distributed Lock*** | Serialises access to a shared resource across separate processes |
| ***Pessimistic Locking*** | Locks the row while it is being worked on so no one else takes it |
| ***Cache-Aside*** | Reads the cache first and goes to the origin only when the value is missing |
| ***Keyset Pagination*** | Walks a long list from the last row delivered rather than by page number |
| ***Append-Only Log*** | Allows records to be added, never modified or deleted |
| ***Hash Chain*** | Chains each record with the digest of the previous one, so tampering shows |
| ***Repository*** | Isolates access to the store in one piece and returns domain objects |
| ***Data Mapper*** | Translates between domain classes and tables without the former knowing the latter |
| ***Unit of Work*** | Groups in a single transaction everything an operation writes |
| ***Data Transfer Object*** | Declares the exact shape of what comes in and goes out, apart from the internal model |
| ***Schema Migrations*** | Versions the evolution of the schema in ordered, reproducible steps |

</div>

## Reliability & Operation

<div align="center">

| Pattern | Function |
|---|---|
| ***Bulkhead*** | Isolates resources by area so the saturation of one does not drag the rest |
| ***Rate Limiting*** | Bounds how many requests one origin may make within a time window |
| ***Health Check API*** | Exposes an endpoint stating whether the piece is alive and ready to serve |
| ***Externalized Configuration*** | Takes from the environment whatever changes between deployments |
| ***Scheduled Job*** | Runs on a clock whatever does not stem from a request |
| ***Structured Logging*** | Emits each event as a record with fields, readable by a machine |
| ***Correlation ID*** | Marks the request with an identifier that follows it across every piece |
| ***Context Propagation*** | Carries the trace context into the message so the thread survives the broker |
| ***Distributed Tracing*** | Reconstructs the full path of an operation through everything it crosses |

</div>

## Security & Privacy

<div align="center">

| Pattern | Function |
|---|---|
| ***Access Token*** | Proves on each request who is calling, without asking for the password again |
| ***Refresh Token Rotation*** | Renews the credential by issuing a new one and voiding the previous immediately |
| ***WebAuthn Passkey*** | Replaces the password with a cryptographic key held by the device |
| ***Time-Based One-Time Password*** | Requires a code that expires in seconds and derives from a shared secret |
| ***Hashed Secret Storage*** | Stores only the digest of the secret, so stealing it does not allow its use |
| ***Field-Level Encryption*** | Encrypts sensitive data column by column rather than the whole volume |
| ***Pseudonymisation*** | Replaces identifying data with a digest that allows comparison without disclosure |
| ***Constant-Time Comparison*** | Compares secrets in a time that does not depend on their content |
| ***Account Lockout*** | Delays or closes access after a run of failed attempts |
| ***Content Security Policy*** | Declares in the response what the browser is allowed to do with it |
| ***Network Segmentation*** | Splits the deployment into separate networks so a piece only reaches what its job requires |
| ***Zero Trust*** | Verifies every request without granting trust because of where it comes from |

</div>

## Client

<div align="center">

| Pattern | Function |
|---|---|
| ***File-Based Routing*** | Derives the map of screens from the file structure of the project |
| ***Route Guard*** | Checks before loading the screen whether the caller is allowed to see it |
| ***Query Cache*** | Stores the server response under a key and reuses it while it stays valid |
| ***Stale-While-Revalidate*** | Serves the data at hand while checking in the background whether it changed |
| ***Container and Presentational Components*** | Separates the piece that decides from the piece that only draws |
| ***HTTP Interceptor*** | Steps into the response to renew the credential and repeat the call unnoticed |
| ***Platform Adapter*** | Wraps the native function behind a single interface for the rest of the code |
| ***Error Boundary*** | Contains the failure of one branch of the interface without bringing the app down |
| ***Skeleton Screen*** | Shows the frame of the content while the data is on its way |
| ***Externalized Strings*** | Keeps visible text out of the code so it can be served in several languages |

</div>
