# Executed verification — 2026-11-13

## Results

| Command / scope | Actual result | Meaning |
|---|---|---|
| `python3 qefro-marketplace-apps/scripts/validate_apps.py` | 132 passed | Entire app corpus plus 7 new package contract tests |
| `uv run --with pytest --with pyyaml python -m pytest tests/test_packages.py -q` (apps repo) | 125 passed; 1608 subtests passed (subsequent full `tests` run: 132 passed) | Existing package regression suite; initial bare python attempt failed because pytest was unavailable, then isolated uv invocation passed |
| `cargo test -p solution-service --test security_workforce_package -- --ignored --nocapture` | 2 passed | Actual ZIP extraction, assembly, schema validation, workflow compilation and install planning; not live install |
| `cargo test -p solution-service --lib solution:: --quiet` | 200 passed | Existing platform solution tests |
| `cargo test -p api --bin b2b-ai-server flow_engine::entity_validate -- --nocapture` | 19 passed | Existing runtime scalar/constraint/state validation |
| `cargo test -p api --bin b2b-ai-server flow_engine::entity_dates::tests -- --nocapture` | 7 passed | Existing timezone/date-watch/idempotency tests; not new contract-duration calculations |
| `cargo test -p api --bin b2b-ai-server app_rbac_authz -- --nocapture` | 7 passed | Existing role-context helper tests; not live two-company isolation |
| `cargo test -p api --bin b2b-ai-server flow_engine::runtime_adapter::tests -- --nocapture` | **146 passed, 3 failed** | Existing adapter regression group; details below |
| Portal Vitest `EntityCrud.test.tsx fieldModel.test.ts metricValue.test.ts insightsDates.test.ts` | 156 passed across 4 files | Generic host forms/filtering/paging/metric regressions |
| `npm run build` (portal) | Passed | TypeScript build and production Vite bundle; chunk-size warnings remain |
| `docker ps` | Failed: daemon socket unavailable | No local container services were available through Docker |

The source worktrees for ACS production runtime were not changed. The platform change is an integration test only. Existing warnings were not suppressed.

## Existing adapter failures

- `get_without_id_returns_failure`: expected a requires-ID error; actual undeclared installed entity error.
- `delete_without_id_returns_failure`: same ordering mismatch.
- `customer_payment_event_does_not_confirm_someone_elses_order`: same-person positive control expected confirmation but observed no output.

These failures were observed in the unchanged runtime checkout. Do not report existing apps as fully regression-certified.

## Browser evidence

The app-specific wrapper runs the existing portal harness with actual app YAML, synthetic workspace/employee rows and intercepted API calls. Earlier attempts exposed harness drift: workspace/role bootstrap mocks, host-owned headings, hidden default/allocated fields, and mocked allocation order. Harness mismatches were corrected only in the wrapper. The hidden allocated-field failure also exposed an actual native save-path incompatibility; package metadata was corrected as documented in the audit. Product runtime source was not edited. The wrapper retains form-label audits, required-input rejection, actual UI save/detail checks, layout overflow checks and unexpected-network/console assertions.

Final desktop run: **6 passed, 0 failed**; final mobile run: **7 passed, 0 failed** (`evidence/browser-mobile.json`), covering dashboard, employee/contract/attendance list-detail-create journeys, pointer targets and console/network assertions. Evidence: `evidence/browser-desktop.json`. The generated screenshots remain under `ai-customer-support-portal/test-results/ui-polish-smoke/2026-11-13T09-46-12-843Z/`. Browser success does not establish backend persistence, FlowRunner execution, RBAC or date-calculation correctness.

## Not executed / not implemented

Live tenant installation/activation/upgrade, actual FlowRunner entity persistence, two-company negative tests, read/write permission enforcement against running services, direct workflow forgery, event delivery and scheduler restart verification: not executed without running services and an identified development tenant.

Two-year leap/month-end calculations, cancellation service days, overnight computed hours, distinct actual worked-day aggregation, overlap rejection, attendance duplicate prevention and full-ID protection: not implemented; therefore there are no passing implementation tests for them. The date convention in `05-entity-model.md` is a proposed contract, not executed business logic.

## New file inventory

- `qefro-marketplace-apps/apps/security-workforce-manager/README.md`
- `qefro-marketplace-apps/apps/security-workforce-manager/entities/attendance.yaml`
- `qefro-marketplace-apps/apps/security-workforce-manager/entities/duty_site.yaml`
- `qefro-marketplace-apps/apps/security-workforce-manager/entities/emirates_id.yaml`
- `qefro-marketplace-apps/apps/security-workforce-manager/entities/employee.yaml`
- `qefro-marketplace-apps/apps/security-workforce-manager/entities/employee_history.yaml`
- `qefro-marketplace-apps/apps/security-workforce-manager/entities/employee_private.yaml`
- `qefro-marketplace-apps/apps/security-workforce-manager/entities/employment_contract.yaml`
- `qefro-marketplace-apps/apps/security-workforce-manager/entities/site_assignment.yaml`
- `qefro-marketplace-apps/apps/security-workforce-manager/manifest.yaml`
- `qefro-marketplace-apps/apps/security-workforce-manager/settings/business.yaml`
- `qefro-marketplace-apps/apps/security-workforce-manager/ui/layouts.yaml`
- `qefro-marketplace-apps/apps/security-workforce-manager/ui/navigation.yaml`
- `qefro-marketplace-apps/apps/security-workforce-manager/ui/pages.yaml`
- `qefro-marketplace-apps/apps/security-workforce-manager/ui/sources.yaml`
- `qefro-marketplace-apps/apps/security-workforce-manager/ui/theme.yaml`
- `qefro-marketplace-apps/apps/security-workforce-manager/ui/widgets.yaml`
- `qefro-marketplace-apps/apps/security-workforce-manager/workflows/create-attendance.yaml`
- `qefro-marketplace-apps/apps/security-workforce-manager/workflows/create-duty-site.yaml`
- `qefro-marketplace-apps/apps/security-workforce-manager/workflows/create-emirates-id.yaml`
- `qefro-marketplace-apps/apps/security-workforce-manager/workflows/create-employee-history.yaml`
- `qefro-marketplace-apps/apps/security-workforce-manager/workflows/create-employee-private.yaml`
- `qefro-marketplace-apps/apps/security-workforce-manager/workflows/create-employee.yaml`
- `qefro-marketplace-apps/apps/security-workforce-manager/workflows/create-employment-contract.yaml`
- `qefro-marketplace-apps/apps/security-workforce-manager/workflows/create-site-assignment.yaml`
- `qefro-marketplace-apps/tests/test_security_workforce.py`
- `qefro-marketplace-apps/tests/fixtures/security-workforce/seed.yaml`
- `qefro-marketplace-apps/scripts/security_workforce_smoke.mjs`
- `qefro-plugin-platform/services/solution-service/tests/security_workforce_package.rs`

## Artifact

Built ZIP: `qefro-marketplace-apps/dist/zips/security-workforce-manager.zip` (25 package files, plus ZIP directory entries). SHA-256: `30c953a1cb650de054c782279122c2180980111c737c667c1f1dafb1c1238c71`. No executable files, credentials or seed data are included.
