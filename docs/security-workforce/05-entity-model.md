# Entity model and date conventions

All records obtain tenant/workspace/installation context from the host. Package fields never contain those authority identifiers. Relationships are native `relation` fields, not copied employee names. Every entity uses optimistic updates and soft deletion; allocated employee/site/contract codes are unique scalar fields.

| Entity | Fields / purpose |
|---|---|
| `employee` | Allocated employee number, full name, role, joining date, employment status, current site, operational notes |
| `employee_private` | Employee FK, birth date, nationality, mobile, basic salary in integer AED fils, emergency contact, HR notes |
| `employment_contract` | Allocated contract number, employee FK, start/end dates, duration years (default 2), status, last working/cancellation dates and reason, predecessor contract |
| `emirates_id` | Employee FK, four-digit suffix, issue/expiry dates, current/renewed/cancelled status, predecessor validity record |
| `attendance` | Employee/site FKs, duty date, captured site timezone, present/absent/leave/off-duty, offset-qualified check-in/out, manually reviewed duty/overtime hours, remarks |
| `duty_site` | Allocated site number, name/client/address/supervisor/contact/timezone/status |
| `site_assignment` | Employee/site FKs, effective interval, reason/status |
| `employee_history` | Employee FK, effective date, event type and operational summary; separate from system mutation audit |

## Required temporal contract (specified, not yet implemented)

Dates are Gregorian civil `YYYY-MM-DD`, not UTC instants. Contract coverage is inclusive `[start_date, end_date]`; derive end as `clamp(start + N calendar years) - 1 calendar day`. Thus 2026-01-01 + 2 years ends 2027-12-31; 2024-02-29 + 2 years clamps anniversary to 2026-02-28 then ends 2026-02-27. This leap-day policy requires business acceptance before deployment. Never substitute 730 days for two years.

Duration is `end - start + 1`; invalid/inverted intervals must fail. Elapsed employed days include today and clamp to `[0, duration]`. Future employment has zero elapsed days. Remaining days exclude today: `max(end - max(today,start-1),0)`. Completed calendar service ends on the last working date, bounded by the contract. Cancellation date is administrative and must not replace last working date. Renewal is a separate interval; for an employee, inclusive intervals intersect when `new.start <= old.end && old.start <= new.end`. Draft/cancelled policy must be explicit before enforcing exclusions.

Actual worked days are distinct employee/duty dates with present attendance. They are not calendar service days. A single employee/day policy needs storage-enforced tuple uniqueness; it is not yet implemented. Overnight duty uses explicit RFC3339 instants, checkout after check-in, with duty date defined as the site's local check-in date. Elapsed hours are instant difference; overtime requires an approved normal-hours policy. Current fields are manually entered and must not be mistaken for verified calculations.

Full Emirates ID format/checksum validation is unimplemented: no authoritative business validation requirement was supplied, and this version never accepts a full number in its dedicated suffix field. The four-digit pattern is a storage constraint for a suffix, not proof of an authentic government identifier.
