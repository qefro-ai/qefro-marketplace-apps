# Metadata Extensions Design: Relationships, Sub-Entities, Computed Fields & Reporting

> **Status**: Design Proposal — NOT implemented
> **Scope**: Minimum generic extensions to the existing metadata-driven runtime
> **Constraint**: Domain-agnostic. No Qefro platform redesign. No new services unless unavoidable.

---

## 1. Current Architecture Relevant to This Change

### 1.1 Entity Metadata Pipeline

```
YAML entities/*.yaml
  → solution-service: EntityDefinition { id, fields, allocate_code, status_events }
  → MongoDB: solution package document
  → ai-customer-support: runtime_adapter parses capabilities
  → storage-service: generic CRUD per collection
  → Flutter: FieldDefinition → EntityViewRenderer / EntityFormRenderer
```

### 1.2 Key Existing Structures

**EntityField** (solution-service `entities.rs`):
```rust
pub struct EntityField {
    pub name: String,
    pub field_type: String,       // "string", "integer", "enum", etc.
    pub required: bool,
    pub description: Option<String>,
    pub enum_values: Vec<String>,
    pub ref_entity: Option<String>,   // ← ALREADY EXISTS, unused for inter-entity refs
    pub multiple: Option<bool>,       // ← ALREADY EXISTS
    pub max_items: Option<usize>,     // ← ALREADY EXISTS
}
```

**StorageContext** (storage-service `models.rs`):
```rust
pub struct StorageContext {
    pub tenant_id: Uuid,
    pub workspace_id: Uuid,
    pub installation_id: Uuid,
    pub solution_id: String,
    pub identity_id: Option<Uuid>,
    pub capabilities: Vec<String>,
    pub source: Option<String>,
}
```

**FindRequest** (storage-service `models.rs`):
```rust
pub struct FindRequest {
    pub context: StorageContext,
    pub collection: String,
    pub filter: Value,          // MongoDB query document
    pub limit: Option<i64>,
    pub sort: Option<Value>,
    pub include_deleted: bool,
    // NO: pagination cursor, field projection, aggregation, join/expand
}
```

**ConditionEvaluator** (flow_execution.rs):
```
Grammar: path OP literal | path 'exists' | path 'empty' | path (truthiness)
Operators: ==, !=, >, <, >=, <=
Types: Bool, Number (f64), Null, Str
NO: arithmetic, logical combinators (and/or), string functions
```

**Flutter FieldDefinition** (field_definition.dart):
```dart
class FieldDefinition {
  final String name;
  final String type;       // text, number, currency, select, relation, date...
  final String? entity;    // ← ALREADY EXISTS for relation references
  // ...
}
```
But `_mapFieldType()` in `ui_bundle_mapper.dart` does NOT map `"relation"` — it falls through to `'text'`.

### 1.3 What Exists Today

| Capability | Status |
|---|---|
| Entity CRUD from metadata | Working |
| Auto-code generation (allocate_code) | Working |
| Status lifecycle events | Working |
| Soft delete | Working |
| Scope isolation (tenant/workspace/installation) | Working |
| Entity-to-entity relationships | **Not implemented** |
| Sub-entity / line-items pattern | **Not implemented** |
| Computed / derived fields | **Not implemented** |
| Reporting / aggregation | **Not implemented** |
| Pagination | **Not implemented** (limit only) |
| Field projection | **Not implemented** |

---

## 2. Exact Files/Modules That Must Change

### 2.1 solution-service (Rust)

| File | Change |
|---|---|
| `src/solution/entities.rs` | Add `"relation"` to `KNOWN_FIELD_TYPES`. Add `computed` field metadata. Add `sub_entity_of` to `EntityDefinition`. Add validation for relation field consistency. |
| `src/solution/manifest.rs` | Add `reports/` to recognized bundle sections. |
| `src/solution/mod.rs` | Validation pass: ensure `sub_entity_of` targets exist, relation fields reference valid entities, no circular sub-entity chains. |

### 2.2 storage-service (Rust)

| File | Change |
|---|---|
| `src/models.rs` | Add `expand` field to `FindRequest`/`GetRequest`. Add `cursor`/`offset` for pagination. Add `AggregateRequest` struct. Add `project` field for field selection. |
| `src/repositories/mongo.rs` | Implement `$lookup` for expand (or post-fetch resolution). Implement cursor pagination. Implement `$group` aggregation pipeline. Implement field projection. |
| `src/routes.rs` | New endpoint: `POST /storage/aggregate`. Add query params for pagination cursor. |

### 2.3 ai-customer-support (Rust)

| File | Change |
|---|---|
| `crates/domain/src/flow_execution.rs` | Extend `ConditionEvaluator` with `and`/`or` combinators and basic arithmetic in templates. |
| `crates/api/src/tool_executor/storage.rs` | Pass through `expand`, `cursor`, `aggregate` parameters. |
| `crates/api/src/flow_engine/runtime_adapter.rs` | Add `entity.list_children` capability. Handle sub-entity cascade on delete. |
| `crates/api/src/agent/executor.rs` | Classify sub-entity operations under parent entity's action class. |

### 2.4 Flutter Mobile

| File | Change |
|---|---|
| `lib/core/api/ui_bundle_mapper.dart` | Map `"relation"` type properly. Map `computed` fields. Map `sub_entities`. |
| `lib/runtime/models/field_definition.dart` | Add `computed_expr`, `aggregate` fields. |
| `lib/runtime/models/entity_definition.dart` | Add `sub_entity_of`, `parent_entity`, `reports` fields. |
| `lib/runtime/page_runtime/entity_view_renderer.dart` | Render inline sub-entity lists. Render relation fields as tappable links. |
| `lib/runtime/page_runtime/entity_form_renderer.dart` | Sub-entity inline editing (add/remove rows). Relation picker widget. |
| `lib/runtime/page_runtime/report_renderer.dart` | **New file**. Render report metadata into summary cards / tables. |

### 2.5 qefro-marketplace-apps (Metadata)

| File | Change |
|---|---|
| `schemas/` | Add JSON schemas for relation fields, sub-entity declarations, computed fields, report definitions. |
| `examples/` | Add example apps demonstrating each new feature. |

---

## 3. Proposed Metadata Syntax

### 3.1 Relation Field

```yaml
# In entities/order.yaml
fields:
  - name: customer
    type: relation
    ref_entity: customer
    required: true
    description: "The customer who placed this order"

  - name: assigned_to
    type: relation
    ref_entity: employee
    required: false
    multiple: false
    description: "Sales representative"
```

### 3.2 Sub-Entity Declaration

```yaml
# In entities/order_line.yaml
id: order_line
name: Order Line
sub_entity_of: order          # ← NEW: declares parent relationship
parent_field: order           # ← NEW: the field name that holds the parent ref

fields:
  - name: order
    type: relation
    ref_entity: order
    required: true

  - name: product
    type: string
    required: true

  - name: quantity
    type: integer
    required: true

  - name: unit_price
    type: float
    required: true
```

The parent entity declares the reverse side:

```yaml
# In entities/order.yaml
sub_entities:
  - entity: order_line
    field: order              # which field on order_line points back
    inline: true              # show inline in parent UI
    label: "Line Items"
```

### 3.3 Computed Field

```yaml
fields:
  - name: total
    type: float
    computed:
      expr: "order_line.quantity * order_line.unit_price"
      aggregate: sum          # sum | count | avg | min | max
      source: order_line      # sub-entity to aggregate over
    description: "Sum of all line item totals"

  - name: tax
    type: float
    computed:
      expr: "subtotal * 0.14"
      depends_on: [subtotal]
    description: "14% VAT"

  - name: display_name
    type: string
    computed:
      expr: "concat(first_name, ' ', last_name)"
      depends_on: [first_name, last_name]
```

Computed fields are **read-only**. They are never sent in insert/update requests. The runtime computes them on read.

### 3.4 Report Definition

```yaml
# In reports/monthly_revenue.yaml
id: monthly_revenue
name: Monthly Revenue Report
entity: order                 # primary entity
group_by:
  - field: created_at
    granularity: month        # day | week | month | quarter | year
metrics:
  - field: total
    aggregate: sum
    label: "Total Revenue"
  - field: id
    aggregate: count
    label: "Order Count"
filters:
  - field: status
    op: "=="
    value: "completed"
sort:
  - field: created_at
    order: desc
```

---

## 4. Proposed Rust Data Structures

### 4.1 Extended EntityField (solution-service)

```rust
pub struct EntityField {
    pub name: String,
    pub field_type: String,
    pub required: bool,
    pub description: Option<String>,
    pub enum_values: Vec<String>,
    pub ref_entity: Option<String>,
    pub multiple: Option<bool>,
    pub max_items: Option<usize>,
    // NEW:
    pub computed: Option<ComputedField>,
}

pub struct ComputedField {
    pub expr: String,
    pub aggregate: Option<AggregateOp>,  // sum, count, avg, min, max
    pub source: Option<String>,           // sub-entity id for aggregation
    pub depends_on: Vec<String>,          // explicit dependency list
}

pub enum AggregateOp {
    #[serde(rename = "sum")] Sum,
    #[serde(rename = "count")] Count,
    #[serde(rename = "avg")] Avg,
    #[serde(rename = "min")] Min,
    #[serde(rename = "max")] Max,
}
```

### 4.2 Extended EntityDefinition (solution-service)

```rust
pub struct EntityDefinition {
    pub id: String,
    pub name: Option<String>,
    pub description: Option<String>,
    pub collection: Option<String>,
    pub fields: Vec<EntityField>,
    pub allocate_code: Option<AllocateCode>,
    pub status_field: Option<String>,
    pub status_events: BTreeMap<String, String>,
    // NEW:
    pub sub_entity_of: Option<String>,
    pub parent_field: Option<String>,
    pub sub_entities: Vec<SubEntityRef>,
}

pub struct SubEntityRef {
    pub entity: String,
    pub field: String,
    pub inline: Option<bool>,
    pub label: Option<String>,
}
```

### 4.3 Report Definition (solution-service)

```rust
pub struct ReportDefinition {
    pub id: String,
    pub name: String,
    pub entity: String,
    pub group_by: Vec<GroupByField>,
    pub metrics: Vec<MetricField>,
    pub filters: Vec<ReportFilter>,
    pub sort: Vec<SortField>,
}

pub struct GroupByField {
    pub field: String,
    pub granularity: Option<String>,  // day, week, month, quarter, year
}

pub struct MetricField {
    pub field: String,
    pub aggregate: AggregateOp,
    pub label: Option<String>,
}

pub struct ReportFilter {
    pub field: String,
    pub op: String,
    pub value: serde_json::Value,
}

pub struct SortField {
    pub field: String,
    pub order: Option<String>,  // asc, desc
}
```

### 4.4 Extended Storage Models (storage-service)

```rust
pub struct FindRequest {
    pub context: StorageContext,
    pub collection: String,
    pub filter: Value,
    pub limit: Option<i64>,
    pub sort: Option<Value>,
    pub include_deleted: bool,
    // NEW:
    pub expand: Option<Vec<ExpandSpec>>,
    pub cursor: Option<String>,
    pub page_size: Option<i64>,
    pub project: Option<Vec<String>>,
}

pub struct ExpandSpec {
    pub field: String,
    pub fields: Option<Vec<String>>,  // which fields to include from the related entity
    pub depth: Option<u8>,            // default 1
}

pub struct AggregateRequest {
    pub context: StorageContext,
    pub collection: String,
    pub filter: Value,
    pub group_by: Vec<GroupByField>,
    pub metrics: Vec<MetricField>,
    pub sort: Option<Vec<SortField>>,
    pub limit: Option<i64>,
}

pub struct AggregateResponse {
    pub groups: Vec<AggregateGroup>,
    pub total_count: Option<u64>,
}

pub struct AggregateGroup {
    pub key: Value,           // the grouped-by value(s)
    pub metrics: Value,       // { "total_revenue": 12345.0, "order_count": 42 }
}
```

---

## 5. Proposed Storage API Changes

### 5.1 Extended Find (existing endpoint)

`POST /storage/find` — body gains optional fields:

```json
{
  "context": { "..." : "..." },
  "collection": "order",
  "filter": { "status": "completed" },
  "limit": 20,
  "expand": [
    { "field": "customer", "fields": ["name", "email"] },
    { "field": "order_line", "fields": ["product", "quantity", "unit_price"] }
  ],
  "cursor": "eyJpZCI6ICI1ZmJj...",
  "page_size": 20,
  "project": ["code", "status", "total", "customer", "created_at"]
}
```

**Expand resolution strategy**: Post-fetch, not `$lookup`.

Rationale: storage-service is domain-agnostic and must not learn about entity metadata. The caller (ai-customer-support runtime_adapter or a new thin resolver) knows which entity a relation field points to and which MongoDB collection holds it. After the primary find, it issues secondary finds for each distinct relation ID and merges the results in memory.

For sub-entities (reverse relation), the expand issues a find on the child collection filtered by `{ parent_field: { $in: [parent_ids] } }` and groups results by parent ID.

This keeps storage-service completely unaware of relationships. The expansion logic lives in a shared utility crate (`storage-expand`) used by both ai-customer-support (tool_executor) and storage-service (as an optional middleware).

### 5.2 New Aggregate Endpoint

`POST /storage/aggregate` — new endpoint:

```json
{
  "context": { "..." : "..." },
  "collection": "order",
  "filter": { "status": "completed" },
  "group_by": [
    { "field": "created_at", "granularity": "month" }
  ],
  "metrics": [
    { "field": "total", "aggregate": "sum" },
    { "field": "id", "aggregate": "count" }
  ],
  "sort": [{ "field": "created_at", "order": "desc" }],
  "limit": 12
}
```

Response:

```json
{
  "groups": [
    { "key": { "created_at": "2026-09" }, "metrics": { "sum_total": 125000.0, "count_id": 42 } },
    { "key": { "created_at": "2026-08" }, "metrics": { "sum_total": 98000.0, "count_id": 35 } }
  ],
  "total_count": 2
}
```

Implementation: MongoDB `$match` → `$group` → `$sort` → `$limit` pipeline. The storage-service translates the generic request into the pipeline without knowing what "order" or "total" means.

### 5.3 Pagination

Cursor-based. The `cursor` field is an opaque base64-encoded JSON of the last document's sort key values. storage-service decodes it into a `{ _id: { $gt: last_id } }` filter clause combined with the user's filter.

Response gains a `next_cursor` field (null when no more pages).

---

## 6. Proposed Runtime Changes

### 6.1 Computed Field Resolution

Computed fields are resolved **at read time** by the layer that assembles the response. Two categories:

**Category A: Simple expressions (depends_on own fields)**

```yaml
computed:
  expr: "subtotal * 0.14"
  depends_on: [subtotal]
```

Resolved by the same post-fetch logic that handles expand. After fetching the document, evaluate `expr` against the document's own fields. The expression evaluator is a simple arithmetic parser: `+`, `-`, `*`, `/`, parentheses, field references, numeric literals, and `concat()`.

**Category B: Sub-entity aggregations**

```yaml
computed:
  expr: "order_line.quantity * order_line.unit_price"
  aggregate: sum
  source: order_line
```

Resolved by first expanding the sub-entity (fetching all order_lines for this order), evaluating `expr` for each child, then applying `aggregate`.

**Where does this logic live?**

In a new shared crate: `metadata-compute` (or a module within solution-service). Both storage-service (when returning documents) and ai-customer-support (when formatting tool results for the Agent) use it.

Alternative: resolve entirely in ai-customer-support after receiving raw documents from storage-service. This is simpler and keeps storage-service 100% domain-agnostic. **Recommended for Phase 1.**

### 6.2 Sub-Entity Lifecycle

**Create**: When a parent entity is created with inline sub-entities, the runtime:
1. Inserts the parent document.
2. For each inline sub-entity, injects the parent's ID into the `parent_field`, then inserts each child.
3. Returns the parent with children embedded.

**Read**: When a parent is fetched, sub-entities are automatically expanded (if `inline: true`).

**Update**: Sub-entities are updated individually via their own entity endpoints. The parent's update payload can include `_children: { order_line: { add: [...], update: [...], remove: [...] } }` for batch operations.

**Delete**: When a parent is soft-deleted, all sub-entities are also soft-deleted (cascade). This is the ONE place where cascade behavior exists. It is implemented as a post-delete hook in the runtime_adapter, not in storage-service.

### 6.3 Relation Field Validation

On insert/update of an entity with a `relation` field:
1. The runtime checks that the referenced entity exists (GET from storage-service).
2. If `multiple: true`, checks each ID in the array.
3. If `max_items` is set, enforces the limit.
4. If the relation is `required`, rejects null/empty.

This validation happens in ai-customer-support's runtime_adapter (the layer that already does authority stripping and permission checks), NOT in storage-service.

---

## 7. Proposed Flutter Metadata Changes

### 7.1 ui_bundle_mapper.dart

Add relation type mapping:

```dart
case 'relation':
  return FieldType.relation;
```

Add computed field mapping:

```dart
case 'computed':
  return FieldType.computed;  // read-only display
```

### 7.2 FieldDefinition Extensions

```dart
class FieldDefinition {
  // existing...
  final String? entity;           // relation target (already exists)
  final bool multiple;            // for multi-select relations
  final int? maxItems;

  // NEW:
  final ComputedFieldDef? computed;
  final SubEntityRef? subEntityOf;
}

class ComputedFieldDef {
  final String expr;
  final String? aggregate;
  final String? source;
  final List<String> dependsOn;
}

class SubEntityRef {
  final String entity;
  final String field;
  final bool inline;
  final String label;
}
```

### 7.3 Entity Definition Extensions

```dart
class EntityDefinition {
  // existing...

  // NEW:
  final String? subEntityOf;
  final String? parentField;
  final List<SubEntityRef> subEntities;
  final List<ReportDefinition> reports;
}
```

### 7.4 UI Components

**Relation picker**: A dropdown/search field that queries the related entity's list endpoint and displays a human-readable field (e.g., customer name). Stores the UUID.

**Sub-entity inline editor**: A section within the parent form showing a list of child rows. Each row is a mini-form. "Add Line" button appends a new empty row. Swipe-to-delete removes a row. On save, the parent form batches create/update/delete operations.

**Computed field display**: Read-only text widget. Shows the computed value from the server. Never editable.

**Report view**: A new page type in the UI bundle. Renders as a summary card list or a data table with grouped rows.

---

## 8. Proposed FlowRunner Changes

### 8.1 ConditionEvaluator Extensions

Current grammar: `path OP literal`

Extended grammar:

```
expr     := comparison (('and' | 'or') comparison)*
comparison := path OP value | path 'exists' | path 'empty' | path
OP       := '==' | '!=' | '>' | '<' | '>=' | '<=' | 'contains' | 'in' | 'not_in'
value    := literal | '{{ template }}'
path     := dotted.path.segments
```

This aligns the flow engine's evaluator with the CRM automation evaluator (which already has `contains`, `in`, `not_in`, `and`, `or`). The CRM evaluator should be extracted into a shared module and reused.

### 8.2 Template Arithmetic

Current template resolution: `{{ path }}` → string substitution.

Extended: support arithmetic in templates for computed field expressions:

```
{{ order_line.quantity }} * {{ order_line.unit_price }}
```

This is only needed in the metadata-compute crate, not in the general FlowVariableContext template resolver. The flow engine's `resolve_template` stays string-only.

### 8.3 New Step Type: `aggregate`

For flows that need to compute totals before branching:

```yaml
steps:
  - id: calc_total
    type: aggregate
    entity: order_line
    filter: "order == {{ current_order.id }}"
    metrics:
      - field: quantity
        aggregate: sum
        output: total_quantity
      - field: unit_price
        aggregate: avg
        output: avg_price

  - id: check_minimum
    type: condition
    conditions:
      - "total_quantity >= 10"
    on_match: apply_bulk_discount
    on_no_match: continue
```

This is a **Phase 2** addition. Phase 1 handles computed fields at the storage/read layer, not in flows.

### 8.4 Sub-Entity-Aware Tool Results

When the Agent calls `entity.order.get` and the order has inline sub-entities, the tool result should include the expanded children. This is handled by the expand mechanism in storage tool_executor — no FlowRunner change needed, just a storage call change.

---

## 9. Proposed Event Semantics

### 9.1 New Event Types

```
entity.sub_entity.created    — a child record was created under a parent
entity.sub_entity.updated    — a child record was updated
entity.sub_entity.deleted    — a child record was deleted (individual or cascade)
entity.relation.changed      — a relation field on an entity was changed
```

### 9.2 Event Payload

```json
{
  "event": "entity.sub_entity.created",
  "tenant_id": "...",
  "workspace_id": "...",
  "installation_id": "...",
  "entity": "order_line",
  "parent_entity": "order",
  "parent_id": "uuid-of-parent",
  "record_id": "uuid-of-child",
  "data": { "..." : "..." }
}
```

### 9.3 Flow Triggering

Flows can trigger on sub-entity events:

```yaml
triggers:
  - event: entity.sub_entity.created
    entity: order_line
    filter: "parent.order.status == pending"
```

This uses the existing event bus (Postgres-backed with idempotency, replay, dead-letter, loop protection). No new transport needed.

### 9.4 Cascade Events

When a parent is deleted and children cascade-delete, each child deletion emits its own `entity.sub_entity.deleted` event, followed by the parent's `entity.deleted` event. This allows flows to react to individual child deletions if needed.

---

## 10. Proposed Security Model

### 10.1 Capability Extensions

New capabilities follow the existing pattern:

```
entity.{entity_name}.create
entity.{entity_name}.list
entity.{entity_name}.get
entity.{entity_name}.update
entity.{entity_name}.delete
```

Sub-entities use their own entity name:

```
entity.order_line.create    — needed to add line items
entity.order_line.list      — needed to view line items
```

No new capability verbs. The existing CRUD vocabulary is sufficient.

### 10.2 Relation Field Authorization

When a user creates/updates an entity with a relation field:
1. The runtime validates the relation target exists (requires `entity.{ref_entity}.get` capability).
2. The user must have `get` permission on the target entity. If not, the write is rejected.
3. The FORBIDDEN_AUTHORITY_KEYS list already prevents authority injection — no change needed.

### 10.3 Sub-Entity Authorization

Sub-entities are scoped by their parent. The runtime_adapter enforces:
1. To create a sub-entity, the user needs both `entity.{child}.create` AND `entity.{parent}.get`.
2. To list sub-entities, the user needs `entity.{child}.list` AND `entity.{parent}.get`.
3. The scope filter automatically restricts sub-entities to the same tenant/workspace/installation as the parent.

### 10.4 Report Authorization

Reports are read-only. They require `entity.{entity}.list` on the primary entity. The aggregate endpoint enforces the same scope isolation as find — every aggregation pipeline starts with the scope filter as the first `$match` stage.

### 10.5 Agent Action Classification

Sub-entity operations inherit the parent's action class:
- `entity.order_line.create` when order_line is a sub-entity of order → classified under the parent order's context.
- Creating a line item on a financial order → `Financial` action class (same as the order itself).

Relation reads are `Read` class. Relation writes are `Write` class. No new action classes needed.

---

## 11. Proposed Agent Integration

### 11.1 ConversationState Extensions

The existing `ConversationState` already tracks entity mentions:

```rust
pub struct EntityMention {
    pub entity: String,
    pub id: Option<String>,
    pub data: Option<Value>,
    // ...
}
```

Sub-entity mentions are tracked as separate entity mentions with a `parent_id` field:

```rust
pub struct EntityMention {
    pub entity: String,
    pub id: Option<String>,
    pub data: Option<Value>,
    pub parent_entity: Option<String>,   // NEW
    pub parent_id: Option<String>,       // NEW
}
```

This allows the Agent to resolve "add a line item to the last order" by looking up the most recent order mention.

### 11.2 WorkingContext Extensions

The `WorkingContext` already has `domain`, `intent`, `filters`, `results`. For sub-entities, the focus can be on a parent entity with a sub-entity context:

```rust
pub struct WorkingContext {
    // existing...
    pub focus_children: Option<ChildrenFocus>,  // NEW
}

pub struct ChildrenFocus {
    pub parent_entity: String,
    pub parent_id: String,
    pub child_entity: String,
    pub results: Vec<Value>,
}
```

This enables follow-up questions like "what's the total quantity?" to resolve against the focused children.

### 11.3 Tool Result Formatting

When the Agent calls `entity.order.get` and the result includes expanded sub-entities, the tool result should format them clearly:

```json
{
  "entity": "order",
  "id": "uuid",
  "code": "ORD-1001",
  "status": "pending",
  "customer": { "name": "Acme Corp", "email": "orders@acme.com" },
  "order_lines": [
    { "product": "Widget A", "quantity": 10, "unit_price": 25.00 },
    { "product": "Widget B", "quantity": 5, "unit_price": 40.00 }
  ],
  "total": 450.00
}
```

The Agent can then reason about line items naturally: "The order has 2 line items totaling $450."

### 11.4 Capability Flags

No new capability flags needed in `metadata.rs`. The existing 9 flags (analytics, promotions, pricing, refunds, orders, reservations, inventory, customers, knowledge) are domain-level. Sub-entity operations are entity-level, handled by the existing entity capability parsing.

---

## 12. Backward Compatibility

### 12.1 Existing Metadata

All new fields are optional. Existing entity YAML files work unchanged:
- `sub_entity_of`: absent → not a sub-entity (current behavior).
- `sub_entities`: empty/absent → no children (current behavior).
- `computed`: absent → regular field (current behavior).
- `relation` type: not used by any existing app (no conflict).
- `expand` in FindRequest: absent → no expansion (current behavior).

### 12.2 Existing Storage API

The storage API is additive:
- `expand`, `cursor`, `page_size`, `project` are optional fields in FindRequest.
- `POST /storage/aggregate` is a new endpoint — no existing endpoint changes.
- Response gains optional `next_cursor` field.

### 12.3 Existing Flutter UI

- `_mapFieldType()` gains a `"relation"` case — existing types unaffected.
- `FieldDefinition` gains optional fields — existing constructors work with defaults.
- New `report_renderer.dart` is additive — existing page types unaffected.

### 12.4 Existing Flow Steps

- No existing step type changes.
- New `aggregate` step type is Phase 2 — Phase 1 uses only read-time computation.
- ConditionEvaluator gains `and`/`or` — existing single-condition expressions still parse correctly (the `(('and' | 'or') comparison)*` suffix matches zero times).

### 12.5 Existing Events

- New event types are additive. Existing event subscriptions are unaffected.
- The event bus schema (Postgres) does not change — event type is a text column.

---

## 13. Migration Strategy

### 13.1 Phase 1: Foundation (No Migration Needed)

All Phase 1 changes are additive. No existing data needs migration.

1. Add `"relation"` to `KNOWN_FIELD_TYPES` in solution-service.
2. Add optional fields to EntityField, EntityDefinition structs (serde default).
3. Add optional fields to FindRequest, GetRequest (serde default).
4. Add `POST /storage/aggregate` endpoint.
5. Add expand resolution logic in ai-customer-support.
6. Add computed field resolution in ai-customer-support.
7. Add Flutter relation/sub-entity/computed rendering.

### 13.2 Phase 2: Flow Integration

1. Extend ConditionEvaluator with `and`/`or`/`contains`/`in`/`not_in`.
2. Add `aggregate` step type.
3. Add sub-entity batch operations (`_children` payload).

### 13.3 Phase 3: Reporting UI

1. Add report renderer in Flutter.
2. Add report definitions to UI bundle.
3. Add report navigation in entity views.

### 13.4 No Database Migration

- MongoDB: no schema changes. New fields are stored as document properties. Existing documents lack the new fields, which is fine (optional).
- PostgreSQL (registry/audit): no schema changes. Event types are text. Audit log entries are JSON.
- storage-service collections: no new tables/collections. Sub-entities use their own collections (already how entities work).

---

## 14. Test Strategy

### 14.1 Unit Tests

**solution-service**:
- Parse entity YAML with `type: relation` → EntityField with ref_entity populated.
- Parse entity YAML with `sub_entity_of` → EntityDefinition with sub_entity_of set.
- Parse entity YAML with `computed` → EntityField with computed populated.
- Validate: sub_entity_of references a valid entity in the same solution.
- Validate: relation field references a valid entity in the same solution.
- Validate: no circular sub-entity chains (A→B→A).
- Parse report YAML → ReportDefinition.

**storage-service**:
- FindRequest with `expand` → correct post-fetch resolution.
- FindRequest with `cursor` → correct pagination.
- AggregateRequest → correct MongoDB pipeline generation.
- AggregateRequest with scope filter → scope enforced in `$match`.
- FindRequest with `project` → correct field projection.

**ai-customer-support**:
- ConditionEvaluator with `and`/`or` → correct boolean logic.
- Computed field resolution: simple arithmetic.
- Computed field resolution: sub-entity aggregation.
- Relation validation: existing target → pass.
- Relation validation: non-existing target → reject.
- Sub-entity cascade delete: parent deleted → children soft-deleted.
- Cascade events emitted in correct order.

**Flutter**:
- `_mapFieldType("relation")` → FieldType.relation.
- FieldDefinition with computed → read-only rendering.
- EntityDefinition with sub_entities → inline section rendered.
- Report metadata → report page rendered.

### 14.2 Integration Tests

1. Create an Order with 3 OrderLines via Agent conversation → verify all records created.
2. Fetch Order → verify OrderLines expanded inline.
3. Update OrderLine → verify computed `total` on Order recalculated.
4. Delete Order → verify OrderLines cascade-deleted.
5. Run aggregate query on Orders grouped by month → verify correct sums.
6. Agent conversation: "Add a line item to my last order" → verify correct parent resolution.
7. RBAC: user without `entity.order_line.create` cannot add line items.
8. Scope isolation: tenant A cannot see tenant B's sub-entities.

### 14.3 Property Tests

- Arbitrary entity metadata with random relation fields → validation never panics.
- Arbitrary computed expressions → parser handles all valid expressions, rejects all invalid ones.
- Arbitrary aggregate requests → MongoDB pipeline is always valid.

---

## 15. Example Metadata

### 15A. Order + OrderLine

```yaml
# entities/order.yaml
id: order
name: Order
allocate_code:
  prefix: "ORD"
  pad: 4
  field: code
status_field: status
status_events:
  place: draft → pending
  confirm: pending → confirmed
  ship: confirmed → shipped
  deliver: shipped → completed
  cancel: "*" → cancelled

fields:
  - name: code
    type: string
    required: true
  - name: customer
    type: relation
    ref_entity: customer
    required: true
  - name: status
    type: enum
    enum_values: [draft, pending, confirmed, shipped, completed, cancelled]
    required: true
  - name: order_date
    type: date
    required: true
  - name: subtotal
    type: float
    computed:
      expr: "order_line.quantity * order_line.unit_price"
      aggregate: sum
      source: order_line
  - name: tax
    type: float
    computed:
      expr: "subtotal * 0.14"
      depends_on: [subtotal]
  - name: total
    type: float
    computed:
      expr: "subtotal + tax"
      depends_on: [subtotal, tax]

sub_entities:
  - entity: order_line
    field: order
    inline: true
    label: "Line Items"
```

```yaml
# entities/order_line.yaml
id: order_line
name: Order Line
sub_entity_of: order
parent_field: order

fields:
  - name: order
    type: relation
    ref_entity: order
    required: true
  - name: product
    type: string
    required: true
  - name: quantity
    type: integer
    required: true
  - name: unit_price
    type: float
    required: true
  - name: line_total
    type: float
    computed:
      expr: "quantity * unit_price"
      depends_on: [quantity, unit_price]
```

```yaml
# entities/customer.yaml
id: customer
name: Customer

fields:
  - name: name
    type: string
    required: true
  - name: email
    type: email
    required: true
  - name: phone
    type: phone
```

### 15B. Invoice + InvoiceLine

```yaml
# entities/invoice.yaml
id: invoice
name: Invoice
allocate_code:
  prefix: "INV"
  pad: 4
  field: code
status_field: status
status_events:
  issue: draft → open
  pay: open → paid
  overdue: open → overdue
  cancel: "*" → void

fields:
  - name: code
    type: string
    required: true
  - name: customer
    type: relation
    ref_entity: customer
    required: true
  - name: order
    type: relation
    ref_entity: order
    required: false
    description: "Optional: link to source order"
  - name: status
    type: enum
    enum_values: [draft, open, paid, overdue, void]
    required: true
  - name: issue_date
    type: date
    required: true
  - name: due_date
    type: date
    required: true
  - name: subtotal
    type: float
    computed:
      expr: "invoice_line.quantity * invoice_line.unit_price"
      aggregate: sum
      source: invoice_line
  - name: tax
    type: float
    computed:
      expr: "subtotal * 0.14"
      depends_on: [subtotal]
  - name: total
    type: float
    computed:
      expr: "subtotal + tax"
      depends_on: [subtotal, tax]

sub_entities:
  - entity: invoice_line
    field: invoice
    inline: true
    label: "Invoice Items"
```

```yaml
# entities/invoice_line.yaml
id: invoice_line
name: Invoice Line
sub_entity_of: invoice
parent_field: invoice

fields:
  - name: invoice
    type: relation
    ref_entity: invoice
    required: true
  - name: description
    type: string
    required: true
  - name: quantity
    type: integer
    required: true
  - name: unit_price
    type: float
    required: true
  - name: line_total
    type: float
    computed:
      expr: "quantity * unit_price"
      depends_on: [quantity, unit_price]
```

### 15C. BOM + Component

```yaml
# entities/bom.yaml
id: bom
name: Bill of Materials
allocate_code:
  prefix: "BOM"
  pad: 4
  field: code

fields:
  - name: code
    type: string
    required: true
  - name: product_name
    type: string
    required: true
  - name: version
    type: string
    required: true
  - name: component_count
    type: integer
    computed:
      expr: "bom_component.id"
      aggregate: count
      source: bom_component
  - name: total_material_cost
    type: float
    computed:
      expr: "bom_component.quantity * bom_component.unit_cost"
      aggregate: sum
      source: bom_component

sub_entities:
  - entity: bom_component
    field: bom
    inline: true
    label: "Components"
```

```yaml
# entities/bom_component.yaml
id: bom_component
name: BOM Component
sub_entity_of: bom
parent_field: bom

fields:
  - name: bom
    type: relation
    ref_entity: bom
    required: true
  - name: material
    type: string
    required: true
  - name: quantity
    type: float
    required: true
  - name: unit
    type: enum
    enum_values: [kg, g, L, mL, pcs, m, cm]
    required: true
  - name: unit_cost
    type: float
    required: true
  - name: line_cost
    type: float
    computed:
      expr: "quantity * unit_cost"
      depends_on: [quantity, unit_cost]
```

### 15D. Employee + Manager (Self-Reference)

```yaml
# entities/employee.yaml
id: employee
name: Employee
allocate_code:
  prefix: "EMP"
  pad: 4
  field: code

fields:
  - name: code
    type: string
    required: true
  - name: first_name
    type: string
    required: true
  - name: last_name
    type: string
    required: true
  - name: email
    type: email
    required: true
  - name: department
    type: enum
    enum_values: [Engineering, Sales, Marketing, Operations, HR, Finance]
    required: true
  - name: title
    type: string
    required: true
  - name: manager
    type: relation
    ref_entity: employee          # ← self-reference
    required: false
    description: "Reporting manager"
  - name: full_name
    type: string
    computed:
      expr: "concat(first_name, ' ', last_name)"
      depends_on: [first_name, last_name]
  - name: direct_reports_count
    type: integer
    computed:
      expr: "employee.id"
      aggregate: count
      source: employee            # count employees where manager == this
      filter_field: manager       # which field on the source entity points back
```

Self-reference is a special case: the `ref_entity` equals the defining entity. The runtime handles this normally — it's just a relation field where the target collection is the same as the source collection. The `direct_reports_count` computed field uses `filter_field: manager` to specify which field on the source entity to filter by (since it's self-referential, the sub_entity pattern doesn't apply directly).

---

## 16. Example BusinessFlows Using Relationships

### 16A. Create Order with Line Items

```yaml
# workflows/create_order.yaml
id: create_order
name: Create Order
trigger:
  type: intent
  match: "create_order"

steps:
  - id: ask_customer
    type: ask
    prompt: "Which customer is this order for?"
    slot: customer

  - id: lookup_customer
    type: tool
    tool: entity.customer.list
    params:
      filter:
        name: "{{ customer }}"
    output: customer_results

  - id: collect_items
    type: ask
    prompt: "What items should I add to this order? Please describe each item with product name, quantity, and price."
    slot: items_json

  - id: create_order
    type: tool
    tool: entity.order.create
    params:
      data:
        customer: "{{ customer_results[0].id }}"
        status: pending
        order_date: "{{ now }}"
    output: new_order

  - id: add_lines
    type: tool
    tool: entity.order_line.create_batch
    params:
      data: "{{ items_json | map({ order: new_order.id, product: item.product, quantity: item.quantity, unit_price: item.price }) }}"
    output: created_lines

  - id: confirm
    type: message
    message: "Order {{ new_order.code }} created with {{ created_lines | length }} items. Total: {{ new_order.total }}"

  - id: done
    type: complete
```

### 16B. Auto-Generate Invoice from Completed Order

```yaml
# workflows/generate_invoice.yaml
id: generate_invoice
name: Generate Invoice
trigger:
  type: event
  event: entity.order.updated
  filter: "status == completed"

steps:
  - id: fetch_order
    type: tool
    tool: entity.order.get
    params:
      id: "{{ event.record_id }}"
      expand: ["order_line"]
    output: order

  - id: create_invoice
    type: tool
    tool: entity.invoice.create
    params:
      data:
        customer: "{{ order.customer }}"
        order: "{{ order.id }}"
        status: open
        issue_date: "{{ now }}"
        due_date: "{{ now + 30 days }}"
    output: new_invoice

  - id: copy_lines
    type: tool
    tool: entity.invoice_line.create_batch
    params:
      data: "{{ order.order_line | map({ invoice: new_invoice.id, description: item.product, quantity: item.quantity, unit_price: item.unit_price }) }}"

  - id: notify
    type: message
    message: "Invoice {{ new_invoice.code }} generated for Order {{ order.code }}. Total: {{ new_invoice.total }}"

  - id: done
    type: complete
```

### 16C. BOM Cost Check Before Production

```yaml
# workflows/bom_cost_check.yaml
id: bom_cost_check
name: BOM Cost Check
trigger:
  type: intent
  match: "check_bom_cost"

steps:
  - id: ask_bom
    type: ask
    prompt: "Which BOM should I check?"
    slot: bom_code

  - id: fetch_bom
    type: tool
    tool: entity.bom.get
    params:
      filter:
        code: "{{ bom_code }}"
      expand: ["bom_component"]
    output: bom

  - id: cost_check
    type: condition
    conditions:
      - "bom.total_material_cost > 1000"
    on_match: warn_high_cost
    on_no_match: report_ok

  - id: warn_high_cost
    type: message
    message: "Warning: BOM {{ bom.code }} ({{ bom.product_name }}) has a high material cost of {{ bom.total_material_cost }} across {{ bom.component_count }} components."

  - id: report_ok
    type: message
    message: "BOM {{ bom.code }} ({{ bom.product_name }}) has {{ bom.component_count }} components with a total material cost of {{ bom.total_material_cost }}."

  - id: done
    type: complete
```

---

## 17. Example UI Metadata

### 17A. Order List View with Relation Display

```yaml
# ui/order_list.yaml
page: entity_list
entity: order
title: Orders
view: table
columns:
  - field: code
    label: Order #
  - field: customer
    label: Customer
    display: relation.name        # show the customer's name
  - field: order_date
    label: Date
  - field: total
    label: Total
    format: currency
  - field: status
    label: Status
    style: badge
actions:
  - label: New Order
    flow: create_order
```

### 17B. Order Detail with Inline Sub-Entities

```yaml
# ui/order_detail.yaml
page: entity_detail
entity: order
title: "Order {{ code }}"
sections:
  - type: fields
    columns:
      - [code, order_date, status]
      - [customer, total, tax]

  - type: sub_entity
    entity: order_line
    label: Line Items
    view: table
    columns:
      - field: product
        label: Product
      - field: quantity
        label: Qty
      - field: unit_price
        label: Unit Price
        format: currency
      - field: line_total
        label: Total
        format: currency
    actions:
      - label: Add Line
        action: add_child
      - label: Remove
        action: remove_child

  - type: actions
    actions:
      - label: Confirm Order
        flow: confirm_order
        condition: "status == pending"
      - label: Generate Invoice
        flow: generate_invoice
        condition: "status == completed"
```

### 17C. Order Form with Relation Picker and Inline Sub-Entity Editor

```yaml
# ui/order_form.yaml
page: entity_form
entity: order
title: New Order
fields:
  - field: customer
    widget: relation_picker
    display_field: name
    search_fields: [name, email]
    label: Customer
  - field: order_date
    widget: date_picker
    label: Order Date

sub_entities:
  - entity: order_line
    label: Line Items
    widget: inline_table_editor
    fields:
      - field: product
        widget: text_input
        label: Product
      - field: quantity
        widget: number_input
        label: Qty
      - field: unit_price
        widget: number_input
        label: Unit Price
        format: currency
    add_label: "Add Line Item"
    remove_label: "Remove"
```

### 17D. Employee Detail with Self-Reference

```yaml
# ui/employee_detail.yaml
page: entity_detail
entity: employee
title: "{{ full_name }}"
sections:
  - type: fields
    columns:
      - [code, title, department]
      - [email, manager, direct_reports_count]
    field_overrides:
      manager:
        display: relation.full_name    # show manager's full name
        tappable: true                  # tap to navigate to manager's detail
```

---

## 18. Example Report Metadata

### 18A. Monthly Revenue Report

```yaml
# reports/monthly_revenue.yaml
id: monthly_revenue
name: Monthly Revenue
description: "Revenue and order count by month"
entity: order
group_by:
  - field: order_date
    granularity: month
metrics:
  - field: total
    aggregate: sum
    label: Revenue
    format: currency
  - field: id
    aggregate: count
    label: Orders
filters:
  - field: status
    op: "in"
    value: [completed, shipped]
sort:
  - field: order_date
    order: desc
limit: 12
```

### 18B. Top Customers Report

```yaml
# reports/top_customers.yaml
id: top_customers
name: Top Customers
description: "Customers by total order value"
entity: order
group_by:
  - field: customer
metrics:
  - field: total
    aggregate: sum
    label: Total Spent
    format: currency
  - field: id
    aggregate: count
    label: Order Count
filters:
  - field: status
    op: "!="
    value: cancelled
sort:
  - field: total
    order: desc
    metric: true          # sort by the aggregated metric, not a raw field
limit: 20
```

### 18C. BOM Cost Summary

```yaml
# reports/bom_cost_summary.yaml
id: bom_cost_summary
name: BOM Cost Summary
description: "Material costs across all BOMs"
entity: bom
group_by:
  - field: code
metrics:
  - field: total_material_cost
    aggregate: sum
    label: Total Cost
    format: currency
  - field: component_count
    aggregate: sum
    label: Components
sort:
  - field: total_material_cost
    order: desc
    metric: true
```

### 18D. Employee Headcount by Department

```yaml
# reports/department_headcount.yaml
id: department_headcount
name: Department Headcount
description: "Employee count by department"
entity: employee
group_by:
  - field: department
metrics:
  - field: id
    aggregate: count
    label: Employees
sort:
  - field: department
    order: asc
```

---

## 19. P0/P1/P2 Classification

### P0 — Cannot build serious apps without this

| # | Gap | Design Section | Effort |
|---|---|---|---|
| 1 | `relation` field type not in KNOWN_FIELD_TYPES | §3.1, §4.1 | Trivial — add string to array |
| 2 | No expand/resolution for relation fields | §5.1, §6 | Medium — post-fetch resolver |
| 3 | No sub-entity declaration or lifecycle | §3.2, §4.2, §6.2 | Medium — metadata + cascade |
| 4 | No computed field support | §3.3, §4.1, §6.1 | Medium — expression evaluator |
| 5 | Flutter doesn't map `relation` type | §7.1, §7.4 | Small — mapper + widgets |

### P1 — Needed for production-quality apps

| # | Gap | Design Section | Effort |
|---|---|---|---|
| 6 | No pagination (cursor-based) | §5.3 | Small — MongoDB cursor |
| 7 | No aggregate endpoint | §5.2, §4.4 | Medium — MongoDB pipeline |
| 8 | ConditionEvaluator lacks `and`/`or` | §8.1 | Small — parser extension |
| 9 | No inline sub-entity editor in Flutter | §7.4 | Medium — new widget |
| 10 | No relation picker widget in Flutter | §7.4 | Medium — new widget |
| 11 | No report rendering in Flutter | §7.4, §18 | Medium — new page type |

### P2 — Nice to have, not blocking

| # | Gap | Design Section | Effort |
|---|---|---|---|
| 12 | `aggregate` step type in flows | §8.3 | Medium |
| 13 | Sub-entity batch operations (`_children` payload) | §6.2 | Medium |
| 14 | Field projection in find requests | §5.1 | Small |
| 15 | Self-referential relation computed fields | §15D | Small |
| 16 | Report sort by metric | §18 | Small |

---

## 20. Minimal Implementation Sequence

### Sprint 1: Relation Fields (P0 #1, #2, #5)

**Goal**: Entity metadata can declare relation fields. The runtime resolves them. Flutter renders them.

1. Add `"relation"` to `KNOWN_FIELD_TYPES` in solution-service `entities.rs`.
2. Add validation: relation field's `ref_entity` must reference an entity in the same solution.
3. Add post-fetch expand resolver in ai-customer-support (shared utility).
4. Wire expand through `invoke_storage()` in tool_executor.
5. Flutter: map `"relation"` type in `_mapFieldType()`. Render as tappable text showing the related entity's primary display field.
6. Test: create an Order with a customer relation, verify it resolves in Agent responses and Flutter UI.

**Deliverable**: Orders can reference Customers. Agent says "Order ORD-1001 for Acme Corp" instead of "Order ORD-1001 for customer UUID abc-123".

### Sprint 2: Sub-Entities (P0 #3)

**Goal**: Entity metadata can declare parent-child relationships. CRUD cascades correctly.

1. Add `sub_entity_of`, `parent_field`, `sub_entities` to EntityDefinition.
2. Add validation: `sub_entity_of` target must exist, no circular chains.
3. Implement cascade soft-delete in runtime_adapter.
4. Auto-expand inline sub-entities on parent GET.
5. Flutter: render inline sub-entity section in entity detail view.
6. Test: create Order with OrderLines, verify cascade delete, verify inline display.

**Deliverable**: Orders have line items. Deleting an order deletes its line items.

### Sprint 3: Computed Fields (P0 #4)

**Goal**: Entity metadata can declare computed fields. Values are calculated at read time.

1. Add `computed` to EntityField struct.
2. Implement simple arithmetic expression evaluator (own-field computed fields).
3. Implement sub-entity aggregation computed fields (uses expand from Sprint 2).
4. Computed fields are read-only — strip from insert/update payloads.
5. Flutter: render computed fields as read-only text.
6. Test: Order.total = sum(OrderLine.line_total). Verify recalculation on child change.

**Deliverable**: Order totals, tax calculations, BOM costs — all computed automatically from metadata.

### Sprint 4: Pagination + Aggregation (P1 #6, #7)

**Goal**: Lists are paginated. Aggregate queries work for reporting.

1. Add cursor pagination to FindRequest/FindResponse.
2. Add `POST /storage/aggregate` endpoint.
3. Implement MongoDB `$group` pipeline.
4. Test: paginate through 100+ orders. Run monthly revenue aggregate.

**Deliverable**: Large lists are usable. Reports can be generated.

### Sprint 5: Condition Evaluator + Report UI (P1 #8, #9, #10, #11)

**Goal**: Flows can use complex conditions. Reports render in the mobile app.

1. Extend ConditionEvaluator with `and`, `or`, `contains`, `in`, `not_in`.
2. Flutter: relation picker widget.
3. Flutter: inline sub-entity editor widget.
4. Flutter: report renderer (table + summary cards).
5. Test: flow with `and`/`or` conditions. Report page renders monthly revenue.

**Deliverable**: Full metadata-driven app experience with relations, sub-entities, computed fields, and reports.

---

## Critical Decision: Can This Be Done as Extensions of Existing Primitives?

**YES.** Every feature in this design is an extension of an existing primitive:

| Feature | Existing Primitive | Extension |
|---|---|---|
| Relation fields | EntityField already has `ref_entity`, `multiple`, `max_items` | Add `"relation"` to KNOWN_FIELD_TYPES + post-fetch resolver |
| Sub-entities | Entities are already generic CRUD per collection | Add `sub_entity_of` metadata + cascade delete hook |
| Computed fields | Documents are JSON — fields can be added at read time | Add expression evaluator that runs after fetch |
| Reporting | MongoDB already supports `$group` aggregation | Add generic aggregate endpoint that translates metadata → pipeline |
| Pagination | FindRequest already has `limit` | Add `cursor` field |
| Condition logic | ConditionEvaluator already parses expressions | Add `and`/`or` to the parser |

**What is NOT added**:
- No new service.
- No new database.
- No join support in storage-service (expand is post-fetch).
- No transactions (sub-entity operations are individual inserts; cascade is best-effort with audit log).
- No domain logic in storage-service (it remains a generic document store).

**What IS added**:
- ~3 new Rust structs (ComputedField, SubEntityRef, ReportDefinition) in solution-service.
- ~2 new storage models (ExpandSpec, AggregateRequest) in storage-service.
- ~1 new endpoint (`POST /storage/aggregate`).
- ~1 new shared utility (post-fetch expand resolver).
- ~1 new expression evaluator (simple arithmetic for computed fields).
- ~3 new Flutter widgets (relation picker, inline sub-entity editor, report renderer).

The total surface area is small. The architecture remains metadata-driven, domain-agnostic, and polyglot-compatible. The design preserves the invariant that storage-service knows nothing about entities — it only knows about collections, documents, and MongoDB pipelines.
