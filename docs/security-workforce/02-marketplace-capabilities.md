# Marketplace capability matrix

Support means an implementation was located; execution evidence is separately listed in `09-test-results.md`. None of the live installation or multi-tenant journeys has been certified.

| Capability | Existing support | Reference | Runtime location | Gap |
|---|---|---|---|---|
| Entity CRUD | Implemented | All native apps | ACS `flow_engine/runtime_adapter.rs`, platform storage `repositories/postgres.rs` | Needs running backend for app persistence verification |
| Form rendering | Generic entity forms and form widgets | Real Estate Pro | Portal `EntityCrud.tsx`, `fieldModel.ts`, `WidgetRegistry.tsx` | Field visibility is not access control |
| Tables | Search/sort/paging/filter UI and server query sanitization | Real Estate Pro | `EntityCrud.tsx`, ACS `entity_validate.rs`, `entity_collection.rs` | App UI checks use synthetic intercepted APIs |
| Dashboards | Count/sum/today aggregate metrics, charts | Restaurant/Billing/Real Estate | Portal `metricValue.ts`, `chartValue.ts`; ACS `entity_runtime.rs::ui_entity_read_op` | No native countdown metadata located |
| Relationships | Declared FK validation, native picker/detail surfaces | Restaurant/Field Service | `runtime_adapter.rs`, `entity_runtime.rs`, portal field model | Atomic transfer across current site/history absent |
| Dates | Normalization, workspace-local windows, due watches | Billing Pro, viewing queues | `entity_dates.rs`, `entity_collection.rs` | Anniversary, inclusive service days, overlap exclusion and overnight-hours rules absent |
| Schedules | Durable flow schedule infrastructure | Engine tests | `scheduler.rs`, `steps.rs` | Package cron parsing alone does not prove end-to-end scheduling registration |
| Notifications | CRM automation actions and date-event emission | Billing/Real Estate | `entity_dates.rs`, CRM automation dispatch | Offset reminders and delivery verification not provided by this package |
| Reports | Entity lists, native filters, server aggregate charts | Billing Pro | Portal entity pages, chart values, host print components | Export completeness/permissions and actual distinct worked days unverified |
| RBAC | Installation entity-operation grants | Host Roles page | `app_rbac_authz.rs`, `db/app_rbac.rs` | Full-number field permissions/redaction and sensitive audit not established |
| Uniqueness | Individual scalar `unique` with advisory locks | Restaurant/Billing | `entity_runtime.rs::UniqueWriteLock` | Employee/date composite uniqueness and contract interval exclusion missing |
| History | Mutation audit plus related records | Generic host | `entity_runtime.rs::write_mutation_audit`, audit API | Audit is best effort; no read-access audit guarantee |
| Upgrades | Version review/diff/install service | Platform tests | `service/installer.rs`, `solution/metadata_diff.rs` | New constraint rollout must address existing rows |

The package uses no WhatsApp Catalog, booking availability, line items, customer flows or external connectors. Staff-only workforce data has no reason to activate those features.
