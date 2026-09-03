# razorpay-runtime

Metadata Marketplace App for Razorpay.

- **App id:** `razorpay-runtime`
- **Hosting:** `runtime`
- **Execution:** generic HTTP tools against a workspace connection

There is no vendor SDK, webhook server, or API client in this package.
Credentials and destination host come from workspace Connect.

## Connection

Named header `Authorization` (workspace stores Basic credentials). Host is typically `api.razorpay.com`.

## CRM Automation examples

- `payment.succeeded` → update CRM relationship, send confirmation
- `payment.failed` → create follow-up task
- `order.paid` → notify staff

## Webhooks

`X-Razorpay-Signature` HMAC-SHA256 hex of the raw body. Identity `X-Razorpay-Account`, topic `X-Razorpay-Event`, idempotency `X-Razorpay-Event-Id`. If Razorpay omits those identity/topic headers, Runtime needs a generic JSON-body topic mapping capability.

