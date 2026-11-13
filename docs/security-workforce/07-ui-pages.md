# Native UI pages

No custom frontend was added. UI definitions live in `apps/security-workforce-manager/ui/` and are validated by the production UI parser.

- Overview: server aggregate total/active/inactive employee counts, explicitly marked active/terminated contract counts, today's attendance/present-record counts and employee history table.
- Eight entity pages: generic native tables, search, filters, new/edit forms, detail pages and soft-delete actions. Related records use declared FKs.
- Contract work queues: active, ends within next seven workspace-local days, terminated.
- ID validity queue: current records expiring within seven days.
- Attendance queues: today's records and present records.
- Attendance reports: monthly record counts, entered duty hours and entered overtime grouped by employee.
- Host pages: Contacts (repository convention), Automations and Roles.

Sources are typed entity sources. Metric queries request backend aggregates, never count the first loaded page or contain static totals. No private-profile or identity source is fetched by the general dashboard. Missing expired-count, remaining-validity and guards-currently-on-duty metrics are intentional gaps: no verified runtime calculation supports those semantics. A present attendance row does not prove a guard is currently on duty.

Employee directory and site-wise browsing use the native employee table and relation/status filters. Early termination uses its contract queue. Contract/ID expiry browsing uses date queues. Worked days cannot be certified until duplicate prevention and distinct-day aggregation exist. Native host print components exist; this package adds no Excel/PDF engine and makes no guarantee of complete export until live host export tests pass.

Loading/empty/error/retry and responsive behavior belong to the existing host. See test results for the exact executed UI checks and any failures.
