# real-estate-pro-runtime

This is a metadata-only Qefro Marketplace App executed by Qefro Runtime.

- **App id:** `real-estate-pro-runtime`
- **Hosting:** `runtime`
- **Architecture:** Marketplace package → metadata → Qefro Runtime → EntityService / FlowRunner / RuntimeAdapter
- **Not included:** SDK backend, custom connector, custom REST API, provider-specific Runtime branches

## What it does

Complete real estate operations: properties, units, agents, leads, viewings, offers,
deals, and property documents.

## Entities

`property`, `property_unit`, `agent`, `lead`, `viewing`, `offer`, `deal`, `property_document`

Lead-owned records bind to Customer Hub via `person_id` (`type: person`).

## Tools (Runtime EntityService)

Staff: create/update/search properties, leads, agents, viewings, offers, deals, documents.
Customer: search properties, get property, request/list/cancel/lookup own viewings, create/list own offers.

Never accept arbitrary `lead_id` / `person_id` / `customer_id` / `email` / `phone` from the LLM
as authoritative ownership. Identity comes from Customer Hub; Runtime injects `person_id` on create.

## Workflows

- `search-properties`, `request-viewing`, `reschedule-viewing`, `cancel-viewing`
- `create-lead`, `create-offer`, `create-deal`

## Business Events

`property.created` / `.updated` / `.status_changed`,
`lead.created` / `.updated`,
`viewing.created` / `.updated` / `.cancelled`,
`offer.created` / `.updated`,
`deal.created` / `.updated` / `.closed`

## Automation examples (generic Automation host)

| Event | Suggested actions |
| --- | --- |
| `viewing.created` | CRM activity + confirmation |
| `viewing.cancelled` | CRM activity + follow-up |
| `lead.created` | CRM activity + assign/follow-up task |
| `offer.created` | CRM activity + notify agent |
| `deal.closed` | CRM activity |

## Customer vs staff surfaces

- **Staff:** Dashboard, Properties, Leads, Viewings, Offers, Deals, Agents, Documents, Automations
- **Customer:** conversation triggers scoped by Hub Person identity

## Architecture

```text
real-estate-pro-runtime (YAML metadata)
        ↓
Qefro Marketplace Runtime
        ↓
EntityService / FlowRunner / RuntimeAdapter
```
