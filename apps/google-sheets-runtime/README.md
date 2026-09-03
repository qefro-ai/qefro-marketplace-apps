# google-sheets-runtime

Metadata Marketplace App for Google Sheets.

- **App id:** `google-sheets-runtime`
- **Hosting:** `runtime`
- **Execution:** generic HTTP tools against a workspace connection

There is no vendor SDK, webhook server, or API client in this package.
Credentials and destination host come from workspace Connect.

## Connection / OAuth

Bearer tokens from Google OAuth. Scopes: `spreadsheets` and `spreadsheets.readonly`.

Staff-only. Google Sheets does not send Shopify-style HMAC webhooks; row events in the manifest are for CRM Automation configuration after HTTP writes. Durable `{entity}.updated` emission from HTTP POST is a Runtime gap — configure Automations on explicit Business Events when Runtime adds HTTP-write event emission.

## CRM Automation examples

- `row.appended` → create CRM activity
- `spreadsheet.updated` → notify staff

