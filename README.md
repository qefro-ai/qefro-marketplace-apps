# Qefro Marketplace Apps

Collection of **metadata-only** Marketplace Apps executed by Qefro Runtime.

There is no SDK process, no `/qefro` server, and no provider-specific
client in these packages. Credentials never appear in YAML.

```text
Marketplace App (this repo)
  → Qefro Plugin Platform (validate, publish, install)
  → Qefro Runtime
      FlowRunner → RuntimeAdapter
        ├── entity.* (managed storage)
        └── generic HTTP executor (workspace connection)
```

The Qefro SDK stays for **external** systems (Focus ERP, Yaaz). It is not
how you build a Marketplace App.

## Apps

| Directory | App id | Vertical | Data plane |
| --- | --- | --- | --- |
| [`apps/shopify-runtime`](./apps/shopify-runtime) | `shopify-runtime` | Commerce | Generic HTTP → Shopify Admin API |
| [`apps/stripe-runtime`](./apps/stripe-runtime) | `stripe-runtime` | Payments | Generic HTTP |
| [`apps/razorpay-runtime`](./apps/razorpay-runtime) | `razorpay-runtime` | Payments | Generic HTTP |
| [`apps/woocommerce-runtime`](./apps/woocommerce-runtime) | `woocommerce-runtime` | Commerce | Generic HTTP |
| [`apps/google-calendar-runtime`](./apps/google-calendar-runtime) | `google-calendar-runtime` | Calendar | Generic HTTP |
| [`apps/google-sheets-runtime`](./apps/google-sheets-runtime) | `google-sheets-runtime` | Spreadsheets | Generic HTTP |
| [`apps/freshdesk-runtime`](./apps/freshdesk-runtime) | `freshdesk-runtime` | Support | Generic HTTP |
| [`apps/zoho-crm-runtime`](./apps/zoho-crm-runtime) | `zoho-crm-runtime` | CRM | Generic HTTP |
| [`apps/whatsapp-business-runtime`](./apps/whatsapp-business-runtime) | `whatsapp-business-runtime` | Messaging | Generic HTTP (Cloud API; not ACS WhatsApp ingest) |
| [`apps/calendly-runtime`](./apps/calendly-runtime) | `calendly-runtime` | Scheduling | Generic HTTP |
| [`apps/slack-runtime`](./apps/slack-runtime) | `slack-runtime` | Collaboration | Generic HTTP |
| [`apps/restaurant-pro-runtime`](./apps/restaurant-pro-runtime) | `restaurant-pro-runtime` | Hospitality | `entity.*` managed storage |
| [`apps/real-estate-runtime`](./apps/real-estate-runtime) | `real-estate-runtime` | Real estate | `entity.*` managed storage |
| [`apps/appointment-runtime`](./apps/appointment-runtime) | `appointment-runtime` | Booking | `entity.*` managed storage |
| [`apps/field-service-runtime`](./apps/field-service-runtime) | `field-service-runtime` | Field service | `entity.*` managed storage |
| [`apps/education-runtime`](./apps/education-runtime) | `education-runtime` | Education | `entity.*` managed storage |
| [`apps/clinic-runtime`](./apps/clinic-runtime) | `clinic-runtime` | Clinic ops | `entity.*` managed storage |
| [`apps/logistics-runtime`](./apps/logistics-runtime) | `logistics-runtime` | Logistics | `entity.*` managed storage |
| [`apps/http-catalog-runtime`](./apps/http-catalog-runtime) | `http-catalog-runtime` | HTTP fixture | Generic HTTP (non-Shopify catalog) |

Product docs: [Marketplace Apps](https://docs.qefro.com/docs/solutions/examples/marketplace-apps)
(when published) and [Runtime vs SDK](https://docs.qefro.com/docs/solutions/runtime-vs-sdk).

## HTTP tools (Shopify 0.1.2)

Staff and customer tools share one workspace Admin API token. Isolation is
metadata + Hub identity, not a second credential.

| Metadata | Role |
| --- | --- |
| `access.surfaces: [staff]` / `[customer]` | Who may run the tool |
| `identity.require_any: [person.email]` | Required Hub fields before the HTTP call |
| `identity.collect: email_otp` | WhatsApp/widget: ask for email, OTP-verify, persist on Person |
| `{person.email}` | Server-resolved from Hub. Never an LLM parameter |
| `ownership` | Filter/deny records after the upstream response |

Customer WhatsApp path for orders:

1. “Show my recent orders”
2. If the Person has no email → ask for it
3. Mail a 6-digit code → customer replies
4. Verified email is written on Customer Hub
5. `list_my_orders` calls Shopify with that email and ownership-checks the response

Shop-wide `list_orders` / `get_order` / customer list tools stay **staff-only**.

Do not add provider-specific lookup code in Runtime. Future identity
improvements (phone / mapped external id) go through this same metadata.

## Layout

```text
apps/<app-id>/
├── manifest.yaml
├── connections/     # declarations only — no secrets
├── tools/           # HTTP tool YAML (commerce / catalog)
├── entities/        # staff UI schema and/or storage entities
├── workflows/
└── ui/
```

No `src/`, no Dockerfile.

## Validate and publish

From a package directory, with the `qefro` CLI:

```bash
qefro app validate .
qefro app package .
# platform admin:
qefro app publish .
```

Validator tests in `qefro-plugin-platform` still vendor copies under
`docs/examples/` so CI can compile packages without a git submodule.
**This repo is the collection to copy, extend, and publish from.**

Collection checks (manifest, tools, workflows, surfaces, identity, webhooks):

```bash
pip install -r tests/requirements.txt
python scripts/validate_apps.py
```

## Related repos

| Repo | Role |
| --- | --- |
| [qefro-platform](https://github.com/qefro-ai/qefro-platform) | Catalog, install, versioning |
| [ai-customer-support-backend](https://github.com/qefro-ai/ai-customer-support-backend) | Qefro Runtime (FlowRunner, HTTP executor, Hub) |
| [qefro-documentation](https://github.com/qefro-ai/qefro-documentation) | Product docs |
