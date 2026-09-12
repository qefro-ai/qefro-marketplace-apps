# zoho-crm-runtime

Metadata Marketplace App for Zoho CRM.

- **App id:** `zoho-crm-runtime`
- **Hosting:** `runtime`
- **Execution:** generic HTTP tools against a workspace connection

There is no vendor SDK, webhook server, or API client in this package.

## Connection / OAuth

Bearer OAuth. Scopes `ZohoCRM.modules.ALL` and `ZohoCRM.settings.ALL`. Host typically `www.zohoapis.com` (workspace-supplied). Staff-only.

Lead email uses parameter `lead_email`, never `email`, so callers cannot override Hub identity keys.

## CRM Automation examples

- `lead.created` → create Qefro Person follow-up task
- `deal.updated` → notify staff

