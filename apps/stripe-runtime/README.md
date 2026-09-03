# stripe-runtime

Metadata Marketplace App for Stripe.

- **App id:** `stripe-runtime`
- **Hosting:** `runtime`
- **Execution:** generic HTTP tools against a workspace connection

There is no vendor SDK, webhook server, or API client in this package.
Credentials and destination host come from workspace Connect.

## Connection

Workspace Connect supplies the allowlisted host (typically `api.stripe.com`) and a Bearer secret key, or Stripe Connect OAuth using the declared authorize/token URLs. Required OAuth scope: `read_write`.

## CRM Automation examples

Configure on the Automations host page. This package emits events; it does not run automations inline.

- `payment.succeeded` → update CRM relationship, send confirmation
- `payment.failed` → create follow-up task
- `subscription.cancelled` → create customer retention task
- `refund.created` → notify staff

## Webhooks

HMAC header `Stripe-Signature`, identity header `Stripe-Account`, topic header `Stripe-Event-Type`, idempotency header `Stripe-Event-Id`. Runtime verifies the raw body. Stripe's timestamped `t=,v1=` signature format is a generic Runtime capability gap if the header is not a raw HMAC digest.

