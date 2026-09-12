# slack-runtime

Metadata Marketplace App for Slack.

- **App id:** `slack-runtime`
- **Hosting:** `runtime`
- **Execution:** generic HTTP tools against a workspace connection

There is no vendor SDK, webhook server, or API client in this package.

## Connection / OAuth

Bearer bot token from Slack OAuth v2. Scopes: `channels:read`, `users:read`, `chat:write`, `channels:history`.

Staff-only notifications. Surfaces are staff. Do not add channel-specific branches.

## CRM Automation examples

- `notification.created` → create CRM activity
- `channel.message` → optional staff digest

## Webhooks

`X-Slack-Signature` uses a `v0:` timestamped base string, not raw-body HMAC. Declare the header here; Runtime generic HMAC will not verify Slack's scheme until a generic signed-payload algorithm exists.

