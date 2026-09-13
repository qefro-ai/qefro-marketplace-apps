# calendly-runtime

Metadata Marketplace App for Calendly.

- **App id:** `calendly-runtime`
- **Hosting:** `runtime`
- **Execution:** generic HTTP tools against a workspace connection

There is no vendor SDK, webhook server, or API client in this package.

## Connection / OAuth

Bearer OAuth (`auth.calendly.com`). Host typically `api.calendly.com`.

## CRM Automation examples

- `booking.created` → send confirmation, schedule reminder
- `booking.cancelled` → create follow-up task

## Webhooks

Signature header `Calendly-Webhook-Signature`. Calendly may use a timestamped scheme similar to Stripe — generic HMAC first, Runtime gap if the digest is not raw-body HMAC.

