# woocommerce-runtime

Metadata Marketplace App for WooCommerce.

- **App id:** `woocommerce-runtime`
- **Hosting:** `runtime`
- **Execution:** generic HTTP tools against a workspace connection

There is no vendor SDK, webhook server, or API client in this package.
Credentials and destination host come from workspace Connect.

## Connection

Workspace supplies the store host and REST credentials as `Authorization`. Paths are `/wp-json/wc/v3/...`.

## CRM Automation examples

- `order.created` → send confirmation, create CRM activity
- `order.cancelled` → create customer follow-up task
- `customer.created` → bind Person relationship
- `product.updated` → notify staff of inventory change

## Webhooks

`X-WC-Webhook-Signature` base64 HMAC-SHA256, source `X-WC-Webhook-Source`, topic `X-WC-Webhook-Topic`, id `X-WC-Webhook-ID`.

