# App architecture and extension decisions

App ID `security-workforce-manager`, development version `0.1.0`, native runtime hosting. Eight entities, eight staff create workflows, native entity pages, operational overview, attendance report charts, host Contacts/Automations/Roles, and two installation settings. No customer channels, backend, connector or database migration.

Employee is the operational root. Separate private details and ID-validity entities allow entity-level role assignment. Contract renewals and ID renewals create successor records linking to predecessors; site assignments and employee history retain operational history. The full ID number is deliberately absent because confidentiality is not enforceable by UI metadata alone. This is a partial delivery against the requested full feature set, not a substitute claim of compliance.

## Generic extensions required before production

| Extension | Smallest reusable design | Affected consumers / migration |
|---|---|---|
| Temporal derivation and validation | Extend the existing entity pre-write pipeline with whitelisted calendar-add, interval-days, elapsed-instant and range constraints. Explicit date-only vs timestamp types. Compute before persistence and revalidate merged PATCH. | CRUD, FlowRunner, importer, bulk, restore, internal effects; UI readonly projection; existing apps opt in. Backfill/validate rows before enabling. |
| Composite uniqueness / interval exclusion | Metadata-declared field tuples and partitioned date intervals. Enforce in shared storage transaction/locking layer, not list-before-create flows. | Storage create/update/batch/restore, import conflict previews, entity schema validator. Reject existing duplicates/overlaps during activation; all-pairs concurrency tests. |
| Sensitive field protection | Server field classification, deny-by-default reveal grants, redacted standard projection, encrypted storage as appropriate, scrubbed errors/audits/events/AI/export, mandatory reveal audit. | Storage, entity adapter, workflow logs, audit, AI tools, exports, search indexes and portal. Needs coordinated security design; simply splitting an entity does not provide field masking. |
| Live expiry metrics | Server aggregate date-window predicates with injected workspace-local clock, or generic read-time derived fields. | UI metric query parser, entity aggregate, cache semantics and date-watch status handling. Existing fields retained. |
| Offset reminders | Existing date watch specs gain bounded offsets with event+offset+date identity and reschedule/cancel semantics. | Validator, watch persistence/idempotency, scheduler, automation templates. Migrate watch key uniqueness before adding multiple events on the same date field. |

No generic runtime contract was modified in this delivery: post-mutation calculations alone would not satisfy the requested pre-write invariants. Options of app-specific backend logic or optimistic list-before-create checks were rejected because they duplicate architecture or race under concurrent writes. These coordinated changes remain necessary work, not features hidden behind invented YAML.
