# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly. **Do not open a public GitHub issue.**

Contact: **cristiangilsanz@gmail.com**

Include in your report:
- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested mitigations

We will acknowledge receipt within 48 hours and aim to resolve confirmed issues within 14 days.


## Scope

In scope:

- Authentication and authorisation bypasses
- JWT handling flaws: algorithm confusion, weak signing, missing validation
- PII exposure via encrypted fields or hashed lookups
- Ticket fraud or double-spend vulnerabilities
- Payment flow manipulation
- Injection vulnerabilities: SQL and command injection
- CORS or gateway misconfiguration allowing cross-origin abuse

Out of scope:

- Denial of service attacks
- Issues requiring physical access to a device
- Social engineering
- Third-party services such as Stripe, Twilio, and Resend. Report those directly to the vendor.


## Security Model

- All traffic flows through the API gateway, which validates JWT tokens before forwarding requests
- Access tokens use ES256 asymmetric signing. Services verify signatures and never issue tokens.
- PII including names, emails, and phone numbers is encrypted at rest with Fernet and looked up via SHA-256 HMAC hashes
- Passwords are hashed with Argon2
- Organisation creation requires `is_admin` claim in the JWT
- Ongoing events cannot be edited or have ticket types mutated via the API


## Supported Versions

Only the latest production deployment is actively maintained.
