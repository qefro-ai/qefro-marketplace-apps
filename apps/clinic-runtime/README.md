# clinic-runtime

Native Qefro Marketplace App for clinic operations.

- **App id:** `clinic-runtime`
- **Hosting:** `runtime`
- **Execution:** `entity.*` via FlowRunner → RuntimeAdapter (managed storage)

This is not a wrapper around an external API. Contacts stay on the platform
Person model (`person_id`). CRM Automations are configured on the Automations
host page and consume Business Events — they are not executed inline from tools.

## Business Events

- `visit.created` / `.updated` / `.cancelled`
- `treatment.created`

## CRM Automation examples

- Visit created → send confirmation, schedule reminder
- Visit cancelled → follow-up task

`entity.create` emits `{entity}.created`. `entity.update` currently does not
emit `{entity}.updated` in Runtime; declare the event so Automations can bind
when that generic capability exists. Cancel flows use update of `status` rather
than delete so records remain auditable.
