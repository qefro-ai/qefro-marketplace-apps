# real-estate-pro

This is a metadata-only Qefro Marketplace App executed by Qefro Runtime.

- **App id:** `real-estate-pro`
- **Hosting:** `runtime`
- **Architecture:** Marketplace package → metadata → Qefro Runtime → EntityService / FlowRunner / RuntimeAdapter
- **Not included:** SDK backend, custom connector, custom REST API, provider-specific Runtime branches

## What it does

Real estate operations: properties, units, agents, Person-scoped leads, viewings,
and offers (the canonical commercial lifecycle). There is no Deal entity.

## Canonical graph

```text
Customer Hub Person → Lead (pipeline)
Customer Hub Person → Viewing → Property
Customer Hub Person → Offer → Property
```

Offer is the commercial proposal and close record (`submitted` through
`closed` / `fallen_through`). Identity is Customer Hub Person. Runtime injects
`person_id`. LLM/user `person_id` is not authority.

## Entities

`property`, `property_unit`, `agent`, `lead`, `viewing`, `offer`, `property_document`

## Tools (Runtime EntityService)

Staff: create/update/search properties, leads, agents, viewings, offers, documents.
Customer: search properties, get property, request/list/cancel/lookup own viewings, create/list own offers.

Never accept arbitrary `lead_id` / `person_id` / `customer_id` / `email` / `phone` from the LLM
as authoritative ownership.

## Workflows

- `search-properties`, `request-viewing`, `reschedule-viewing`, `cancel-viewing`
- `create-lead`, `create-offer`, `create-property`

## Business Events

`property.created` / `.updated` / `.status_changed`,
`lead.created` / `.updated`,
`viewing.created` / `.updated` / `.cancelled`,
`offer.created` / `.updated` / `.closed`

## Automation examples (generic Automation host)

| Event | Suggested actions |
| --- | --- |
| `viewing.created` | CRM activity + confirmation |
| `viewing.cancelled` | CRM activity + follow-up |
| `lead.created` | CRM activity + assign/follow-up task |
| `offer.created` | CRM activity + notify agent |
| `offer.closed` | CRM activity |

## Customer vs staff surfaces

- **Staff:** Dashboard, Properties, Leads, Viewings, Offers, Agents, Documents, Automations
- **Customer:** conversation triggers scoped by Hub Person identity

## Architecture

```text
real-estate-pro (YAML metadata)
        ↓
Qefro Marketplace Runtime
        ↓
EntityService / FlowRunner / RuntimeAdapter
```
