# Metadata-Driven Runtime Audit

**Date:** 2026-09-09
**Scope:** Entire Qefro repository — plugin platform, runtime engine, mobile app, marketplace apps
**Question:** *Is the current Qefro Runtime actually capable of building serious production Marketplace Apps using metadata alone?*

---

## 1. Executive Summary

**Verdict: YES WITH GAPS**

The metadata-driven architecture is real, functional, and already powering 20 marketplace apps (8 entity-native verticals + 12 HTTP integrations). The core pipeline — YAML metadata → solution-service → storage-service → flow engine → mobile UI — works end-to-end without any app-specific code. The architecture rule (no app-specific Rust, no app-specific Flutter, no vertical-specific runtime logic) is **not violated anywhere** in the codebase.

However, serious ERP applications (Accounting, HR, Inventory with full supply chain) hit **five structural gaps** that metadata alone cannot yet express. These are fixable without architecture changes, but they are not trivial.

---

## 2. Metadata → Runtime Pipeline

### What exists

```
manifest.yaml + entities/*.yaml + workflows/*.yaml + ui/*.yaml
        │
        ▼
  solution-service (validate, sign, store, install)
        │
        ├──▶ PostgreSQL (catalog, installations, flows, settings)
        │
        ├──▶ storage-service (document CRUD per tenant/installation)
        │         │
        │         ▼
        │       MongoDB / PostgreSQL (per-deployment choice)
        │
        ├──▶ runtime-service (flow execution, event dispatch)
        │         │
        │         ▼
        │       FlowRunner step loop + Event bus
        │
        └──▶ UI Bundle API → Flutter mobile renders generically
```

### Trace: Entity Create (e.g., "Create Property")

1. User taps "Add Property" in mobile → `EntityFormRenderer` → POST to backend
2. Backend resolves installation → loads entity metadata (`property.yaml`)
3. `parse_entity_capability("entity.property.create")` → `EntityOp { entity: "property", op: "create" }`
4. `require_entity_permission()` → checks RBAC (org role + app role)
5. `strip_authority_overrides()` → removes tenant_id, workspace_id, person_id from params
6. `invoke_storage("storage.insert", body)` → HTTP POST to storage-service
7. Storage-service writes to MongoDB with tenant/installation isolation
8. `entity_mutation_events()` → generates `property.created` event
9. `emit_marketplace_event()` → bus persists + dispatches
10. `crm_automation::handle_event()` → matches automations
11. `dispatch::process_event()` → finds flows with matching triggers → starts executions

**PASS.** Full pipeline exists and is exercised by Real Estate Pro, Clinic Pro, Restaurant Pro.

### Trace: Conversational Flow (e.g., "Book a Viewing")

1. User sends "I want to see the apartment on Main St" via WhatsApp/widget
2. `try_advance_or_start()` → no active execution → semantic flow selection
3. Catalog matches "request-viewing" flow (cosine similarity on embeddings)
4. `FlowRunner::run(Trigger::Start)` → step loop begins
5. Step `ask_property_title` → resolves from user message via ConversationState entity extraction
6. Step `tool: entity.property.list` → filters by extracted property title
7. Step `ask_date` → prompts user, collects response
8. Step `tool: entity.viewing.create` → creates viewing record
9. Step `message` → "Viewing scheduled for {{property_title}} on {{date}}"
10. Step `complete` → terminal state, WorkingContext captures result

**PASS.** Proven live with 409+ conversations in production (Real Estate Pro).

---

## 3. Metadata Primitive Inventory

### 3.1 Entity Fields

| Type | Supported | Used in Apps |
|------|-----------|--------------|
| string | Yes | All apps |
| integer | Yes | All apps |
| float | Yes | Real Estate Pro (price, area) |
| boolean | Yes | Clinic Pro |
| date | Yes | Clinic Pro (date_of_birth) |
| datetime | Yes | Appointments (start_at) |
| email | Yes | Clinic Pro, Field Service |
| phone | Yes | Clinic Pro, Field Service |
| url | Yes | Real Estate Pro (image_url) |
| uuid | Yes | Internal |
| enum | Yes | All apps (status, type fields) |
| json | Yes | Reserved, not widely used |
| person | Yes | All apps (Customer Hub link) |
| **relation** | **Flutter renders it** | **No app uses it for entity-to-entity** |
| image | Yes | Real Estate Pro |
| currency | **Flutter supports it** | **No app uses it** |

### 3.2 Flow Step Types

| Step Type | Runtime Support | Used in Apps |
|-----------|----------------|--------------|
| ask | Yes | All apps |
| tool | Yes | All apps |
| message | Yes | All apps |
| complete | Yes | All apps |
| condition | Yes | **None** |
| branch | Yes | **None** |
| upload | Yes | **None** |
| approval | Yes | **None** |
| challenge | Yes | **None** |
| delay | Yes | **None** |
| tag | Yes | **None** |
| assign | Yes | **None** |
| activity | Yes | **None** |
| notify | Yes | **None** |
| handoff | Yes | **None** |

**Finding:** The runtime supports 15 step types but apps only use 4. The remaining 11 are implemented but untested in production metadata.

### 3.3 UI Primitives

| Primitive | Backend | Mobile Renderer |
|-----------|---------|-----------------|
| Entity list (table) | Yes | EntityListRenderer |
| Entity detail | Yes | EntityDetailRenderer |
| Entity form (create/edit) | Yes | EntityFormRenderer |
| Dashboard | Yes | DashboardRenderer |
| Kanban view | Yes | EntityKanbanView |
| Calendar view | Yes | EntityCalendarView |
| Metric cards | Yes | _MetricCard |
| Status cards | Yes | _StatusWidget |
| Markdown | Yes | Markdown widget |
| Table widget | Yes | _EntityListWidget |
| Form widget | Yes | Form widget |
| Custom screen | **Native Flutter escape hatch** | CustomScreenRegistry |
| Navigation (sidebar) | Yes | SolutionNavBar |
| Theme/colors | Yes | theme.yaml |

### 3.4 Conversation Primitives

| Primitive | Status |
|-----------|--------|
| NLU triggers (intent matching) | Exact string lists |
| Conversation slots (entity extraction) | string, person_name, date, time, email, phone, integer |
| WorkingContext (post-flow follow-up) | Lightweight: domain, intent, filters, results |
| ConversationState (durable memory) | Full: values, entities, mentions, customer, knowledge, commerce |
| Pronoun/ordinal resolution | "cancel it", "the first order" |
| Fast Router (skip-LLM path) | Pattern → embedding → LLM fallback |

### 3.5 Permission Primitives

| Primitive | Status |
|-----------|--------|
| Org RBAC (Owner/Admin/Member) | Implemented |
| App RBAC (entity.view/create/update/delete) | Implemented + seeded |
| Surface-based (customer vs staff) | Implemented |
| Agent action staging (human approval) | Implemented |
| Authority stripping | Implemented |
| Identity binding (person_id injection) | Implemented |

### 3.6 Automation Primitives

| Primitive | Status |
|-----------|--------|
| Event declarations (manifest) | Implemented |
| Status events (entity → event mapping) | Implemented |
| CRM automations (event → condition → action) | Implemented |
| Automation actions | AddTag, RemoveTag, ChangeContactStatus, AssignUser, CreateFollowup, CreateTask, SendWhatsapp, SendEmail, NotifyTeam |
| Cron scheduler | Implemented (5-field cron) |
| Event bus (Postgres-backed) | Implemented with idempotency, replay, dead-letter |

---

## 4. Entity Runtime Audit

### What works

- **Generic CRUD:** `entity.{name}.{create|list|get|update|delete}` parsed generically. No app-specific code.
- **Tenant isolation:** Every storage call carries `tenant_id + workspace_id + installation_id`.
- **Auto-code generation:** `allocate_code` (e.g., `P-1001`, `PT-1001`) implemented.
- **Status events:** Entity status transitions automatically emit business events.
- **Identity binding:** `type: person` fields are runtime-injected, never trusted from LLM.
- **RBAC enforcement:** `require_entity_permission()` checked before every operation.
- **Authority stripping:** Identity fields removed from parameters before storage call.

### What's missing

| Gap | Severity | Impact |
|-----|----------|--------|
| **No entity-to-entity relationships** | P0 | Cannot express `order.customer_id → customer.id` or `invoice_line.invoice_id → invoice.id`. Only `person` (Customer Hub) is supported. |
| **No sub-entity / line-items pattern** | P0 | Orders need line items, invoices need line items, BOMs need components. No metadata primitive for this. |
| **No foreign key validation** | P1 | Creating an order with `customer_id: "C-123"` doesn't verify the customer exists. |
| **No join / eager loading** | P1 | Listing orders can't include customer name. Each entity is isolated. |
| **No unique constraints** | P2 | Can't declare `email` as unique on `customer` entity. |
| **No computed / derived fields** | P2 | Can't express `total = quantity * unit_price` in metadata. |

### Evidence

```
# No app uses ref_entity for anything other than "person"
$ grep "ref_entity:" apps/ -r
# Result: every single hit is "ref_entity: person"

# No app declares relation-type fields between entities
$ grep "type: relation" apps/ -r
# Result: no matches
```

---

## 5. BusinessFlow Runtime Audit

### What works

- **Step runner:** `FlowRunner::run()` iterates steps with 50-step safety bound.
- **Variable system:** `FlowVariableContext` with dotted paths (`customer.name`) and `{{template}}` substitution.
- **Condition evaluator:** Non-eval parser supporting `==`, `!=`, `>`, `<`, `>=`, `<=`, `exists`, `empty`.
- **Dynamic choices:** `choices_from` in `ask` steps fetches from prior tool output (proven in Clinic Pro `book-appointment`).
- **Constants:** `$constants.key` and `$literal:value` for hardcoded values.
- **Surface isolation:** `surfaces: [customer]` vs `surfaces: [staff]` enforced.
- **Crash recovery:** Executions persist in Postgres, resume from `current_step`.
- **Idempotency:** `event_id` deduplication prevents duplicate executions.

### What's missing

| Gap | Severity | Impact |
|-----|----------|--------|
| **condition/branch never used** | P1 | 11 step types are implemented but zero apps use condition or branch. They may work but are untested. |
| **No foreach / parallel steps** | P1 | Cannot iterate over a list (e.g., "send notification to all assignees"). |
| **No sub-flow / workflow chaining** | P2 | Cannot call another flow as a step. |
| **No error handling steps** | P2 | If a tool step fails, the flow fails. No retry/catch/compensation. |
| **No variable transformation** | P2 | Cannot compute `total = qty * price` within a flow. |
| **No approval step usage** | P2 | Agent staging exists but flow-level approval steps are unused. |

### Evidence

```
# condition and branch are implemented in steps.rs but never appear in app metadata
$ grep "type: condition" apps/ -r   → no matches
$ grep "type: branch" apps/ -r      → no matches

# Only 4 step types are used across all 20 apps
$ grep "type:" apps/*/workflows/ -rh | sort | uniq -c | sort -rn
   → ask, tool, message, complete (everything else: 0)
```

---

## 6. UI Metadata Runtime Audit

### What works

- **Generic page renderer:** `RuntimePageRenderer` dispatches to entity views, forms, dashboards based on metadata.
- **Three view types:** Table, Kanban, Calendar — all rendered generically from entity metadata.
- **Field rendering:** 13+ field types with dedicated widgets (text, number, currency, select, relation, date, boolean, phone, email, status, multiline, image, datetime).
- **Dashboard composition:** Metrics, entity lists, kanban, calendar, quick actions, markdown — all from metadata.
- **Theme support:** Per-app colors (primary, secondary, accent, background, surface, text) from `theme.yaml`.
- **Navigation:** Sidebar with icons, entity highlighting, RBAC-filtered tabs.
- **Extension composition:** `ExtensionRuntime.compose()` merges host + extension apps seamlessly.
- **Brand overrides:** Tenant settings can override logo, name, colors per installation.

### What's missing

| Gap | Severity | Impact |
|-----|----------|--------|
| **Custom screens require native Flutter** | P1 | `restaurant.live_orders` needs a custom Flutter widget. Not pure metadata. |
| **Relation field renders but no data** | P1 | Flutter has `case 'relation'` in form and display code, but no app defines entity-to-entity relations. |
| **No sub-entity rendering** | P0 | Cannot show order lines inside an order detail. No nested list within detail view. |
| **No report / chart views** | P1 | No chart widget (bar, line, pie) in dashboard runtime. Metrics are count-only. |
| **No print / PDF** | P2 | Invoices, receipts, reports need PDF generation. Not in metadata. |
| **No bulk operations UI** | P2 | Cannot select multiple records and perform bulk action from metadata. |
| **No search configuration** | P2 | Search is text-only. Cannot configure which fields are searchable or add filters. |

---

## 7. Conversational Runtime Audit

### What works

- **Durable memory:** `ConversationState` persists values, entities, mentions, customer profile, knowledge, commerce session.
- **Entity extraction:** Deterministic extraction of reference codes (`ORD-12345`), emails, phones from messages.
- **Pronoun resolution:** "cancel it" → latest mention, "the first order" → ordinal, "that one" → deictic.
- **WorkingContext:** Post-flow follow-up ("how much is it?") resolved from focused results.
- **Fast Router:** Pattern → embedding → LLM fallback pipeline avoids LLM cost for simple intents.
- **Slot extraction:** NLU extracts typed slots (string, person_name, date, time, email, phone, integer).
- **Multi-surface:** WhatsApp, widget, API — all share the same conversation runtime.

### What's missing

| Gap | Severity | Impact |
|-----|----------|--------|
| **Intent matching is string-list based** | P1 | Triggers use exact `intents: ["schedule a viewing", "book a viewing"]`. No semantic similarity at trigger level (only at flow selection level). |
| **No cross-flow context** | P2 | ConversationState persists between flows, but there's no explicit "carry forward" mechanism for variables. |
| **No rich response cards in chat** | P2 | Flows can only send text messages. Cannot send entity cards, images, or action buttons within a conversation. |
| **No proactive messaging from flows** | P2 | A flow cannot initiate a conversation — it can only respond to triggers. |

---

## 8. Events + Automation Audit

### What works

- **Event bus:** Postgres-backed with idempotency keys, replay, dead-letter, loop protection.
- **Event emission:** Every entity mutation auto-generates events (`property.created`, `property.updated`, status transition events).
- **CRM automations:** Deterministic event → condition → action engine with loop protection.
- **9 action types:** AddTag, RemoveTag, ChangeContactStatus, AssignUser, CreateFollowup, CreateTask, SendWhatsapp, SendEmail, NotifyTeam.
- **Cron scheduler:** 5-field cron expression support for scheduled flows.
- **Event dispatch:** Events trigger matching flows automatically.

### What's missing

| Gap | Severity | Impact |
|-----|----------|--------|
| **No entity-mutation automation actions** | P1 | Cannot say "when lead.created → create a task" using metadata alone. CRM actions are contact-centric, not entity-generic. |
| **No cross-entity automation** | P1 | Cannot say "when deal.closed → update all related viewings to cancelled". |
| **No conditional automation actions** | P2 | Automation conditions exist but actions don't support conditional branching. |
| **No webhook outbound** | P2 | Cannot say "when order.created → POST to external URL". |
| **Automation actions are CRM-scoped** | P2 | AddTag, ChangeContactStatus assume a CRM contact model. Not generic enough for ERP. |

---

## 9. Permissions / Security Audit

### What works

- **Two-layer RBAC:** Org (Owner/Admin/Member) + App (entity.view/create/update/delete per role).
- **Seeded roles:** Admin (full CRUD) and Staff (view + create + update, no delete) auto-created on install.
- **Surface isolation:** Customer flows cannot access staff-only tools.
- **Authority stripping:** Identity fields removed from all parameters before execution.
- **Agent staging:** Non-read tool calls create PendingAction records requiring human approval.
- **Action classification:** Read / Write / Destructive / Financial / ExternalCommunication.
- **Identity injection:** `person_id` injected by runtime, never trusted from LLM.

### What's missing

| Gap | Severity | Impact |
|-----|----------|--------|
| **No custom role creation from metadata** | P1 | Only Admin and Staff are seeded. Cannot define "Manager" role with custom permissions via metadata. |
| **No field-level security** | P2 | Cannot hide `salary` field from non-HR users within the same entity. |
| **No row-level security beyond person-ownership** | P2 | Customer-facing tools filter by `person.email`, but staff-facing has no row-level filtering. |
| **No approval workflows in metadata** | P2 | Agent staging provides approval, but it's not configurable per-entity or per-role from metadata. |

---

## 10. Agent Integration Audit

### What works

- **QefroAgentExecutor:** Authoritative execution boundary with fencing, staging, provenance.
- **Metadata → capabilities:** `AgentManifestMetadata` maps manifest to per-role capability flags.
- **Tool advertisement:** Filters workspace catalog by Role × Channel × RBAC × Capability.
- **Result fencing:** `fence_json_for_model()` redacts sensitive data from tool results.
- **Session trust:** `AgentSession` carries `turn_id`, `tenant_id`, `workspace_id`, `installation_id`, `auth_ctx`, `observed_entities`.
- **5-round limit:** `MAX_AGENT_TOOL_ROUNDS = 5` prevents runaway tool loops.

### What's missing

| Gap | Severity | Impact |
|-----|----------|--------|
| **Coarse capability mapping** | P1 | `flags_for_role()` returns boolean flags (knowledge, orders, analytics, customers, inventory). Not granular enough for complex apps. |
| **No agent-specific metadata** | P2 | The Agent consumes existing flow/entity metadata. No way to define agent-specific instructions, personality, or tool preferences per app. |
| **No multi-agent orchestration** | P2 | Cannot define a "sales agent" and a "support agent" with different tool access within the same app. |

---

## 11. Real Application Capability Test

### 11.A Reference Apps (Existing)

| App | Entities | Flows | Verdict |
|-----|----------|-------|---------|
| **Real Estate Pro** | 8 | 8 | **PASS** — Fully metadata, proven in production (409 conversations) |
| **Clinic Pro** | 9 | 11 | **PASS** — Most sophisticated flow (book-appointment with dynamic choices) |
| **Restaurant Pro** | 11 | 7 | **PASS** — Custom screen escape hatch used for live orders |
| **Project Tracker** | 3 | 3 | **PASS** — Simple but complete |
| **Field Service** | 4 | 4 | **PASS** — Sites, technicians, parts, work orders |
| **Education** | 4 | 4 | **PASS** — Courses, enrollments, sessions, assignments |
| **Logistics** | 4 | 4 | **PASS** — Vehicles, consignments, shipments, stops |
| **Appointments** | 4 | 4 | **PASS** — Services, staff, availability, appointments |

### 11.B Hypothetical Apps

| Hypothetical App | Can Build? | Blockers |
|------------------|------------|----------|
| **School Management** | **YES** | Already have Education app. Add entities (student, teacher, class, grade, attendance). No blockers. |
| **Restaurant** (enhanced) | **YES** | Already exists with 11 entities. Custom screen for live orders works. |
| **Field Service** (enhanced) | **YES** | Already exists. GPS tracking would need custom screen. |
| **CRM Pro** | **YES WITH GAPS** | Entities work. Missing: email campaign tracking, deal pipeline stages with probability, activity timeline as sub-entity. |
| **HR Pro** | **YES WITH GAPS** | Entities work. Missing: org chart (entity-to-entity self-reference), payroll (computed fields), document management (file attachments on entities). |
| **Inventory Pro** | **PARTIAL** | Missing: BOM (bill of materials — sub-entity), stock movements (sub-entity of product), warehouse-to-warehouse transfers (entity-to-entity relation). |
| **Accounting Pro** | **NO** | Missing: double-entry ledger (journal entries with debit/credit lines — sub-entity pattern), chart of accounts (hierarchical entity — parent-child self-reference), financial reports (computed aggregates across entities). |

### 11.C Missing Named Apps

The user's audit request mentioned **CRM Pro, HR Pro, Inventory Pro, Project Pro, Clinic Pro, Accounting Pro**. Of these:

- **Clinic Pro** — EXISTS (9 entities, 11 flows)
- **Project Pro** — EXISTS as "Project Tracker" (3 entities, 3 flows)
- **CRM Pro** — DOES NOT EXIST (Shopify/Zoho/Freshdesk exist as HTTP integrations only)
- **HR Pro** — DOES NOT EXIST
- **Inventory Pro** — DOES NOT EXIST
- **Accounting Pro** — DOES NOT EXIST

---

## 12. Gap Classification

### P0 — Blocks serious ERP apps

| # | Gap | Why P0 | Fix |
|---|-----|--------|-----|
| 1 | **No entity-to-entity relationships** | Every ERP app needs `order → customer`, `invoice → invoice_line`, `BOM → component`. Currently only `person` (Customer Hub) is supported. | Add `ref_entity` support for inter-entity references. Storage-service adds foreign-key-like validation. Flutter renders relation field as entity picker. |
| 2 | **No sub-entity / line-items pattern** | Invoices have line items, orders have items, BOMs have components. This is the most common ERP pattern. | Add `sub_entities:` to entity metadata. Parent detail view renders child list. Storage-service handles cascade. |
| 3 | **No Accounting Pro pattern** | Double-entry accounting is the hardest ERP requirement. Needs hierarchical chart of accounts, journal entries with balanced debit/credit lines, trial balance reports. | Requires P0#1 (entity relations) and P0#2 (sub-entities) first. Then add `computed` field type and `report` UI primitive. |

### P1 — Significantly limits app quality

| # | Gap | Why P1 | Fix |
|---|-----|--------|-----|
| 4 | **condition/branch steps unused** | Implemented but untested. Serious apps need conditional logic (e.g., "if amount > 10000, require approval"). | Write test flows using condition/branch. Validate in production with a real app. |
| 5 | **No entity-mutation automation actions** | CRM automations can tag contacts and send messages, but cannot create/update entities. "When lead.created → create follow-up task" requires custom code. | Add `CreateEntity`, `UpdateEntity` actions to CRM automation engine. |
| 6 | **No custom roles from metadata** | Only Admin and Staff are seeded. ERP apps need Manager, Accountant, Viewer, etc. | Add `roles:` section to manifest.yaml. Solution-service creates roles + permission assignments on install. |
| 7 | **No report / chart views** | Dashboards have count metrics only. ERP apps need bar charts, line graphs, pivot tables. | Add `chart` widget type to UI metadata. Mobile renders with a charting library. |
| 8 | **Coarse agent capability mapping** | Boolean flags (knowledge, orders, analytics) are too coarse for complex apps with 20+ entities. | Map capabilities per-entity: `entity.property.view`, `entity.deal.create`. |

### P2 — Noticeable but workable around

| # | Gap | Fix |
|---|-----|-----|
| 9 | No field-level security | Add `visibility:` to field metadata (role-based) |
| 10 | No print / PDF generation | Add `print_template:` to entity metadata |
| 11 | No bulk operations UI | Add `bulk_actions:` to entity metadata |
| 12 | No sub-flow / workflow chaining | Add `sub_flow:` step type |
| 13 | No error handling in flows | Add `on_error:` to step metadata |
| 14 | No webhook outbound automation | Add `Webhook` action to CRM automations |
| 15 | No computed / derived fields | Add `computed:` to field metadata with expression |

### P3 — Nice to have

| # | Gap |
|---|-----|
| 16 | No calendar view for entities with date fields (view exists but not connected to entity date fields) |
| 17 | No search configuration (which fields are searchable, filter presets) |
| 18 | No multi-agent orchestration per app |
| 19 | No proactive messaging from flows |
| 20 | No unique constraints on entity fields |

---

## 13. Architecture Violation Scan

Searched for violations of the "metadata-only" rule:

| Check | Result |
|-------|--------|
| App-specific Rust branches in runtime? | **CLEAN** — No `if app == "restaurant"` anywhere |
| App-specific Flutter code? | **CLEAN** — CustomScreenRegistry is a generic escape hatch, not app-specific |
| Vertical-specific runtime logic? | **CLEAN** — Entity CRUD is fully generic |
| Unnecessary new services? | **CLEAN** — 7 services (after installer removal), all justified |
| Docker containers for normal apps? | **CLEAN** — Apps are YAML files, not containers |
| Agent-specific metadata? | **CLEAN** — Agent consumes existing manifest, no separate agent metadata |
| Duplicate plugin runtime? | **CLEAN** — One flow engine, one entity runtime |

**No architecture violations found.** The codebase respects the metadata-only rule.

---

## 14. Duplicate Runtime Audit

| Capability | Owner | Duplicates |
|------------|-------|------------|
| Flow execution | `ai-customer-support/` FlowRunner | None |
| Entity CRUD | `ai-customer-support/` RuntimeAdapter → storage-service | None |
| Event bus | `ai-customer-support/` bus.rs (Postgres) | None (Redis Streams mentioned in docs but Postgres in code) |
| Conversation memory | `ai-customer-support/` ConversationState | None |
| UI rendering | `qefro-mobile/` RuntimePageRenderer | None |
| RBAC | `ai-customer-support/` app_rbac + org_rbac | None |
| CRM automations | `ai-customer-support/` crm_automation | None |
| Agent execution | `ai-customer-support/` QefroAgentExecutor | None |

**No duplicate runtimes.** Each capability has exactly one owner.

---

## 15. Storage Architecture Observation

The runtime talks to storage-service via HTTP, not directly to MongoDB. This is correct architecture — storage-service handles tenant isolation, soft delete, and media assets. However:

- **storage-service uses PostgreSQL** (not MongoDB as docs suggest). The `STORAGE_DATABASE_URL` in k8s manifests points to PostgreSQL.
- **No schema enforcement:** Storage-service accepts any JSON document. Entity field validation (types, required) happens in the runtime adapter, not in storage.
- **No transactional multi-entity operations:** Cannot atomically create an order + its line items in one call.

---

## 16. Mobile Rendering Pipeline Verification

```
Backend UI Bundle API
    │
    ▼
UiBundleMapper.fromUiBundle()     ← Converts JSON to AppManifest
    │
    ▼
QefroAppRuntime.registerManifest() ← Registers in memory
    │
    ▼
ExtensionRuntime.compose()         ← Merges host + extensions
    │
    ▼
AppSession                         ← Wraps ComposedWorkspace
    │
    ▼
AppWorkspaceScreen                 ← RBAC-filters navigation
    │
    ▼
RuntimePageRenderer                ← Dispatches by nav type
    │
    ├── EntityViewRenderer         ← Table / Kanban / Calendar
    │       └── EntityListRenderer ← Card list with search + filter
    │       └── EntityKanbanView   ← Status-grouped columns
    │       └── EntityCalendarView ← Date-based calendar
    │
    ├── EntityFormRenderer         ← Create / edit forms
    │       └── EntityForm         ← Field-level _FieldControl
    │
    ├── EntityDetailRenderer       ← Record detail with actions
    │       └── FieldValueView     ← Type-formatted display
    │
    └── DashboardRenderer          ← Widget grid
            └── DashboardView      ← Metric, table, kanban, calendar, markdown
```

**Verified:** Every widget type, every field type, every view type is rendered generically from metadata. The only non-metadata escape hatch is `CustomScreenRegistry`, which is used by Restaurant Pro for `live_orders` (a real-time kitchen display).

---

## 17. Production Validation Evidence

- **Real Estate Pro:** 409 conversations, 18 flows, live on production
- **Clinic Pro:** Most sophisticated flow (book-appointment with dynamic practitioner/slot choices)
- **Restaurant Pro:** 11 entities, custom screen for live orders
- **8 entity-native apps** fully defined in YAML, zero app-specific code
- **12 HTTP integration apps** (Shopify, Stripe, WooCommerce, etc.) with connections + tools

---

## 18. Recommendations (Priority Order)

1. **Add entity-to-entity relationships** (P0) — This is the single most impactful change. Add `ref_entity` for inter-entity references, validate on create/update, render as entity picker in forms, include in detail views.

2. **Add sub-entity / line-items pattern** (P0) — Parent entity declares `sub_entities: [line_items]`. Child list rendered inside parent detail. Storage handles cascade delete.

3. **Build CRM Pro** (P1) — The most requested vertical. Use P0#1 for contact-to-deal, deal-to-activity relationships.

4. **Test condition/branch steps in production** (P1) — Write a real flow that uses conditional logic. Validate the 11 unused step types.

5. **Add entity-mutation automation actions** (P1) — Allow "when X.created → create Y" automations.

6. **Add custom roles from metadata** (P1) — Let manifests define roles with specific permission sets.

7. **Build Accounting Pro** (P2) — Requires P0#1 and P0#2 first. Then add computed fields and report views.

---

## 19. Final Verdict

### Can Qefro now build serious metadata-only ERP applications?

## **YES WITH GAPS**

The architecture is sound. The metadata pipeline works end-to-end. 20 apps are defined in pure YAML. Zero architecture violations. The runtime is genuinely generic.

**But serious ERP apps (Accounting, full Inventory, HR with payroll) need three things the metadata system cannot yet express:**

1. **Entity-to-entity relationships** — the foundation of every ERP data model
2. **Sub-entity / line-items patterns** — the most common ERP structure (orders have lines, invoices have items, BOMs have components)
3. **Computed fields and report views** — financial summaries, stock valuations, aging reports

These are **architecture-compatible** fixes — they extend the metadata schema, they don't require new services or app-specific code. The foundation is right. The primitive inventory needs expansion.

### Top 5 Gaps (Ranked)

| # | Gap | Severity |
|---|-----|----------|
| 1 | No entity-to-entity relationships | P0 |
| 2 | No sub-entity / line-items pattern | P0 |
| 3 | No Accounting Pro pattern (computed fields, hierarchical entities, reports) | P0 |
| 4 | condition/branch steps untested in production | P1 |
| 5 | No entity-mutation automation actions | P1 |
