# restaurant-pro-runtime

This is a metadata-only Qefro Marketplace App executed by Qefro Runtime.

- **App id:** `restaurant-pro-runtime`
- **Hosting:** `runtime`
- **Architecture:** Marketplace package → metadata → Qefro Runtime → EntityService / FlowRunner / RuntimeAdapter
- **Not included:** SDK backend, custom connector, custom REST API, provider-specific Runtime branches

## What it does

Complete restaurant operations: restaurants, tables, menu categories/items, customers,
reservations, orders, order items, staff, dining sessions, and payments.

## Entities

`restaurant`, `table`, `menu_category`, `menu_item`, `customer`, `reservation`,
`order`, `order_item`, `staff_member`, `dining_session`, `payment`

Customer-owned records (`customer`, `reservation`, `order`, `dining_session`, `payment`)
bind to Customer Hub via `person_id` (`type: person`).

## Tools (Runtime EntityService)

Staff portal + EntityService: create/list/get/update menu, tables, reservations, orders, customers, staff.
Customer conversation flows: browse menu, check table availability, book table, list/cancel/lookup own reservations, create/lookup own orders.

Customer tools never expose all restaurant customers, reservations, or orders.
Identity comes from Customer Hub — never trust `customer_id` / `email` / `phone` from the LLM.

## Workflows

- `book-table`, `cancel-reservation`, `lookup-reservation`
- `create-order`, `update-order-status`
- `browse-menu`, `check-table-availability`

## Business Events

`reservation.created` / `.updated` / `.cancelled`,
`order.created` / `.updated` / `.completed` / `.cancelled`,
`payment.created`, `customer.created`, `menu_item.created` / `.updated`

Status transitions on `reservation` and `order` emit via entity `status_events`.

## Automation examples (generic Automation host)

| Event | Suggested actions |
| --- | --- |
| `reservation.created` | CRM activity + confirmation |
| `reservation.cancelled` | CRM activity + follow-up |
| `order.created` | CRM activity |
| `order.completed` | CRM activity |

## Customer vs staff surfaces

- **Staff:** Dashboard, Reservations, Tables, Menu, Orders, Customers, Staff, Automations
- **Customer:** conversation triggers scoped by Hub Person identity

## Architecture

```text
restaurant-pro-runtime (YAML metadata)
        ↓
Qefro Marketplace Runtime
        ↓
EntityService / FlowRunner / RuntimeAdapter
```
