# billing-pro

Metadata-only Qefro Marketplace App. Not an accounting ERP and not a payment gateway.

- **App id:** `billing-pro`
- **Hosting:** `runtime`
- **Architecture:** Marketplace package → metadata → Qefro Runtime → EntityService / FlowRunner / RuntimeAdapter
- **Not included:** SDK backend, custom connector, custom REST API, payment gateway, accounting engine, Billing scheduler, Billing WhatsApp sender, Goal/Agent metadata

## What it does

1. Create invoices (and catalog products / invoice line items).
2. Track payments and split them across invoices via payment allocations.
3. Track outstanding balances from generic computed rollups.
4. Follow up on unpaid / partial bills.
5. Use existing Qefro CRM Automation + WhatsApp to remind the customer.
6. Stop follow-up after the invoice is paid (`on_events` completes pending follow-ups).

Core journey:

```text
CREATE INVOICE → TRACK PAYMENT → IDENTIFY OUTSTANDING
    → FOLLOW UP → CUSTOMER PAYS → STOP FOLLOW-UP
```

1. Invoice created (`issued`). Line-item totals roll up when items exist; CSV/conversation totals are kept when there are no items yet.
2. Staff record a payment → allocation → invoice `paid_amount` / `outstanding_amount` / `partially_paid` or `paid`.
3. Unpaid past `due_date` → `invoice.overdue` (date watch + status). Event → FlowRunner `on-invoice-overdue` creates a pending follow-up.
4. Staff can also create a follow-up when the customer says they will pay later.
5. `follow_up.due` (date watch) is a fact for CRM Automation to send WhatsApp. Billing Pro does not send WhatsApp.
6. When outstanding reaches zero, `invoice.paid` completes pending follow-ups.

## Entities

| Entity | Role |
| --- | --- |
| `product` | Catalog item or service (`sku` unique) |
| `invoice` | Customer invoice bound to Customer Hub `person_id` |
| `invoice_item` | Line on an invoice (`unit_price` is a snapshot) |
| `payment` | Recorded receipt bound to Customer Hub `person_id` |
| `payment_allocation` | Amount of a payment applied to an invoice |
| `follow_up` | Follow-up against an invoice (`follow_up_date`) |

There is no Customer entity and no Collection Case. Identity is Customer Hub Person (`person_id`, `type: person`). Invoice and Payment are `scope: customer`. Follow-up is an operational record created by staff or Event → FlowRunner; the invoice relation is the customer link.

## Tools (Runtime EntityService)

Staff operations use generic `entity.<name>.{create,list,get,update,delete,restore,aggregate}` capabilities.
There is no HTTP `tools/` folder.

Command Chat uses generic capability advertisement (entity list/get/aggregate projection and flow triggers). This package does not ship chat UI or `agent:` / `goal:` metadata.

Never trust `person_id`, `customer_id`, `email`, or `phone` supplied by the LLM/client.
Runtime injects `person_id` on create for customer-scoped entities (portal staff pick Person in generic CRUD).

## Workflows

- `create-product`, `create-invoice`, `record-payment`
- `create-follow-up`, `complete-follow-up`
- `allocate-payment`, `cancel-invoice`
- `on-invoice-overdue` (`trigger.type: event`, `event: invoice.overdue`)

`record-payment` creates a Payment and a Payment Allocation. It does not ask staff for invoice totals; computed fields are authoritative.

## Computed fields

| Invoice field | Source |
| --- | --- |
| `subtotal` / `total_amount` | `relation_sum` of `invoice_item.amount` (empty children do not wipe an explicit create/CSV total) |
| `paid_amount` | `relation_sum` of `payment_allocation.amount` |
| `outstanding_amount` | `total_amount - paid_amount` |
| `status` | `status_from_number` + `status_from_date` (`paid` / `partially_paid` / `issued` / `overdue`; `draft` and `cancelled` preserved) |

Invoice-item `amount` = `quantity * unit_price - discount`.

## Business Events

- `product.created` / `.updated`
- `invoice.created` / `.issued` / `.updated` / `.partially_paid` / `.paid` / `.cancelled` / `.overdue`
- `payment.created` / `.received` / `.reversed`
- `payment_allocation.created`
- `follow_up.created` / `.completed` / `.cancelled` / `.due`

## Automation (generic host — configure on Automations)

| Event | Suggested actions |
| --- | --- |
| `invoice.created` | CRM activity |
| `invoice.overdue` | CRM activity (Event → FlowRunner also creates a follow-up) |
| `follow_up.created` / `follow_up.due` | CRM activity + WhatsApp reminder |
| `payment.received` | CRM activity + payment confirmation |
| `invoice.paid` | CRM activity (pending follow-ups are completed via `on_events`) |

Message templates can use generic entity values (customer name, invoice number, outstanding, due date). Do not hardcode Billing fields into the WhatsApp channel.

## CSV import

Use generic Entity CSV Import on Invoice. Typical headers:

| CSV header | Maps to |
| --- | --- |
| Name / Phone / Email | Customer Hub Person (not a Customer entity) |
| Invoice number | `invoice_number` (unique) |
| Invoice date | `issue_date` |
| Due date | `due_date` |
| Due Amount / Total | `total_amount` |
| Amount paid / Paid | `paid_amount` |
| Outstanding / Balance | `outstanding_amount` |

Identity is resolved to Customer Hub Person. There is no Receivable entity. Workspace isolation is the generic importer's. CSV cannot set tenant/workspace/person authority keys.

## Settings

Workspace install settings: `currency`, `invoice_prefix`, `payment_terms_days`, `default_tax_rate`, `follow_up_interval_days`. `currency` and `default_tax_rate` are create defaults via `default_from_setting`.

## Customer vs staff surfaces

- **Staff:** portal navigation (Dashboard, Products, Invoices, Payments, Follow-ups, Contacts, Automations)
- **Customer:** Hub Person identity on customer-scoped records

## Architecture

```text
billing-pro (YAML metadata)
        ↓
Qefro Marketplace Runtime
        ↓
EntityService / FlowRunner / RuntimeAdapter
        ↓
managed storage · events · Event → FlowRunner · Automations host · WhatsApp channel · UI host
```
