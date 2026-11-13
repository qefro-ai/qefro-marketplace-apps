# Security and production gates

## Boundaries

Storage SQL binds tenant, workspace, installation and solution. Runtime parameters are stripped of authority overrides and use installed entity definitions. Staff entity CRUD calls installation RBAC. Relations must resolve inside scoped storage. These are inspected mechanisms, not a passed live isolation certification.

No customer channels are enabled. No agent capability projection is requested. These reduce exposure but do not establish field-level confidentiality for arbitrary direct invocation. Before real data: explicitly configure HR, operations and read-only roles using installation Roles. HR alone receives employee_private and emirates_id grants. Operations receives only operational entities and needed create/update grants. Do not grant wildcard privileges to ordinary staff. Host owners/admins retain broad permissions.

## Data minimization

Full Emirates IDs are not collected; suffix field is exactly four digits. Private profile and suffix/validity are separate entities excluded from dashboard sources. Notes must not carry sensitive identifiers. Masking after retrieval is insufficient: logs, audit snapshots, events, AI tool outputs and exports all need protected projections. Existing audit sanitization removes authority keys but retains ordinary business fields.

## Required attack tests before release

1. Two independent tenant/workspace/install contexts: list/get/update/delete/aggregate/export A against B IDs must fail or return no data.
2. Submit forged tenant/workspace/install in top-level/nested workflow inputs and source filters; server must retain authenticated context.
3. Cross-tenant employee/site/predecessor references must fail on create, update and import.
4. Operations user cannot view or mutate private/identity entities via direct API, workflow, aggregate, related expansion, agent or export.
5. Customer channels and untrusted API contexts cannot invoke staff workflows or enumerate staff entities.
6. Sensitive-field audit/log/AI exposure tests and denial-of-reveal tests once that contract exists.
7. Parallel duplicate attendance and overlapping contracts fail atomically, including import/restore paths.

`tests/isolation.rs` contains database-dependent tests that explicitly skip when `STORAGE_TEST_DATABASE_URL` is absent. Do not count those as passed security checks. No production data was accessed or created. See `03-runtime-audit.md` for findings and `09-test-results.md` for actual evidence.
