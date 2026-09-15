# payments-collection-pro

This is a metadata-only Qefro Marketplace App executed by Qefro Runtime.

- **App id:** `payments-collection-pro`
- **Hosting:** `runtime`
- **Architecture:** Marketplace package → metadata → Qefro Runtime → EntityService / FlowRunner / RuntimeAdapter
- **Not included:** SDK backend, custom connector, custom REST API, payment gateway, provider-specific Runtime branches

## What it does

Outstanding customer payments: invoices, recorded receipts, collection cases, and
follow-ups — all as declarative entities interpreted by the generic Runtime.
This is not a payment gateway and not an accounting ERP.

## Entities

| Entity | Role |
| --- | --- |
| `invoice` | Customer invoice bound to Customer Hub `person_id` |
| `payment` | Recorded receipt against an invoice |
| `collection_case` | Collection work against an outstanding invoice |
| `follow_up` | Follow-up logged on a collection case |

There is no second customer entity. Identity is Customer Hub Person
(`person_id`, `type: person`). Display field `customer_name` is a label only.

## Tools (Runtime EntityService)

Staff operations use generic `entity.<name>.{create,list,get,update}` capabilities.
There is no HTTP `tools/` folder — this is not an external-system integration.

Command Chat uses generic capability advertisement (entity list/get projection and
flow triggers). This package does not ship chat UI or keyword parsing.

Never trust `person_id`, `customer_id`, `email`, or `phone` supplied by the LLM/client.
Runtime injects `person_id` on create for customer-scoped entities.

## Workflows

- `create-invoice`, `record-payment`
- `create-collection-case`, `mark-promise-to-pay`, `log-follow-up`

Staff mark invoice `overdue` / case `recovered` on the generic entity pages when
those facts happen. Cancel uses status update, not delete.

## Business Events

Declared on the manifest and via entity `status_events`:

- `invoice.created` / `.updated` / `.overdue`
- `payment.created` / `.received` / `.failed`
- `collection_case.created` / `.updated` / `.escalated` / `.recovered` / `.closed`
- `follow_up.created` / `.completed`
- `promise_to_pay.created`

## Automation examples (generic Automation host)

Configure on the Automations host page — do not embed an automation engine in the package:

| Event | Suggested actions |
| --- | --- |
| `invoice.overdue` | CRM activity + open collection follow-up |
| `promise_to_pay.created` | CRM activity + reminder task |
| `payment.received` | CRM activity + payment confirmation |
| `collection_case.recovered` | CRM activity + close follow-ups |
| `follow_up.completed` | CRM activity |

## Settings

Workspace install settings (Settings UI): `currency`, `payment_terms_days`,
`grace_period_days`, `default_collection_priority`, `follow_up_interval_days`,
`escalation_after_days`.

## Customer vs staff surfaces

- **Staff:** portal navigation (Invoices, Payments, Collections, Follow-ups, Contacts, Automations)
- **Customer:** Hub Person identity on customer-scoped records; no customer booking chat in this package

## Architecture

```text
payments-collection-pro (YAML metadata)
        ↓
Qefro Marketplace Runtime
        ↓
EntityService / FlowRunner / RuntimeAdapter
        ↓
managed storage · events · Automations host · UI host
```
