# Security Workforce Manager — development release 0.1.0

Native Qefro metadata package. Uses the installed entity runtime, FlowRunner, portal EntityCrud, server aggregates, app roles, mutation history and date watches. No external backend. No customer channels are activated.

**Not approved for production employee data.** Full identity-number security, date calculations, overlap prevention and employee/day attendance uniqueness are release gates. See workspace `docs/security-workforce/` for source evidence and verification results.

## Staff journeys

Create duty site → employee → restricted private details → draft contract → review dates and overlaps → activate with generic edit. Record attendance in the site's timezone. Record transfers in assignment history and update the employee's current site separately (not atomic). Record termination dates/reason and change contract status. Renewal creates a separate contract referencing the previous contract; retain the prior record. ID renewal similarly creates a new validity record referencing its predecessor.

Search, status filters, detail/edit forms and related records use native entity pages. Dates use YYYY-MM-DD; timestamps must carry UTC offsets. Salary is integer AED fils. End dates and duty/overtime hours currently require manual entry and verification. Contract duration defaults to 2 years from installation settings; this does not calculate an end date.

## Identity and access

Only four trailing Emirates ID digits are collected. Never put a full number in notes. `employee_private` and `emirates_id` require separately assigned entity permissions. Configure installation roles before onboarding staff. Owners/admins retain host privileges. No permission declaration in this package automatically creates an HR-only role. General dashboard sources exclude both restricted entities. Agent exposure and live access controls must pass the release security tests before real data is used.

## Events and reminders

Contract end and identity expiry dates use existing `date_events`, with status guards. Four optional notify_team presets are provided, with messages containing no identifiers. Administrators may create existing Qefro automations for `contract.expiry_due`, `identity.expiry_due`, `contract.renewed`, and termination events. No notifications are sent merely by installing this package. Offset reminders and daily summaries are not implemented. Date watches are idempotent in the runtime; downstream channel delivery still needs verification.

## Reporting limitations

Counts are server aggregates of stored records. Present-record counts are not certified distinct worked days until employee/day uniqueness is enforced. “Active” metrics mean explicitly stored status, not automatically computed expiry. Use the 7-day expiry queues for current date windows. No fabricated expired/remaining-validity KPI is displayed. Native list CSV export/print availability depends on the host; Excel/PDF generation is not added here.

Build: from `qefro-marketplace-apps`, run `python3 scripts/validate_apps.py`, `uv run --with pytest --with pyyaml python -m pytest tests -q`, then `bash scripts/build_app_zip.sh security-workforce-manager`. Actual Rust package validation is covered by `solution-service/tests/security_workforce_package.rs` in the sibling platform repository. Synthetic seed fixtures are in `qefro-marketplace-apps/tests/fixtures/security-workforce/`, outside the installable package.
