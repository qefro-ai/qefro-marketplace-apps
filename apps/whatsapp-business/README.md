# whatsapp-business-runtime

Metadata Marketplace App for WhatsApp Business Cloud API.

- **App id:** `whatsapp-business-runtime`
- **Hosting:** `runtime`
- **Execution:** generic HTTP tools against a workspace connection

There is no vendor SDK, webhook server, or API client in this package.

## Connection

Bearer system-user token. Host typically `graph.facebook.com`. `phone_number_id` / `waba_id` are staff parameters, not secrets and not Hub `phone`.

This app does **not** replace Qefro's WhatsApp channel. Surface restrictions stay `staff` / `customer` in metadata.

## CRM Automation examples

- `message.inbound` → create CRM activity, notify staff
- `message.status` → update conversation state

## Webhooks

`X-Hub-Signature-256` hex HMAC (`sha256=` prefix is already stripped by generic hex verify). Topic/identity headers may need JSON-body mapping if Meta does not send them.

