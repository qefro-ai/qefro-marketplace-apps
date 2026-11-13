# Runtime discovery

Inspected current source on 2026-11-13. All paths relative to `/Users/abu/qefro`. This workspace is a collection of Git checkouts, not one build: root skill/docs repository, Rust application runtime, Rust platform, React portal and metadata apps.

## Confirmed architecture and source inventory

| Subsystem | Actual source and execution path |
|---|---|
| App corpus | `qefro-marketplace-apps/apps/*/manifest.yaml`; `scripts/validate_apps.py` discovers Python unittest contracts |
| Package ingest | `qefro-plugin-platform/services/solution-service/src/solution/zip_security.rs::extract_package_zip`, `zip_assemble.rs::assemble_from_extracted` |
| Manifest/entity/flow/UI schemas | Same `solution/` directory: `manifest.rs::SolutionPackageManifest`, `entities.rs::EntityDefinition`, `workflows.rs::FlowDefinition`, `ui.rs`; host DTOs in `crates/qefro-plugin-proto/src/ui.rs` |
| Cross-package validation | `solution/validator.rs::parse_and_validate` checks inventories, references, events, supported vocabularies |
| Registration/version | `services/solution-service/src/service/publisher.rs::publish_package`, checksum/signature helpers in `solution/validator.rs` |
| Installation | `solution/installer.rs::plan_install`, `service/installer.rs::{install_for_tenant,set_state,update_settings,upgrade_for_tenant,uninstall_for_tenant}` |
| Runtime projection | `services/solution-service/src/api/chat_context.rs` selects primary active workspace installation; `service/installer.rs::get_ui_bundle` supplies UI |
| Host UI | `ai-customer-support-portal/src/pages/solutions/ui/{SolutionSubdomain,LayoutEngine,WidgetRegistry,EntityCrud}.tsx`; `DataSources.ts`, `Capabilities.tsx`, `fieldModel.ts` |
| API entry | `ai-customer-support/crates/api/src/routes/solutions_plane.rs::{runtime_ui_data,runtime_ui_entity,runtime_action_execute,runtime_ui_entity_audit,runtime_ui_entity_import}` |
| Workflow engine | `ai-customer-support/crates/api/src/flow_engine/{executor,steps,variables,dispatch,lease,retry_policy,scheduler}.rs`; canonical flow domain types under `crates/domain/src/` |
| Entity operations | `flow_engine/runtime_adapter.rs::execute_entity_tool`; `entity_validate.rs`, `entity_compute.rs`, `entity_integrity.rs`, `entity_runtime.rs`, `entity_collection.rs` |
| Authorization | `crates/api/src/app_rbac_authz.rs`, `crates/db/src/app_rbac.rs`; runtime derives tenant/workspace/install context, does not trust document IDs as authority |
| Document persistence | `qefro-plugin-platform/services/storage-service/src/{auth,filter,models}.rs`, `repositories/postgres.rs` binds all isolation dimensions |
| Events and automation | `flow_engine/{bus,entity_dates,entity_runtime,scheduler}.rs`; `crates/db/src/{entity_date_watches,entity_mutation_audit}.rs`; CRM automation action types in `crates/domain/src/crm_automation.rs` |
| Verification | Apps Python tests; solution-service Cargo unit/integration tests; storage-service integration tests; ACS API Cargo tests; portal Vitest and Playwright smoke harness |

## Verified package grammar

`hosting: runtime`, `entities`, `flows`, `events`, `settings`, `permissions`, `capabilities`, `ui` are consumed. Entity fields use canonical scalar/date/datetime/enum/relation types; relations use `ref_entity`. Staff workflows use `surfaces: [staff]`, `trigger: {type: conversation}`, `ask`, `tool` with `execution: runtime`, `input_map`, `output`, then `complete`. Dynamic asks bind `choices_from` to a **string output variable**, with `title_field` and `value_field` beside it. UI files use page entity bindings or grid widget placements, sources with `type: entity`, and supported widget kinds.

There is **no explicit YAML schema-version field** on `SolutionPackageManifest`. `version` is the app SemVer, not a schema version. Do not invent `schema_version: 1`. Compatibility here means the current checked-out parser accepted the built ZIP; future parsers need rerunning.

## Existing references

Real Estate Pro is the primary reference: staff entity pages, relation pickers, runtime workflows, settings, date queues. Restaurant Pro supplies related-create, uniqueness, optimistic concurrency and computed-rollup patterns. Billing Pro demonstrates date events and status derivation. Field Service demonstrates site/staff relations. Other corpus packages include appointment, clinic, education, project tracking, logistics, travel and HTTP connectors. The corpus validation passed, but that alone is not evidence every live journey works.

## Documentation discrepancies

ADR-003 explicitly marks its SDK-required app model superseded for Marketplace Apps; its body still describes mandatory SDK processes. Current runtime packages require no separate backend. ADR-002 describes MongoDB; inspected current document repository uses PostgreSQL scoped predicates. The skill's references correctly warn that permissive entity/flow metadata can survive parsing without a consumer. In particular no field-security, reminder-offset or anniversary arithmetic keys are invented in this app.

Source revisions: ACS `3b6b3db`, platform `b4acb00`, apps `71e3a9d`, portal `a444734` (portal had pre-existing local changes). Another confirmed vocabulary mismatch: publisher state machines consume `initial`/state `name`/`terminal`; runtime validation consumes `initial_state`/state `id`/`final`. This package follows Restaurant Pro and declares both forms in raw metadata.
