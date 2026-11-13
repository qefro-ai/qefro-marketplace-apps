# Runtime audit — 2026-11-13

Source inspection precedes runtime modifications. Paths below are relative to `/Users/abu/qefro`.

## Verified gaps and security findings

1. **Full identity-number confidentiality is not available as a proven metadata contract.** `ai-customer-support/crates/api/src/app_rbac_authz.rs::require_entity_permission` checks entity operations, not per-field grants. `flow_engine/entity_runtime.rs::write_mutation_audit` stores before/after documents through `entity_integrity::sanitize_audit_doc`; it does not consult field classification metadata. A hidden form field is not a security boundary. Do not collect full Emirates IDs in this release. Keep only a four-digit suffix in a separately permissioned entity; full-number storage, authorized reveal, log redaction and AI exclusion require a coordinated security contract across storage, events, audit and agent projections.
2. **Calendar arithmetic missing.** `flow_engine/entity_compute.rs::ComputedOp` supports numeric arithmetic, relation sums/counts and status derivation, but no anniversary, duration or elapsed-instant arithmetic. Existing calculations run after mutation (`entity_runtime::recompute_after_mutation`), so extending that function alone would not establish pre-write integrity. Contract interval validation, overlap exclusion, attendance composite uniqueness and date derivation need a coordinated pre-write contract including CSV/bulk ingress. Do not claim ordinary `unique: true` on a caller-supplied key enforces employee/day uniqueness.
3. **Read-time expiry is not established by stored computed status.** `status_from_date` runs on mutations; midnight does not itself recompute every record. Date watches emit events but do not inherently change status. Reports must use dates or explicitly maintained status, not advertise stored status as live expiry.
4. **Reminder offsets are not consumed.** `entity_dates::parse_date_events` consumes field/event/status, not an offset. Date watches provide expiry-day triggers; 90/60/30/7-day reminders need derived dates or scheduler changes. Do not invent `offset_days` YAML.
5. **Rollups are bounded.** `entity_compute::MAX_RELATION_ROWS` is 500. Do not use relation-count as a lifetime attendance total. Use server aggregate queries; actual worked days must filter attendance status, not subtract employment dates.
6. **Audit persistence is best effort.** `write_mutation_audit` logs a warning on insert failure. This is not a transactional, mandatory identity-access audit.

## Enforcement traced

`RuntimeAdapter::execute_entity_tool` resolves installation and entity definitions, calls `require_entity_permission`, strips authority from parameters, validates scalar/required/enum fields, verifies relations and uses scoped storage. Portal permissions are installation-scoped. Customer channels use Person ownership and surface rules; absence of customer exposure is not field confidentiality. Bare system API context intentionally bypasses app-role checks: only trusted internal dispatch may construct it.

`qefro-plugin-platform/services/storage-service/src/repositories/postgres.rs` binds tenant, workspace, installation and solution on record queries. Those are storage predicates, not UI filters. Storage auth validates invocation context/grants. Existing tests include `tests/isolation.rs`, `grant_isolation.rs`, `relation_e2e.rs`. Database-dependent tests can skip without their test database environment; a green process alone is insufficient evidence.

Updates support optimistic version checks and state-machine transitions. `entity_runtime::UniqueWriteLock` holds scoped advisory locks through unique writes. Required scalar validation on PATCH is not equivalent to whole-record invariant validation. Related operations, audits and events are not a single all-or-nothing transaction.

## Lifecycle and execution

ZIP extraction → `zip_assemble::assemble_from_extracted` → `validator::parse_and_validate` → publisher checksum/signature/version checks → `installer::plan_install` → `service/installer::install_for_tenant` → settings/onboarding/state → UI bundle and compiled flows. `upgrade_for_tenant`, `upgrade_review` and `uninstall_for_tenant` exist; uninstall must not be represented as guaranteed erasure of every historical record. Review actual retention policy before PII onboarding.

Portal `DataSources.ts` calls the unified UI data endpoint. `metricValue.ts` requests server aggregation. `EntityCrud` handles generic lists/forms/details. FlowRunner `executor.rs`, `steps.rs`, `variables.rs`, `retry_policy.rs`, `lease.rs` and `scheduler.rs` provide step execution, input binding, leases/retries and scheduled execution. This is durable orchestration, not a database transaction across multiple entity mutations. Retries do not automatically make arbitrary business mutations idempotent.

## Release gate

This audit does not certify production readiness. Full Emirates ID handling, enforced overlapping-contract prevention, atomic employee/day attendance uniqueness, validated temporal calculations and live multi-tenant installation tests are release blockers. The native package can still be validated and exercised locally with synthetic data. No unsupported metadata should be used to conceal these blockers.

## Executed regression findings

The unchanged ACS runtime adapter test group executed 149 tests: 146 passed and 3 failed. `get_without_id_returns_failure` and `delete_without_id_returns_failure` encounter undeclared-entity rejection before the error expected by their tests. `customer_payment_event_does_not_confirm_someone_elses_order` fails its same-person positive control (no confirmation was emitted). These are existing runtime/test failures in the inspected checkout; no ACS production source was modified by this work. They prevent claiming a fully green runtime regression suite.

## Portal allocation validation mismatch

Browser checks reproduced native form submission rejecting a hidden allocated code when the field also declares `required: true`. `EntityCrud.tsx` save payload construction checks missing required values before the runtime allocator; runtime `prepare_document` exempts the allocated field. The app now follows compatible code metadata: allocation plus uniqueness, without user-input required on allocated code fields. The server still supplies the code. This is a package adaptation, not a portal runtime fix.

Site assignment history originally used a separate manual write. Existing post-save events cannot make a history insert and prior period closure atomic with the employee save. The optional storage trigger records configured relation transitions in the same transaction and scopes each read and write to the employee's tenant, workspace, installation and app. It uses existing entity rows and requires no change to API schemas or stored documents.
