# Development installation and release guide

This is development package `0.1.0`, not production-ready workforce software. Use synthetic data only until every release gate is resolved.

## Local verification

From `/Users/abu/qefro`:

```sh
python3 qefro-marketplace-apps/scripts/validate_apps.py
uv run --with pytest --with pyyaml python -m pytest qefro-marketplace-apps/tests -q
bash qefro-marketplace-apps/scripts/build_app_zip.sh security-workforce-manager
cargo test --manifest-path qefro-plugin-platform/Cargo.toml -p solution-service --test security_workforce_package -- --ignored --nocapture
```

The integration test is explicitly ignored in standalone platform CI because it requires the sibling app ZIP. The command above executes it. `SECURITY_WORKFORCE_ZIP` may supply another built ZIP path. Rebuild before every validation; do not validate an old archive after YAML changes.

Portal synthetic UI check:

```sh
npm --prefix ai-customer-support-portal run dev -- --host 127.0.0.1 --port 5178
node qefro-marketplace-apps/scripts/security_workforce_smoke.mjs --base-url=http://127.0.0.1:5178 --viewport=desktop,mobile --entity=employee,employment_contract,attendance --channel=chrome
```

The adapter reuses the existing portal smoke harness, adds the app to its synthetic fixtures in a temporary script, blocks external API calls and removes the temporary script afterwards. It does not install or write to a real tenant.

## Authorized development tenant

Use the portal Marketplace ZIP installer with `qefro-marketplace-apps/dist/zips/security-workforce-manager.zip`. Source-confirmed platform routes are `POST /v1/tenant/packages/upload`, preview/session endpoints, and `POST /v1/tenant/packages/uploads/:id/commit` with `install` and settings, followed by normal installation state handling. Prefer the existing portal wizard rather than guessed CLI commands. The runtime/API and solution/storage services, databases and authenticated workspace must be available.

Set timezone (default Asia/Dubai), duration years (default 2), review capabilities and configure app roles before activation. Do not enable customer channels. Run seed records in `tests/fixtures/security-workforce/seed.yaml` through native CRUD in order, replacing symbolic @references with returned IDs. Never inject tenant IDs from fixtures or write directly to the database. Check dashboard, forms, relation navigation, audit, expiry watches and cross-tenant negative tests. Retain evidence of running versions.

Upgrade through existing installer version review; current package introduces no migrations. Disabling/deactivating is the initial rollback; it is not erasure. Review uninstall retention of records, audits, schedules and exports before deletion.

## Production catalog deployment

On 2026-11-13, version `0.1.0` was signed on `app.qefro.com` with the configured trust key and published through the production solution service. The publish API returned HTTP 201. Version listing confirmed status `published` and canonical checksum `18eef12f39926aec32bc7acb510e6d8083bd0755bd3c69df0df8ab07225b37e6`. Version detail returned HTTP 200. Catalog version ID is `d78587fb-806d-407a-b0d6-0432e431c6c5`.

[Production Marketplace listing](https://app.qefro.com/app/marketplace/security-workforce-manager)

Version 0.1.1 was later installed in the active production workspace. Full live tenant isolation checks remain pending. The catalog entry is labeled as a development release and the functional limitations above still apply.

## Site assignment history

On 2026-11-13 the production storage database enabled automatic assignment history for Security Workforce Manager. The generic `record_relation_history` function lives in `qefro-plugin-platform/deploy/storage-extensions/record-relation-history.sql`. The workforce-specific binding is `ops/site-assignment-history.sql`. Apply them in that order in a transaction when provisioning a new storage database. The binding is an operational database change that lives outside the app ZIP.

A changed site closes active history that still covers the transfer date, including an assignment with a scheduled end, and creates a new active entry. A cleared site closes the open period when the caller sends a null value. A save with the same site skips history writes. The deployment verified initial assignment, transfer, unchanged edits, retries, planned-record preservation, clearing, and installation isolation using synthetic rows rolled back before commit. The initial trigger deployment left existing history untouched.

Rollback is `DROP TRIGGER IF EXISTS workforce_site_assignment_history ON public.storage_entities;`. Existing history remains available after rollback.

The production backfill reconciled the one current assignment using the employee mutation audit. The existing planned entry matched the employee, site and audit-derived start date of 2026-11-13. It was activated in place and retained its scheduled end of 2026-11-30. The retry updated zero rows and verification found one active match and zero duplicates.


## Contract expiry HR tasks

On 2026-11-13, the signed Workforce Manager 0.1.1 package was published and the active production installation was upgraded. The contract entity's `date_tasks` rule is enabled by default, targets HR in Organization Tasks, and becomes eligible 30 calendar days before the recorded end date in the workspace timezone. Active contracts already within that window are eligible on the next run.

The production platform worker runs every minute via `qefro-date-tasks.timer`. It discovers rules from active, published workspace installations and holds the contract row lock while rechecking the date and status and committing the task. The task ID is derived from the installation, rule, record, and source date. Repeated runs preserve the original task even after completion. HR is the suggested team in the existing task model.

Worker, unit files, and PostgreSQL test are in `qefro-plugin-platform/deploy/date-tasks/`. A new deployment must install that worker and timer to execute these rules. On production, `journalctl -u qefro-date-tasks.service` reports rule, candidate, creation, and error counts. To pause delivery on this host, use `systemctl disable --now qefro-date-tasks.timer`.

The isolated database test covered stale end dates, renewed and terminated records, installation scope, paused installs, and task deduplication. The first production run found the enabled rule and zero eligible contracts.
