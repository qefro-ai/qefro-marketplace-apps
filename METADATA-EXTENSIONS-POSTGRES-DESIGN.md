# Metadata Extensions Design — PostgreSQL Revision

> **Status**: Design Proposal — NOT implemented
> **Supersedes**: `METADATA-EXTENSIONS-DESIGN.md` (MongoDB-based)
> **Constraint**: Storage-agnostic runtime. PostgreSQL is the current production implementation.
> **Principle**: Marketplace Apps know nothing about SQL.

---

## 1. Current Actual Storage Architecture

### 1.1 What Exists Today

The storage-service runs a **hybrid** architecture:

| Data | Backend | Tables/Collections |
|---|---|---|
| Entity documents (marketplace apps) | **MongoDB** | Dynamic collections: `{solution}__{entity}` |
| Collection registry (logical→physical mapping) | **PostgreSQL** | `storage_collection_registry` |
| Audit log | **PostgreSQL** | `storage_audit_log` |
| Media assets (binary + metadata) | **PostgreSQL** | `storage_media_assets` |
| Sequence counters (allocate_code) | **MongoDB** | `{solution}__counters` |

### 1.2 MongoDB Entity Storage (Current)

Each metadata-defined entity becomes a MongoDB collection named `{solution_id}__{entity_id}`. Example: `restaurant_pro__orders`.

Every document carries scope fields injected by the service:

```
{
  _id: ObjectId("..."),
  tenant_id: "uuid-string",
  workspace_id: "uuid-string",
  installation_id: "uuid-string",
  solution_id: "restaurant-pro",
  schema_version: 1,
  created_at: ISODate("..."),
  updated_at: ISODate("..."),
  created_by: "actor",
  updated_by: "actor",
  deleted_at: null,
  deleted_by: null,
  ... user fields ...
}
```

### 1.3 MongoDB Limitations Exposed by the Audit

1. **No transactions** — insert/update/delete are individual operations. If parent insert succeeds but child insert fails, there is no rollback.
2. **No real pagination** — only `limit` (default 100, max 500). No cursor, no offset.
3. **No aggregation** — no `$group`, no `$lookup`, no reporting pipeline.
4. **No joins** — relation fields store raw UUIDs with no resolution mechanism.
5. **No field projection** — every query returns all fields.
6. **No referential integrity** — relation fields are unvalidated UUIDs.
7. **Filters are raw MongoDB syntax** — callers pass `{"$gt": ...}` directly. This couples the runtime to MongoDB's query dialect.
8. **IDs are ObjectIds** — not UUIDs. Requires normalization (`normalize_document_ids`) on every response.
9. **Domain leakage** — `service/mod.rs` line 118-123 contains `if req.collection == "orders"` — a domain-specific check in the generic storage layer.

### 1.4 What Must Change

MongoDB must be replaced with PostgreSQL as the entity store. The generic storage API contract (HTTP endpoints, request/response shapes) remains unchanged for callers. Only the internal implementation changes.

---

## 2. PostgreSQL Data Model

### 2.1 Core Entity Table

A single generic table stores ALL metadata-defined entities across ALL solutions:

```sql
CREATE TABLE storage_entities (
    -- Scope isolation (NOT NULL, indexed, always filtered)
    tenant_id       UUID NOT NULL,
    workspace_id    UUID NOT NULL,
    installation_id UUID NOT NULL,
    solution_id     TEXT NOT NULL,
    collection      TEXT NOT NULL,        -- logical entity name: "order", "customer", etc.

    -- Identity
    id              UUID NOT NULL DEFAULT gen_random_uuid(),
    code            TEXT,                 -- human-readable: "ORD-1001", "R-1001"

    -- Generic entity data (all user-defined fields live here)
    data            JSONB NOT NULL DEFAULT '{}',

    -- System metadata
    schema_version  INTEGER NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by      TEXT,
    updated_by      TEXT,
    deleted_at      TIMESTAMPTZ,
    deleted_by      TEXT,

    PRIMARY KEY (tenant_id, id)
);
```

**Why a single table, not per-entity tables:**

1. Metadata-defined entities are dynamic — new entities are added when a solution is installed. Per-entity tables require dynamic DDL (`CREATE TABLE`), which is operationally dangerous.
2. A single table keeps the schema static. No migrations needed when a new Marketplace App is installed.
3. JSONB provides the schema flexibility that MongoDB documents provided.
4. Scope columns (`tenant_id`, `workspace_id`, `installation_id`, `solution_id`, `collection`) provide logical partitioning within the single table.

**Why `PRIMARY KEY (tenant_id, id)`:**

Every query includes `tenant_id` in the WHERE clause (scope isolation). Making it part of the primary key enables efficient partition-localized lookups. This also enables future partitioning by `tenant_id` or `tenant_id, solution_id` if needed.

### 2.2 Supporting Tables

```sql
-- Collection registry (already exists, unchanged)
CREATE TABLE storage_collection_registry (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    solution_id     TEXT NOT NULL,
    logical_name    TEXT NOT NULL,
    physical_name   TEXT NOT NULL UNIQUE,  -- kept for backward compat, now = "solution_id::collection"
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (solution_id, logical_name)
);

-- Sequence counters (replaces MongoDB counters collection)
CREATE TABLE storage_sequences (
    tenant_id       UUID NOT NULL,
    workspace_id    UUID NOT NULL,
    installation_id UUID NOT NULL,
    solution_id     TEXT NOT NULL,
    collection      TEXT NOT NULL,
    field           TEXT NOT NULL DEFAULT 'code',
    prefix          TEXT NOT NULL,
    seed            BIGINT NOT NULL,      -- start - 1
    n               BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (tenant_id, workspace_id, installation_id, solution_id, collection, field)
);

-- Audit log (already exists, unchanged)
-- storage_audit_log ...

-- Media assets (already exists, unchanged)
-- storage_media_assets ...

-- Relation index: tracks which entities reference which other entities
-- Enables cascade delete, reverse lookups, and referential validation
CREATE TABLE storage_relations (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       UUID NOT NULL,
    -- Source: the entity that HAS the relation field
    source_collection   TEXT NOT NULL,
    source_id           UUID NOT NULL,
    source_field        TEXT NOT NULL,      -- field name: "customer", "order", etc.
    -- Target: the entity being referenced
    target_collection   TEXT NOT NULL,
    target_id           UUID NOT NULL,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (source_collection, source_id, source_field, target_id)
);
```

### 2.3 Indexes

```sql
-- Scope + collection (every query hits this)
CREATE INDEX idx_entities_scope_collection
    ON storage_entities (tenant_id, workspace_id, installation_id, solution_id, collection);

-- Scope + collection + code (for human-readable ID lookup)
CREATE INDEX idx_entities_code
    ON storage_entities (tenant_id, solution_id, collection, code)
    WHERE code IS NOT NULL;

-- Scope + collection + deleted_at (for soft-delete filtering)
CREATE INDEX idx_entities_active
    ON storage_entities (tenant_id, workspace_id, installation_id, solution_id, collection)
    WHERE deleted_at IS NULL;

-- Scope + collection + created_at (default sort)
CREATE INDEX idx_entities_created
    ON storage_entities (tenant_id, workspace_id, installation_id, solution_id, collection, created_at DESC);

-- Scope + collection + updated_at
CREATE INDEX idx_entities_updated
    ON storage_entities (tenant_id, workspace_id, installation_id, solution_id, collection, updated_at DESC);

-- Relation index lookups
CREATE INDEX idx_relations_source
    ON storage_relations (tenant_id, source_collection, source_id);

CREATE INDEX idx_relations_target
    ON storage_relations (tenant_id, target_collection, target_id);

-- Sequence counters
CREATE INDEX idx_sequences_lookup
    ON storage_sequences (tenant_id, workspace_id, installation_id, solution_id, collection, field);
```

### 2.4 Future Partitioning

When a single table becomes too large (millions of rows across many tenants), partition by `tenant_id`:

```sql
-- Convert to partitioned table (requires table recreation)
CREATE TABLE storage_entities (
    ...
) PARTITION BY HASH (tenant_id) WITH (partitions = 16);
```

Or by range on `created_at` for time-series workloads. The application code does not change — PostgreSQL's query router handles partition pruning automatically when `tenant_id` is in the WHERE clause.

---

## 3. Generic Entity Representation

### 3.1 How a Metadata-Defined Entity Becomes a Row

Given this metadata:

```yaml
# entities/order.yaml
id: order
fields:
  - name: customer
    type: relation
    ref_entity: customer
    required: true
  - name: status
    type: enum
    enum_values: [draft, pending, confirmed, completed, cancelled]
  - name: order_date
    type: date
  - name: notes
    type: string
```

When a caller inserts:

```json
{
  "collection": "order",
  "document": {
    "customer": "uuid-of-customer",
    "status": "pending",
    "order_date": "2026-09-09",
    "notes": "Rush delivery"
  },
  "allocate_code": { "prefix": "ORD", "field": "code" }
}
```

The resulting row:

```
tenant_id:       '...'
workspace_id:    '...'
installation_id: '...'
solution_id:     'restaurant-pro'
collection:      'order'
id:              gen_random_uuid()
code:            'ORD-1001'
data:            '{"customer": "uuid-of-customer", "status": "pending", "order_date": "2026-09-09", "notes": "Rush delivery"}'
schema_version:  1
created_at:      NOW()
updated_at:      NOW()
created_by:      'actor'
deleted_at:      NULL
```

### 3.2 Response Normalization

The response flattens system fields and data fields into a single JSON object (same shape as the current MongoDB response):

```json
{
  "id": "uuid",
  "code": "ORD-1001",
  "tenant_id": "...",
  "workspace_id": "...",
  "installation_id": "...",
  "solution_id": "restaurant-pro",
  "collection": "order",
  "customer": "uuid-of-customer",
  "status": "pending",
  "order_date": "2026-09-09",
  "notes": "Rush delivery",
  "created_at": "2026-09-09T10:00:00Z",
  "updated_at": "2026-09-09T10:00:00Z"
}
```

The storage service merges `data` fields with system fields on read, and strips system fields on write. Callers see a flat JSON object — identical to the current MongoDB behavior.

### 3.3 Reserved Keys

Same as current: `_id`, `tenant_id`, `workspace_id`, `installation_id`, `solution_id`, `schema_version`, `created_at`, `updated_at`, `created_by`, `updated_by`, `deleted_at`, `deleted_by`. These are stripped from user input before storing in `data`.

Additionally: `id`, `code`, `collection` are reserved (they map to dedicated columns).

---

## 4. Relationship Model

### 4.1 Storage Representation

Relation fields are stored as UUID values inside the `data` JSONB column:

```json
{ "customer": "550e8400-e29b-41d4-a716-446655440000" }
```

For `multiple: true` relations (array of references):

```json
{ "tags": ["uuid-1", "uuid-2", "uuid-3"] }
```

No SQL-level FOREIGN KEY is used. Rationale:

1. Relation targets are inside JSONB — PostgreSQL cannot enforce FK constraints on JSONB values without extracted columns.
2. Extracting every possible relation field into dedicated columns would require dynamic DDL per solution — violating the generic model.
3. Cross-solution references may be valid in future (e.g., shared customer entity). SQL FKs cannot cross solution boundaries within a single table.
4. Application-level validation provides more flexibility (e.g., soft-deleted targets, conditional validation).

### 4.2 Relation Index

When a row is inserted or updated with relation fields, the storage service maintains the `storage_relations` table:

```
source_collection: 'order'
source_id:         uuid-of-order
source_field:      'customer'
target_collection: 'customer'
target_id:         uuid-of-customer
```

This index enables:
- **Referential validation**: Before insert/update, check that target exists.
- **Cascade delete**: When a customer is deleted, find all orders referencing it.
- **Reverse lookups**: "Find all orders for customer X" → query `storage_relations` where `target_id = X AND target_collection = 'order'`.
- **Expand/resolution**: Batch-fetch related entities.

### 4.3 Self-Reference

Employee → Manager is stored the same way:

```json
{ "manager": "uuid-of-manager-employee" }
```

In `storage_relations`:

```
source_collection: 'employee'
source_id:         uuid-of-employee
source_field:      'manager'
target_collection: 'employee'       -- same collection
target_id:         uuid-of-manager
```

No special handling needed. The relation model is collection-agnostic.

### 4.4 Why Not SQL Foreign Keys

| Concern | SQL FK | Application-Level |
|---|---|---|
| Dynamic relation definitions | Requires DDL per relation | Metadata-driven, no DDL |
| Cross-solution references | Impossible with single-table FK | Supported |
| Soft-delete handling | FK prevents delete entirely | Can implement cascade soft-delete |
| Performance | DB-enforced, fast | Requires query, but relation index is fast |
| Schema stability | New relation = new FK = migration | New relation = metadata change only |

**Verdict**: Application-level with relation index. The `storage_relations` table provides near-FK performance for lookups while maintaining the generic, metadata-driven model.

---

## 5. Parent/Child Model (Sub-Entities)

### 5.1 Re-Evaluation: Is `sub_entity_of` Necessary?

The task asks to compare:

**Option A: Explicit `sub_entity_of` primitive**

```yaml
# order_line.yaml
sub_entity_of: order
parent_field: order
```

**Option B: Normal relation + UI hint**

```yaml
# order_line.yaml
fields:
  - name: order
    type: relation
    ref_entity: order
    required: true
```

### 5.2 Analysis

Option B (normal relation) can express everything Option A expresses at the storage level:

| Capability | Option A (sub_entity_of) | Option B (normal relation) |
|---|---|---|
| Store child with parent reference | `order` field stores parent UUID | `order` field stores parent UUID |
| Query children of parent | `WHERE data->>'order' = parent_id` | `WHERE data->>'order' = parent_id` |
| Cascade delete | Runtime reads `sub_entity_of` metadata | Runtime reads `parent_entity` UI hint |
| Inline UI display | `sub_entities: [{entity: order_line, inline: true}]` | `sub_entities: [{entity: order_line, inline: true}]` |
| Expand children with parent | Same batch query | Same batch query |

The storage representation is **identical**. The only difference is metadata labeling.

### 5.3 Decision: Use Normal Relations + Lightweight UI Hint

`sub_entity_of` is **NOT** a storage primitive. It is a **metadata annotation** that provides UI and runtime hints:

```yaml
# order_line.yaml
id: order_line
name: Order Line

fields:
  - name: order
    type: relation
    ref_entity: order
    required: true

# Metadata annotation (not a storage primitive):
ui:
  parent_entity: order        # hint: this is a child of order
  inline: true                # hint: show inline in parent detail view
  label: "Line Items"         # hint: display label
```

The parent declares:

```yaml
# order.yaml
sub_entities:
  - entity: order_line
    field: order              # which field on order_line points back
    inline: true
    label: "Line Items"
```

### 5.4 What the Runtime Does With This

The `sub_entities` declaration on the parent entity tells the runtime:

1. **Cascade delete**: When an order is deleted, find all `order_line` entities where `order = <deleted_order_id>` and soft-delete them too.
2. **Auto-expand**: When an order is fetched, automatically fetch its order_lines and include them in the response.
3. **UI rendering**: Show order_lines inline in the order detail view.

None of this requires a storage-level primitive. It is all driven by metadata annotations processed by the runtime layer (ai-customer-support or solution-service).

### 5.5 Why This Is Better

1. **Fewer primitives**: A relation is a relation. Parent/child is just a relation with UI hints.
2. **Composable**: The same `order_line` entity can be a child of `order` AND reference `product` — both are just relations.
3. **No special storage logic**: The storage service treats order_line exactly like any other entity.
4. **Metadata-driven**: Adding a new sub-entity type requires only a YAML change, not a storage migration.

---

## 6. Transaction Model

### 6.1 The Problem

Current MongoDB implementation has no transactions. Creating an order with line items requires:

```
1. INSERT order          → succeeds
2. INSERT order_line 1   → succeeds
3. INSERT order_line 2   → FAILS (e.g., validation error)
```

Result: orphaned order with only 1 of 2 line items. No rollback.

### 6.2 PostgreSQL Solution: Batch Insert Endpoint

New endpoint: `POST /v1/internal/storage/batch`

```json
{
  "context": { "tenant_id": "...", "workspace_id": "...", "installation_id": "...", "solution_id": "..." },
  "operations": [
    {
      "op": "insert",
      "collection": "order",
      "document": { "customer": "uuid", "status": "pending", "order_date": "2026-09-09" },
      "allocate_code": { "prefix": "ORD" }
    },
    {
      "op": "insert",
      "collection": "order_line",
      "document": { "order": "$ref:0.id", "product": "Widget A", "quantity": 10, "unit_price": 25.00 }
    },
    {
      "op": "insert",
      "collection": "order_line",
      "document": { "order": "$ref:0.id", "product": "Widget B", "quantity": 5, "unit_price": 40.00 }
    }
  ]
}
```

The `$ref:0.id` syntax references the `id` field from the result of operation 0 (the inserted order). This allows child operations to reference the parent's generated UUID without knowing it in advance.

**Implementation**:

```rust
pub async fn batch(&self, req: BatchRequest) -> StorageResult<BatchResponse> {
    let mut tx = self.pool.begin().await?;
    let mut results = Vec::new();

    for operation in &req.operations {
        match operation.op {
            "insert" => {
                // Resolve $ref references from previous results
                let resolved = resolve_refs(&operation.document, &results)?;
                let row = self.insert_in_tx(&mut *tx, &req.context, &operation.collection, resolved, operation.allocate_code.as_ref()).await?;
                results.push(row);
            }
            "update" => {
                let resolved = resolve_refs(&operation.patch, &results)?;
                let row = self.update_in_tx(&mut *tx, &req.context, &operation.collection, &operation.id, resolved).await?;
                results.push(row);
            }
            "delete" => {
                self.delete_in_tx(&mut *tx, &req.context, &operation.collection, &operation.id).await?;
                results.push(Value::Null);
            }
            _ => return Err(StorageError::Validation(format!("unknown op: {}", operation.op))),
        }
    }

    tx.commit().await?;
    Ok(BatchResponse { results })
}
```

If any operation fails, the entire transaction is rolled back. No partial state.

### 6.3 Transaction Boundaries

Transactions are scoped to a single batch request. There is no distributed transaction across services. The storage service wraps all operations in a single PostgreSQL transaction (`BEGIN` → operations → `COMMIT` or `ROLLBACK`).

The runtime layer (ai-customer-support) can also use the batch endpoint for multi-step flows that need atomicity.

### 6.4 Why Not Expose BEGIN/COMMIT/ROLLBACK

Explicit transaction primitives (`POST /storage/begin`, `POST /storage/commit`, `POST /storage/rollback`) require:

1. Server-side transaction state management (transaction IDs, timeouts, cleanup).
2. Handling of abandoned transactions (client crashes mid-transaction).
3. Connection pinning (a transaction must use the same DB connection throughout).

The batch endpoint covers the primary use case (create parent + children atomically) without these complications. If more flexibility is needed later, it can be added as a Phase 2 enhancement.

---

## 7. Referential Integrity Model

### 7.1 Strategy: Hybrid (Storage-Service Validation)

| Layer | Responsibility |
|---|---|
| **Storage service** | Validates that relation targets exist within the same scope. Maintains `storage_relations` index. |
| **Runtime (ai-customer-support)** | Validates business rules (e.g., "customer must be active"). Strips authority overrides. |
| **PostgreSQL** | Enforces scope isolation via NOT NULL constraints and indexes. No FK constraints on JSONB data. |

### 7.2 Validation Flow

On insert/update of an entity with relation fields:

1. **Parse metadata**: The solution-service provides the entity definition, including which fields are `type: relation` and their `ref_entity`.
2. **Extract relation values**: For each relation field, extract the UUID (or UUIDs if `multiple: true`) from the document.
3. **Scope-check targets**: Query `storage_entities` to verify each target exists:
   ```sql
   SELECT id FROM storage_entities
   WHERE tenant_id = $1 AND id = ANY($2) AND collection = $3 AND deleted_at IS NULL
   ```
4. **Scope isolation**: The query automatically enforces tenant isolation — a target in a different tenant cannot be found because `tenant_id` is always filtered.
5. **Write relation index**: Insert rows into `storage_relations` for each relation.

### 7.3 Cross-Scope Prevention

The validation query always includes `tenant_id`, `workspace_id`, and `installation_id` in the WHERE clause. This makes it impossible for:

- Tenant A to reference Tenant B's entities (different `tenant_id`).
- Workspace A to reference Workspace B's entities (different `workspace_id`).
- Installation A to reference Installation B's entities (different `installation_id`).

### 7.4 Soft-Delete Behavior

When a referenced entity is soft-deleted:

1. The relation index row is NOT deleted (it records the historical relationship).
2. The relation field in the referencing entity still contains the UUID.
3. On expand/resolution, the storage service checks `deleted_at IS NULL` on the target. If the target is soft-deleted, the relation resolves to `null` (or is flagged as deleted in the response).

This prevents dangling references while preserving audit history.

### 7.5 Cascade Delete

When an entity is deleted and it has `sub_entities` declared:

1. The runtime queries `storage_relations` for all entities that reference the deleted entity:
   ```sql
   SELECT source_collection, source_id FROM storage_relations
   WHERE tenant_id = $1 AND target_collection = $2 AND target_id = $3
   ```
2. For each relation where the source is a declared sub-entity, soft-delete the source.
3. Cascade is recursive: if order_line has sub-entities of its own, they cascade too.
4. All cascaded deletes happen within a single transaction.

---

## 8. Query Model

### 8.1 Generic Filter Translation

The current MongoDB implementation passes raw MongoDB query syntax from callers. This must change — PostgreSQL uses SQL, not MongoDB queries.

**New approach**: Callers pass a **storage-agnostic filter grammar** that the storage service translates to SQL.

```json
{
  "filter": {
    "and": [
      { "field": "status", "op": "==", "value": "completed" },
      { "field": "total", "op": ">=", "value": 1000 },
      { "or": [
        { "field": "customer", "op": "==", "value": "uuid-1" },
        { "field": "customer", "op": "==", "value": "uuid-2" }
      ]}
    ]
  }
}
```

**Translation to SQL**:

```sql
WHERE tenant_id = $1 AND workspace_id = $2 AND installation_id = $3
  AND solution_id = $4 AND collection = $5
  AND deleted_at IS NULL
  AND data->>'status' = 'completed'
  AND (data->>'total')::NUMERIC >= 1000
  AND (data->>'customer' = 'uuid-1' OR data->>'customer' = 'uuid-2')
```

### 8.2 Filter Grammar

```
filter := { "and": [filter, ...] }
        | { "or": [filter, ...] }
        | { "not": filter }
        | { "field": "...", "op": "...", "value": ... }
        | { "field": "...", "op": "in", "value": [...] }
        | { "field": "...", "op": "not_in", "value": [...] }
        | { "field": "...", "op": "contains", "value": "..." }
        | { "field": "...", "op": "exists", "value": true }
        | { "field": "...", "op": "empty", "value": true }

op := "==" | "!=" | ">" | "<" | ">=" | "<=" | "in" | "not_in" | "contains" | "exists" | "empty" | "between"
```

### 8.3 JSONB Field Access

For a field `f` inside the `data` JSONB column:

| Filter op | SQL translation |
|---|---|
| `==` | `data->>'f' = $value` |
| `!=` | `data->>'f' != $value` |
| `>`, `<`, `>=`, `<=` | `(data->>'f')::NUMERIC > $value` (for numeric fields) |
| `contains` | `data->>'f' ILIKE '%' \|\| $value \|\| '%'` |
| `in` | `data->>'f' = ANY($values)` |
| `exists` | `data ? 'f'` |
| `empty` | `data->>'f' IS NULL OR data->>'f' = ''` |
| `between` | `(data->>'f')::NUMERIC BETWEEN $low AND $high` |

**Type casting**: The storage service determines the cast based on the value type in the filter. If the filter value is a number, cast to `NUMERIC`. If it's a string, compare as text. If it's a boolean, cast to `BOOLEAN`.

### 8.4 Backward Compatibility for Filters

The current MongoDB filter syntax (`{"status": "confirmed"}`) is a simple key-value equality. The new grammar supports this as a shorthand:

```json
// Old (MongoDB-style, still supported as shorthand):
{ "status": "confirmed" }

// Equivalent in new grammar:
{ "and": [
  { "field": "status", "op": "==", "value": "confirmed" }
]}
```

The storage service detects simple key-value objects and translates them to the new grammar internally. This avoids breaking existing callers during migration.

MongoDB-specific operators (`$gt`, `$lt`, `$in`, `$or`, etc.) are NOT supported in the new API. They are translated if possible (e.g., `$gt` → `>`), or rejected with a clear error message.

---

## 9. Pagination Model

### 9.1 Keyset Cursor Pagination

Offset-based pagination is inefficient for large tables (requires scanning and discarding rows). Keyset (seek) pagination uses the sort key values as a cursor.

**Request**:

```json
{
  "collection": "order",
  "filter": { "status": "completed" },
  "sort": [{ "field": "created_at", "order": "desc" }],
  "page_size": 20,
  "cursor": "eyJjcmVhdGVkX2F0IjoiMjAyNi0wOS0wOVQxMDowMDowMFoiLCJpZCI6InV1aWQifQ=="
}
```

**Cursor encoding**: Base64-encoded JSON of the last item's sort key values:

```json
{ "created_at": "2026-09-09T10:00:00Z", "id": "uuid" }
```

The `id` is always included as a tiebreaker to ensure deterministic ordering.

**SQL translation**:

```sql
WHERE tenant_id = $1 AND ... AND deleted_at IS NULL
  AND (created_at, id) < ($cursor_created_at, $cursor_id)
ORDER BY created_at DESC, id DESC
LIMIT 20
```

**Response**:

```json
{
  "items": [...],
  "page_size": 20,
  "next_cursor": "eyJjcmVhdGVkX2F0IjoiMjAyNi0wOS0wOFQxMDowMDowMFoiLCJpZCI6InV1aWQyIn0=",
  "has_more": true
}
```

`next_cursor` is `null` when there are no more pages.

### 9.2 Deterministic Ordering

Every paginated query must have a deterministic sort. If the caller does not specify a sort, the default is `created_at DESC, id DESC`. The `id` tiebreaker ensures that rows with identical `created_at` values are still ordered deterministically.

### 9.3 Storage-Agnostic API

The cursor is an opaque base64 string. Callers do not see PostgreSQL internals. The storage service decodes the cursor, extracts the sort key values, and constructs the appropriate WHERE clause. If the backend were switched to another database, the cursor format would remain the same.

---

## 10. Aggregation Model

### 10.1 Generic Aggregate Endpoint

`POST /v1/internal/storage/aggregate`

```json
{
  "context": { "..." : "..." },
  "collection": "order",
  "filter": { "field": "status", "op": "!=", "value": "cancelled" },
  "group_by": [
    { "field": "order_date", "granularity": "month" }
  ],
  "metrics": [
    { "field": "total", "aggregate": "sum", "label": "Revenue" },
    { "field": "id", "aggregate": "count", "label": "Order Count" }
  ],
  "sort": [
    { "field": "order_date", "order": "desc" }
  ],
  "limit": 12
}
```

### 10.2 SQL Translation

```sql
SELECT
    DATE_TRUNC('month', (data->>'order_date')::DATE) AS group_order_date,
    SUM((data->>'total')::NUMERIC) AS metric_sum_total,
    COUNT(*) AS metric_count_id
FROM storage_entities
WHERE tenant_id = $1 AND workspace_id = $2 AND installation_id = $3
  AND solution_id = $4 AND collection = 'order'
  AND deleted_at IS NULL
  AND data->>'status' != 'cancelled'
GROUP BY DATE_TRUNC('month', (data->>'order_date')::DATE)
ORDER BY group_order_date DESC
LIMIT 12
```

### 10.3 Supported Aggregations

| Aggregate | SQL | Notes |
|---|---|---|
| `count` | `COUNT(*)` | Counts rows |
| `sum` | `SUM((data->>'field')::NUMERIC)` | Numeric only |
| `avg` | `AVG((data->>'field')::NUMERIC)` | Numeric only |
| `min` | `MIN((data->>'field')::NUMERIC)` | Numeric or date |
| `max` | `MAX((data->>'field')::NUMERIC)` | Numeric or date |

### 10.4 Group-By Granularity

| Granularity | SQL |
|---|---|
| (none) | No GROUP BY — single aggregate across all matching rows |
| `day` | `DATE_TRUNC('day', (data->>'field')::DATE)` |
| `week` | `DATE_TRUNC('week', (data->>'field')::DATE)` |
| `month` | `DATE_TRUNC('month', (data->>'field')::DATE)` |
| `quarter` | `DATE_TRUNC('quarter', (data->>'field')::DATE)` |
| `year` | `DATE_TRUNC('year', (data->>'field')::DATE)` |
| raw | `data->>'field'` — group by exact value (e.g., department, status) |

### 10.5 Response

```json
{
  "groups": [
    {
      "key": { "order_date": "2026-09-01" },
      "metrics": { "Revenue": 125000.00, "Order Count": 42 }
    },
    {
      "key": { "order_date": "2026-08-01" },
      "metrics": { "Revenue": 98000.00, "Order Count": 35 }
    }
  ],
  "total_groups": 2
}
```

### 10.6 Safety

- No raw SQL is accepted from callers. All queries are constructed by the storage service from the generic request.
- JSONB field access uses `->>` (text extraction) with explicit casts. No arbitrary SQL injection is possible.
- Scope isolation is always enforced — the WHERE clause always starts with tenant/workspace/installation/solution filters.
- `LIMIT` is always applied (default 100, max 1000).

---

## 11. Computed Field Model

### 11.1 Principle: Computed at Read Time

Computed fields are NEVER stored in PostgreSQL. They are calculated by the runtime layer after fetching raw data from storage.

This keeps the storage service completely unaware of computation logic. The storage service returns raw entity data; the runtime applies computed field expressions.

### 11.2 Expression Evaluator

A restricted expression evaluator (in the runtime layer, NOT in storage-service):

**Supported operations**:
- Arithmetic: `+`, `-`, `*`, `/`, parentheses
- Field references: `quantity`, `unit_price`, `order_line.quantity`
- Numeric literals: `0.14`, `100`
- String functions: `concat(a, b)`
- Comparison (for conditional expressions): `if cond then a else b`

**NOT supported**:
- SQL expressions
- Arbitrary code execution (JavaScript, Python, Lua)
- Database queries
- Side effects

### 11.3 Two Categories

**Category A: Own-field computation**

```yaml
computed:
  expr: "quantity * unit_price"
  depends_on: [quantity, unit_price]
```

Evaluated against the entity's own `data` fields after fetch.

**Category B: Sub-entity aggregation**

```yaml
computed:
  expr: "quantity * unit_price"
  aggregate: sum
  source: order_line
```

Evaluated by:
1. Fetching all sub-entities (order_lines for this order).
2. Evaluating `expr` for each child.
3. Applying `aggregate` (sum) to the results.

### 11.4 Financial Precision

**Do NOT use `f64` for financial calculations.**

The expression evaluator uses `rust_decimal::Decimal` (or equivalent) for all numeric operations. This provides exact decimal arithmetic without floating-point rounding errors.

PostgreSQL stores numeric values in JSONB as strings when they require decimal precision:

```json
{ "total": "1250.50" }
```

The runtime parses these as `Decimal`, not `f64`. The metadata declares which fields are financial:

```yaml
- name: total
  type: float
  precision: decimal    # ← signals the runtime to use Decimal, not f64
```

When the storage service performs aggregation (SUM, AVG), it uses `NUMERIC` casts in SQL, which maps to PostgreSQL's arbitrary-precision decimal type. The result is returned as a string in JSON to preserve precision.

---

## 12. FlowRunner Integration

### 12.1 Existing Capabilities (Unchanged)

```
entity.{name}.create
entity.{name}.list
entity.{name}.get
entity.{name}.update
entity.{name}.delete
```

These work identically. The runtime translates them to storage-service HTTP calls. The storage service handles the PostgreSQL implementation.

### 12.2 Relation-Aware Tool Parameters

When a flow creates an entity with a relation field:

```yaml
- id: create_order
  type: tool
  tool: entity.order.create
  params:
    data:
      customer: "{{ customer_results[0].id }}"
      status: pending
```

The runtime passes `customer: "uuid"` in the document. The storage service validates that the customer UUID exists (referential integrity) and stores it in the `data` JSONB column.

### 12.3 Batch Tool for Atomic Parent+Children

New tool: `entity.batch` (or extend existing tools with batch capability):

```yaml
- id: create_order_with_lines
  type: tool
  tool: storage.batch
  params:
    operations:
      - op: insert
        collection: order
        data:
          customer: "{{ customer.id }}"
          status: pending
        allocate_code: { prefix: "ORD" }
      - op: insert
        collection: order_line
        data:
          order: "$ref:0.id"
          product: Widget A
          quantity: 10
          unit_price: 25.00
      - op: insert
        collection: order_line
        data:
          order: "$ref:0.id"
          product: Widget B
          quantity: 5
          unit_price: 40.00
```

This calls `POST /v1/internal/storage/batch` and executes atomically.

### 12.4 No Domain-Specific Flow Steps

There is no `order.create_with_lines` or `invoice.create_with_lines`. The batch tool is generic — it works for any entity combination. The flow author specifies the operations; the runtime executes them atomically.

### 12.5 Expand in Tool Results

When a flow calls `entity.order.get`, the result includes expanded relations and sub-entities:

```json
{
  "id": "uuid",
  "code": "ORD-1001",
  "customer": { "id": "uuid", "name": "Acme Corp", "email": "orders@acme.com" },
  "status": "pending",
  "order_lines": [
    { "id": "uuid1", "product": "Widget A", "quantity": 10, "unit_price": 25.00, "line_total": 250.00 },
    { "id": "uuid2", "product": "Widget B", "quantity": 5, "unit_price": 40.00, "line_total": 200.00 }
  ],
  "subtotal": 450.00,
  "tax": 63.00,
  "total": 513.00
}
```

The `customer` is expanded from a UUID to the full customer object. The `order_lines` are fetched and included inline. Computed fields (`line_total`, `subtotal`, `tax`, `total`) are calculated by the runtime.

---

## 13. Flutter Integration

### 13.1 Metadata-Driven (No Domain-Specific Screens)

All UI is rendered from metadata. No `OrderDetailScreen`, `InvoiceDetailScreen`, etc.

### 13.2 New/Updated Widgets

| Widget | Purpose | Metadata Trigger |
|---|---|---|
| Relation picker | Dropdown/search for selecting a related entity | `type: relation` field in form |
| Relation display | Shows related entity's display field, tappable to navigate | `type: relation` field in detail view |
| Inline sub-entity editor | Add/remove/edit child rows within parent form | `sub_entities` declaration with `inline: true` |
| Sub-entity list | Shows child entities in a table/list within parent detail | `sub_entities` declaration |
| Computed field display | Read-only display of computed value | `computed` field definition |
| Paginated list | List with "Load more" / infinite scroll using cursor | Any entity list view |
| Report view | Summary cards / grouped table from aggregate data | Report metadata |

### 13.3 Field Type Mapping

```dart
// ui_bundle_mapper.dart
switch (fieldType) {
  case 'relation':
    return FieldType.relation;
  case 'computed':
    return FieldType.computed;  // read-only
  // ... existing types unchanged
}
```

### 13.4 Relation Picker

The relation picker queries the related entity's list endpoint:

```
GET /v1/internal/storage/find
  collection: customer
  filter: { name: { contains: "Acme" } }
  page_size: 20
```

Results are displayed in a searchable dropdown. The selected entity's UUID is stored in the relation field.

### 13.5 Pagination

Entity list views use cursor-based pagination. The list view:

1. Fetches the first page (no cursor).
2. Displays items.
3. On scroll to bottom, fetches next page using `next_cursor`.
4. Appends new items to the list.
5. Repeats until `has_more` is false.

---

## 14. Agent Integration

### 14.1 Zero Agent-Specific Changes

The Agent benefits from the new capabilities automatically through existing generic tools.

**"Show me orders for Acme"**:

1. Agent calls `entity.customer.list` with filter `{ name: { contains: "Acme" } }`.
2. Gets customer UUID.
3. Calls `entity.order.list` with filter `{ customer: customer_uuid }`.
4. Results include expanded customer name and computed totals.

**"Add another item to my order"**:

1. Agent resolves "my order" from ConversationState entity mentions.
2. Calls `entity.order_line.create` with `{ order: order_uuid, product: "...", quantity: N, unit_price: N }`.
3. Storage service validates the order exists (referential integrity).
4. Computed `total` on the order is recalculated on next read.

### 14.2 ConversationState

Existing `EntityMention` tracking works unchanged. Sub-entity mentions are tracked as separate entity mentions. The Agent can resolve "add a line to the last order" because the order is already in the entity mention history.

### 14.3 Tool Result Formatting

When tool results include expanded relations, the Agent sees human-readable data:

```json
{ "customer": { "name": "Acme Corp" } }
```

Not:

```json
{ "customer": "550e8400-e29b-41d4-a716-446655440000" }
```

This happens automatically because the runtime expands relations before returning tool results to the Agent.

---

## 15. Event Semantics

### 15.1 Existing Events (Sufficient)

```
entity.order.created
entity.order.updated
entity.order.deleted
entity.order_line.created
entity.order_line.updated
entity.order_line.deleted
```

These are sufficient. No new event types are needed for relationships.

### 15.2 Why No `entity.relation.changed`

A relation change is just a field update. When `order.customer` changes from UUID-A to UUID-B, the event is:

```
entity.order.updated
```

With the payload containing both old and new values. Flows that need to react to relation changes can use the existing condition evaluator:

```yaml
trigger:
  event: entity.order.updated
  filter: "customer changed"    # CRM-style change detection
```

This is already supported by the CRM automation evaluator (which has `changed` operator). Extending the flow engine's ConditionEvaluator to include `changed` (as proposed in the previous design) is sufficient.

### 15.3 Cascade Delete Events

When a parent is deleted and children cascade-delete, each child deletion emits its own `entity.{child}.deleted` event. This allows flows to react to individual child deletions.

### 15.4 Batch Operation Events

A batch insert (order + order_lines) emits individual events for each created entity:

```
entity.order.created       (order)
entity.order_line.created  (line 1)
entity.order_line.created  (line 2)
```

Events are emitted after the transaction commits, so they only fire for successfully committed operations.

---

## 16. Security Model

### 16.1 Scope Isolation (PostgreSQL-Level)

Every SQL query includes scope columns in the WHERE clause:

```sql
WHERE tenant_id = $1 AND workspace_id = $2 AND installation_id = $3 AND solution_id = $4
```

This is enforced at the storage service level — not by the caller. The `StorageContext` is injected by the runtime (ai-customer-support) and cannot be forged by the caller because:

1. The runtime extracts scope from the authenticated session.
2. The storage service validates the scope against the service-to-service auth token.
3. Reserved keys are stripped from user input.

### 16.2 Capability Enforcement

Unchanged from current model:

```
storage.read    → find, get, aggregate
storage.write   → insert, batch
storage.update  → update
storage.delete  → delete
```

Entity-level capabilities (`entity.order.create`, etc.) are enforced by the runtime layer, not the storage service.

### 16.3 Relation Authorization

When creating/updating a relation field:

1. The runtime checks that the caller has `entity.{ref_entity}.get` capability (you can only reference entities you can read).
2. The storage service validates that the target exists within the same scope.
3. The FORBIDDEN_AUTHORITY_KEYS list prevents authority injection.

### 16.4 Aggregate Authorization

Aggregate queries require `storage.read` (or `entity.{name}.list`) capability. The scope filter is always applied — users can only aggregate over entities they can see.

---

## 17. Backward Compatibility

### 17.1 API Contract

The HTTP API contract is preserved:

| Endpoint | Change |
|---|---|
| `POST /v1/internal/storage/insert` | Unchanged |
| `POST /v1/internal/storage/find` | Gains optional `cursor`, `page_size`, `expand` fields |
| `POST /v1/internal/storage/get` | Gains optional `expand` field |
| `POST /v1/internal/storage/update` | Unchanged |
| `POST /v1/internal/storage/delete` | Unchanged |
| `POST /v1/internal/storage/batch` | **NEW** |
| `POST /v1/internal/storage/aggregate` | **NEW** |

### 17.2 Filter Syntax Migration

Old MongoDB-style filters (`{"status": "confirmed"}`) are auto-translated to the new grammar. MongoDB-specific operators (`$gt`, `$lt`, `$in`) are translated where possible or rejected with clear errors.

### 17.3 Response Shape

Responses maintain the same flat JSON shape. The `id` field is now a UUID string (was an ObjectId hex string). Callers that treat IDs as opaque strings are unaffected.

### 17.4 Code Allocation

The `allocate_code` mechanism is preserved. The sequence counter moves from MongoDB to the `storage_sequences` PostgreSQL table. The atomic increment uses `INSERT ... ON CONFLICT ... DO UPDATE` with `RETURNING`.

---

## 18. Migration Strategy

### 18.1 Phase 0: Add PostgreSQL Entity Schema

Add the new tables (`storage_entities`, `storage_sequences`, `storage_relations`) via a new migration (`003_entities.sql`). The existing MongoDB entity store continues to operate.

### 18.2 Phase 1: Dual-Write

The storage service writes to BOTH MongoDB and PostgreSQL for every insert/update/delete. Reads still come from MongoDB. This validates that PostgreSQL writes work correctly without affecting production behavior.

### 18.3 Phase 2: Data Migration

A migration tool reads all MongoDB documents and inserts them into PostgreSQL:

```
For each collection in storage_collection_registry:
  For each document in MongoDB collection:
    Extract scope fields, user data, system metadata
    Insert into storage_entities
    Rebuild storage_relations index
```

This can run offline (maintenance window) or online (with change-data-capture for consistency).

### 18.4 Phase 3: Switch Reads

The storage service switches reads from MongoDB to PostgreSQL. MongoDB writes continue as a safety net.

### 18.5 Phase 4: Remove MongoDB

After validation, remove MongoDB writes. Remove the MongoDB driver dependency. Remove the MongoDB connection configuration.

### 18.6 What Assumes MongoDB and Must Be Removed

| MongoDB Assumption | Location | Replacement |
|---|---|---|
| Raw MongoDB query syntax in filters | `service/mod.rs` lines 182-197 | Generic filter grammar → SQL |
| ObjectId as entity ID | `repositories/mongo.rs` lines 46-55, 281-309 | UUID (`gen_random_uuid()`) |
| BSON document manipulation | Throughout `service/mod.rs` | JSONB via `serde_json::Value` |
| MongoDB extended JSON normalization | `repositories/mongo.rs` lines 205-279 | Not needed (PostgreSQL returns standard JSON) |
| MongoDB `find_one_and_update` for sequences | `repositories/mongo.rs` lines 115-162 | `INSERT ... ON CONFLICT DO UPDATE RETURNING` |
| MongoDB collection-per-entity | `collections.rs` lines 41-45 | Single `storage_entities` table with `collection` column |
| MongoDB background index creation | `indexes.rs` lines 10-37 | PostgreSQL `CREATE INDEX` in migration |
| `if req.collection == "orders"` domain leak | `service/mod.rs` lines 118-123 | Remove — was a hack for `order_number` sync |
| `Bson::Null` for deleted_at | Throughout | SQL `NULL` (TIMESTAMPTZ NULL) |
| `Bson::DateTime` for timestamps | Throughout | SQL `TIMESTAMPTZ` |

---

## 19. Test Strategy

### 19.1 Unit Tests

**Storage service**:
- Insert entity → row appears in `storage_entities` with correct scope fields.
- Find with filter → correct SQL WHERE clause generated.
- Find with cursor → correct keyset pagination.
- Aggregate → correct GROUP BY pipeline.
- Batch insert → all-or-nothing transaction.
- Batch with `$ref` → references resolved correctly.
- Relation validation → existing target passes, missing target rejected.
- Cross-scope relation → rejected.
- Cascade delete → children soft-deleted in same transaction.
- Sequence counter → atomic increment, correct code generation.

**Runtime (ai-customer-support)**:
- Computed field evaluation → correct arithmetic with Decimal.
- Expand resolution → relations resolved, sub-entities included.
- Batch tool → calls storage batch endpoint correctly.
- Filter translation → generic grammar translated correctly.

**Flutter**:
- Relation picker → queries related entity, stores UUID.
- Inline sub-entity editor → add/remove/edit child rows.
- Paginated list → cursor-based load more.
- Report view → renders aggregate data.

### 19.2 Integration Tests

1. Create Order + 3 OrderLines via batch → verify atomic commit.
2. Create Order + 3 OrderLines, fail on 3rd → verify rollback (no order, no lines).
3. Fetch Order → verify OrderLines expanded inline, computed totals correct.
4. Delete Order → verify OrderLines cascade-deleted.
5. Paginate through 500 orders → verify cursor consistency.
6. Aggregate monthly revenue → verify correct sums.
7. Cross-tenant relation → verify rejection.
8. Agent conversation: "Create an order for Acme with 2 items" → verify full flow.

### 19.3 Migration Tests

1. Insert entities via MongoDB path → migrate to PostgreSQL → verify data matches.
2. Dual-write mode → verify MongoDB and PostgreSQL data are identical.
3. Switch reads → verify no data loss or inconsistency.

---

## 20. Storage Abstraction Boundary

### 20.1 The Boundary

```
Marketplace Metadata (YAML)
        ↓
Solution Service (parse + validate metadata)
        ↓
Qefro Runtime (ai-customer-support: flows, Agent, computed fields, expand)
        ↓
Generic Storage API (HTTP: insert, find, get, update, delete, batch, aggregate)
        ↓
PostgreSQL Implementation (storage_entities, storage_relations, storage_sequences)
```

### 20.2 What Each Layer Knows

| Layer | Knows About | Does NOT Know About |
|---|---|---|
| Metadata | Entity definitions, relations, computed fields, reports | SQL, PostgreSQL, HTTP |
| Solution Service | Metadata validation, package signing | SQL, PostgreSQL |
| Runtime | Flows, Agent, computed fields, expand, conversation | SQL, PostgreSQL, table names |
| Storage API | Collections, documents, filters, pagination, aggregation | SQL, PostgreSQL, table names |
| PostgreSQL Impl | Tables, indexes, transactions, SQL | Orders, invoices, customers, business domains |

### 20.3 What the Storage API Does NOT Expose

- SQL syntax
- Table names
- Column names
- PostgreSQL-specific operators
- Connection details
- Transaction IDs

### 20.4 What the Runtime Does NOT Expose

- Storage API details (endpoints, request shapes)
- MongoDB or PostgreSQL specifics
- Collection names (translates entity names to collection names)
- Scope injection (handled transparently)

---

## 21. Critical Architectural Test

Proving that the SAME runtime/storage implementation supports all five domains WITHOUT domain-specific code:

### 21.1 Real Estate

```yaml
# Property → Agent (relation)
property:
  fields:
    - { name: agent, type: relation, ref_entity: agent }

# Viewing → Property (relation), Viewing → Person (relation)
viewing:
  fields:
    - { name: property, type: relation, ref_entity: property }
    - { name: person, type: relation, ref_entity: person }
```

Storage: 3 entities in `storage_entities` with relation fields in JSONB. `storage_relations` tracks property→agent, viewing→property, viewing→person.

Runtime: No domain code. Generic CRUD, generic expand, generic relation validation.

### 21.2 Restaurant

```yaml
# Order → Customer, Order → OrderLine (sub-entity), OrderLine → Product
order:
  fields:
    - { name: customer, type: relation, ref_entity: customer }
  sub_entities:
    - { entity: order_line, field: order, inline: true }

order_line:
  fields:
    - { name: order, type: relation, ref_entity: order }
    - { name: product, type: relation, ref_entity: product }
  ui:
    parent_entity: order
```

Storage: Same generic table. Relations in JSONB. Batch insert for order + lines.

Runtime: Cascade delete (order → order_lines). Computed total = sum(order_line.line_total). No domain code.

### 21.3 Accounting

```yaml
# Invoice → Customer, Invoice → InvoiceLine, InvoiceLine → Account
invoice:
  fields:
    - { name: customer, type: relation, ref_entity: customer }
  sub_entities:
    - { entity: invoice_line, field: invoice, inline: true }

invoice_line:
  fields:
    - { name: invoice, type: relation, ref_entity: invoice }
    - { name: account, type: relation, ref_entity: account }
```

Identical pattern. No domain code. The storage service does not know "invoice" is financial.

### 21.4 HR

```yaml
# Employee → Manager (self-reference)
employee:
  fields:
    - { name: manager, type: relation, ref_entity: employee }  # self-reference
```

Self-reference works because the relation model is collection-agnostic. `storage_relations` row has `source_collection = target_collection = 'employee'`. No special handling.

### 21.5 School

```yaml
# Student → Class, Student → Parent
student:
  fields:
    - { name: class, type: relation, ref_entity: class }
    - { name: parent, type: relation, ref_entity: parent, multiple: true }
```

Multiple relations (student has multiple parents) stored as JSON array in `data`. `storage_relations` has one row per parent. No domain code.

### 21.6 Verdict

All five domains use the SAME:
- `storage_entities` table
- `storage_relations` index
- Generic filter grammar
- Generic batch/transaction endpoint
- Generic aggregate endpoint
- Generic expand resolution
- Generic cascade delete
- Generic computed field evaluator

**Zero domain-specific code in the runtime or storage service.**

---

## 22. Final Answer

### Is PostgreSQL the correct canonical storage implementation for Qefro metadata-driven Marketplace Apps?

**YES.**

PostgreSQL provides:

1. **Transactions** — `BEGIN`/`COMMIT`/`ROLLBACK` for atomic parent+child operations. MongoDB lacks multi-document transactions in the current deployment (single-node).
2. **Referential integrity** — Application-level validation backed by the `storage_relations` index. Fast, scope-aware, domain-agnostic.
3. **Aggregation** — Native `GROUP BY`, `SUM`, `COUNT`, `DATE_TRUNC` for reporting. No need for a separate analytics system.
4. **Keyset pagination** — Efficient cursor-based pagination using `(sort_key, id)` tuples.
5. **JSONB flexibility** — Schema-less entity data within a structured relational framework. Best of both worlds.
6. **Operational simplicity** — One database engine for all services. No MongoDB + PostgreSQL split.
7. **Decimal precision** — `NUMERIC` type for financial calculations. No floating-point rounding.
8. **Mature ecosystem** — sqlx (Rust), EXPLAIN ANALYZE, pg_stat, partitioning, replication, backup.

### Final Storage Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Marketplace Metadata                    │
│              (YAML: entities, flows, UI, reports)         │
└────────────────────────┬────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│                   Solution Service                        │
│    Parse + validate metadata. Register entity defs.       │
│    Validate relation consistency. No storage logic.       │
└────────────────────────┬────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              Qefro Runtime (ai-customer-support)          │
│  Flows, Agent, computed fields, expand, conversation.     │
│  Translates entity ops → storage API calls.               │
│  Injects scope context. Enforces entity capabilities.     │
└────────────────────────┬────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│               Generic Storage API (HTTP)                  │
│  insert | find | get | update | delete | batch | aggregate│
│  Storage-agnostic filter grammar. Cursor pagination.      │
│  Expand specs. Aggregate requests. Batch operations.      │
└────────────────────────┬────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              PostgreSQL Implementation                    │
│                                                          │
│  storage_entities     — single generic table (JSONB data) │
│  storage_relations    — relation index (source→target)    │
│  storage_sequences    — atomic code counters              │
│  storage_collection_registry — logical→physical mapping   │
│  storage_audit_log    — CRUD audit trail                  │
│  storage_media_assets — binary media storage              │
│                                                          │
│  All queries scoped by tenant_id + workspace_id +         │
│  installation_id + solution_id. Always.                   │
└─────────────────────────────────────────────────────────┘
```

### What Must Be Removed Before Implementation

| MongoDB Artifact | Action |
|---|---|
| `MongoStore` struct and all MongoDB driver code | Replace with `PostgresEntityStore` using sqlx |
| `mongodb` crate dependency in Cargo.toml | Remove |
| `MONGODB_URL`, `MONGODB_DB` config | Remove |
| BSON/JSON conversion utilities | Remove (not needed — PostgreSQL returns JSON directly) |
| `normalize_extended_json()`, `normalize_document_ids()` | Remove (PostgreSQL returns standard JSON) |
| `id_filter()` ObjectId parsing | Replace with UUID + code lookup |
| `json_to_document()` (BSON conversion) | Replace with JSONB filter grammar → SQL |
| MongoDB `find_one_and_update` for sequences | Replace with `INSERT ... ON CONFLICT DO UPDATE RETURNING` |
| MongoDB collection-per-entity naming | Replace with `collection` column in `storage_entities` |
| MongoDB background index creation | Replace with SQL migration `CREATE INDEX` |
| `if req.collection == "orders"` domain leak | Delete entirely |
| `solution-mongodb` from docker-compose | Remove after migration complete |
| MongoDB extended JSON in API responses | Not needed — PostgreSQL returns standard JSON |
