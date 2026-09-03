# freshdesk-runtime

Metadata Marketplace App for Freshdesk.

- **App id:** `freshdesk-runtime`
- **Hosting:** `runtime`
- **Execution:** generic HTTP tools against a workspace connection

There is no vendor SDK, webhook server, or API client in this package.

## Connection

Bearer credential. `oauth.host_suffix: .freshdesk.com` so Connect cannot point at an arbitrary host.

create_ticket uses `requester_email` (not `email`) so LLM/client parameters cannot override Hub identity keys.

## CRM Automation examples

- `ticket.created` → create CRM activity, notify staff
- `ticket.updated` → notify assignee

## Webhooks

Declared HMAC/topic headers. Freshdesk automations may use a different signature envelope — treat as generic HMAC first.

