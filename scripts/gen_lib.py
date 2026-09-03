"""Emit Marketplace App YAML using the existing Shopify / Restaurant Pro conventions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
APPS = ROOT / "apps"

FORBIDDEN_CONNECTION_KEYS = {
    "url",
    "base_url",
    "host",
    "hostname",
    "access_token",
    "api_key",
    "apikey",
    "token",
    "secret",
    "password",
    "authorization",
}

IDENTITY_PARAM_KEYS = {
    "email",
    "phone",
    "person_id",
    "customer_id",
    "workspace_id",
    "tenant_id",
    "external_id",
    "external_customer_id",
}

ALLOWED_ICONS = {
    "home",
    "calendar",
    "chef-hat",
    "receipt",
    "users",
    "user",
    "file-text",
    "bar-chart",
    "settings",
    "package",
    "clipboard",
    "credit-card",
    "activity",
    "list",
    "clock",
    "map",
    "stethoscope",
    "wallet",
    "report",
    "workflow",
}

RUNTIME_PERMISSIONS = [
    "workflow.execute",
    "storage.read",
    "storage.write",
    "storage.update",
    "storage.delete",
]

RUNTIME_CAPABILITIES = [
    "theme.get",
    "user.get",
    "tenant.get",
    "runtime.query",
    "workflow.trigger",
    "storage.read",
    "storage.write",
]


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8")


def yaml_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    text = str(value)
    if "\n" in text:
        raise ValueError("multiline strings must use emit_block")
    if text == "":
        return '""'
    if (
        text.startswith("{")
        or text.startswith("/")
        or text.startswith(".")
        or ":" in text
        or "#" in text
        or " " in text
        or text.startswith("*")
    ):
        return json_quote(text)
    if text.lower() in {"true", "false", "null", "yes", "no"}:
        return json_quote(text)
    return text


def emit_block(text: str, indent: int) -> list[str]:
    pad = "  " * indent
    lines = [f"{pad}|"]
    for line in text.splitlines():
        lines.append(f"{pad}{line}")
    if text.endswith("\n"):
        lines.append(pad)
    return lines


def json_quote(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def emit_map(obj: dict[str, Any], indent: int = 0) -> list[str]:
    pad = "  " * indent
    lines: list[str] = []
    for key, value in obj.items():
        if value is None:
            continue
        if isinstance(value, dict):
            if not value:
                continue
            lines.append(f"{pad}{key}:")
            lines.extend(emit_map(value, indent + 1))
        elif isinstance(value, list):
            if not value:
                lines.append(f"{pad}{key}: []")
                continue
            lines.append(f"{pad}{key}:")
            lines.extend(emit_list(value, indent + 1))
        else:
            if isinstance(value, str) and "\n" in value:
                lines.append(f"{pad}{key}: |")
                for line in value.splitlines():
                    lines.append(f"{pad}  {line}")
            else:
                lines.append(f"{pad}{key}: {yaml_scalar(value)}")
    return lines


def emit_list(items: list[Any], indent: int = 0) -> list[str]:
    pad = "  " * indent
    lines: list[str] = []
    for item in items:
        if isinstance(item, dict):
            if not item:
                lines.append(f"{pad}- {{}}")
                continue
            first = True
            for key, value in item.items():
                if value is None:
                    continue
                prefix = f"{pad}- " if first else f"{pad}  "
                first = False
                if isinstance(value, dict):
                    lines.append(f"{prefix}{key}:")
                    lines.extend(emit_map(value, indent + 2))
                elif isinstance(value, list):
                    lines.append(f"{prefix}{key}:")
                    lines.extend(emit_list(value, indent + 2))
                else:
                    if isinstance(value, str) and "\n" in value:
                        lines.append(f"{prefix}{key}: |")
                        body_pad = "  " * (indent + 2)
                        for line in value.splitlines():
                            lines.append(f"{body_pad}{line}")
                    else:
                        lines.append(f"{prefix}{key}: {yaml_scalar(value)}")
            if first:
                lines.append(f"{pad}- {{}}")
        else:
            lines.append(f"{pad}- {yaml_scalar(item)}")
    return lines


def dump_yaml(obj: dict[str, Any], comments: list[str] | None = None) -> str:
    lines: list[str] = []
    for comment in comments or []:
        lines.append(f"# {comment}" if comment else "#")
    lines.extend(emit_map(obj, 0))
    return "\n".join(lines) + "\n"


def render_entity(
    entity_id: str,
    name: str,
    description: str,
    fields: list[dict[str, Any]],
    prefix: str | None = None,
    start: int = 1001,
) -> str:
    obj: dict[str, Any] = {
        "id": entity_id,
        "name": name,
        "description": description,
    }
    if prefix:
        obj["allocate_code"] = {"prefix": prefix, "start": start}
    obj["fields"] = fields
    return dump_yaml(obj)


def render_http_tool(spec: dict[str, Any]) -> str:
    return dump_yaml(spec)


def render_http_workflow(
    flow_id: str,
    name: str,
    description: str,
    tool: str,
    ask: dict[str, str] | None = None,
    confirm: str = "",
    extra_asks: list[dict[str, str]] | None = None,
) -> str:
    steps: list[dict[str, Any]] = []
    input_map: dict[str, str] = {}
    asks = list(extra_asks or [])
    if ask:
        asks = [ask, *asks]
    for item in asks:
        field = item["field"]
        steps.append(
            {
                "id": f"ask_{field}",
                "type": "ask",
                "field": field,
                "message": item["message"],
            }
        )
        input_map[field] = field
    tool_step: dict[str, Any] = {
        "id": "run",
        "type": "tool",
        "tool": tool,
        "execution": "http",
    }
    if input_map:
        tool_step["input_map"] = input_map
    steps.append(tool_step)
    steps.append({"id": "confirm", "type": "message", "message": confirm})
    steps.append({"id": "done", "type": "complete", "message": ""})
    return dump_yaml(
        {
            "id": flow_id,
            "name": name,
            "description": description,
            "trigger": {"type": "conversation"},
            "steps": steps,
        }
    )


def render_entity_workflow(
    flow_id: str,
    name: str,
    description: str,
    tool: str,
    asks: list[dict[str, str]],
    input_map: dict[str, str],
    confirm: str,
) -> str:
    steps: list[dict[str, Any]] = []
    for item in asks:
        field = item["field"]
        steps.append(
            {
                "id": f"ask_{field}",
                "type": "ask",
                "field": field,
                "message": item["message"],
            }
        )
    steps.append(
        {
            "id": "run",
            "type": "tool",
            "tool": tool,
            "execution": "runtime",
            "input_map": input_map,
        }
    )
    steps.append({"id": "confirm", "type": "message", "message": confirm})
    steps.append({"id": "done", "type": "complete"})
    return dump_yaml(
        {
            "id": flow_id,
            "name": name,
            "description": description,
            "trigger": {"type": "conversation"},
            "steps": steps,
        }
    )


def render_manifest(spec: dict[str, Any]) -> str:
    payload = dict(spec)
    comments = payload.pop("_comments", None)
    return dump_yaml(payload, comments)


def render_connection(spec: dict[str, Any]) -> str:
    payload = dict(spec)
    comments = payload.pop("_comments", None)
    return dump_yaml(payload, comments)


def default_layouts() -> str:
    return """- id: dashboard-grid
  type: grid
  columns: 12
- id: split-grid
  type: grid
  columns: 12
"""


def render_theme(colors: dict[str, str]) -> str:
    return dump_yaml(colors)


def render_sources(pairs: list[tuple[str, str]]) -> str:
    items = [{"id": sid, "type": "entity", "target": target} for sid, target in pairs]
    return "\n".join(emit_list(items, 0)) + "\n"


def render_navigation(items: list[dict[str, str]]) -> str:
    for item in items:
        icon = item.get("icon")
        if icon and icon not in ALLOWED_ICONS:
            raise ValueError(f"icon {icon} is not in the host set")
    return "\n".join(emit_list(items, 0)) + "\n"


def host_pages() -> list[dict[str, Any]]:
    return [
        {"id": "contacts", "title": "Contacts", "host": "contacts"},
        {"id": "automations", "title": "Automations", "host": "automations"},
    ]


def nav_contacts_automations() -> list[dict[str, str]]:
    return [
        {"id": "contacts", "page": "contacts", "title": "Contacts", "icon": "users"},
        {"id": "automations", "page": "automations", "title": "Automations", "icon": "workflow"},
    ]


def person_field(description: str) -> dict[str, Any]:
    return {
        "name": "person_id",
        "type": "person",
        "ref_entity": "person",
        "description": description,
    }


def enum_field(name: str, values: list[str], required: bool = False) -> dict[str, Any]:
    field: dict[str, Any] = {"name": name, "type": "enum", "enum_values": values}
    if required:
        field["required"] = True
    return field


def field(name: str, ftype: str, required: bool = False, description: str | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {"name": name, "type": ftype}
    if required:
        item["required"] = True
    if description:
        item["description"] = description
    return item


def pagination(limit_param: str = "limit", default: int = 20, maximum: int = 50) -> dict[str, Any]:
    return {
        "style": "query",
        "limit_param": limit_param,
        "default_limit": default,
        "max_limit": maximum,
    }


def staff_access() -> dict[str, Any]:
    return {"surfaces": ["staff"]}


def customer_identity(
    ownership_paths: list[str],
    require_any: list[str] | None = None,
    also: list[dict[str, Any]] | None = None,
    collect: str | None = "email_otp",
) -> dict[str, Any]:
    identity: dict[str, Any] = {"require_any": require_any or ["person.email"]}
    if collect:
        identity["collect"] = collect
    ownership: dict[str, Any] = {
        "identity": "person.email",
        "paths": ownership_paths,
    }
    if also:
        ownership["also"] = also
    return {
        "access": {"surfaces": ["customer"]},
        "identity": identity,
        "ownership": ownership,
    }


def trigger(
    trigger_id: str,
    workflow: str,
    input_variable: str,
    intents: list[str],
    reply_signals: list[str],
    required_slots: list[str],
    confirmation_message: str,
) -> dict[str, Any]:
    return {
        "id": trigger_id,
        "workflow": workflow,
        "input_variable": input_variable,
        "match": {
            "intents": intents,
            "confirmation": {
                "reply_signals": reply_signals,
                "required_slots": required_slots,
            },
        },
        "confirmation_message": confirmation_message,
    }


def slot(slot_id: str, labels: list[str], kind: str, identity: str | None = None, chip_prefix: str | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {"id": slot_id, "labels": labels, "kind": kind}
    if identity:
        item["identity"] = identity
    if chip_prefix:
        item["chip_prefix"] = chip_prefix
    return item


def write_ui(
    app_dir: Path,
    *,
    name: str,
    intro: str,
    theme: dict[str, str],
    sources: list[tuple[str, str]],
    tables: list[dict[str, Any]],
    form: dict[str, Any] | None = None,
    status: dict[str, Any] | None = None,
    extra_markdown: list[dict[str, str]] | None = None,
) -> None:
    widgets: list[dict[str, Any]] = [
        {
            "id": "intro",
            "type": "markdown",
            "title": name,
            "options": {"content": intro},
        }
    ]
    if form:
        widgets.append(
            {
                "id": form["id"],
                "type": "form",
                "title": form["title"],
                "options": {
                    "fields": form["fields"],
                    "submit_label": form.get("submit_label", "Submit"),
                    "action": {"trigger": form["trigger"]},
                },
            }
        )
    if status:
        widgets.append(
            {
                "id": status["id"],
                "type": "status",
                "title": status["title"],
                "source": status["source"],
                "options": {
                    "rows_path": "items",
                    "status_field": status.get("status_field", "status"),
                    "label_field": status["label_field"],
                    "empty_title": status.get("empty_title", "Nothing yet"),
                },
            }
        )
    for table in tables:
        widgets.append(
            {
                "id": table["id"],
                "type": "table",
                "title": table["title"],
                "source": table["source"],
                "options": {
                    "rows_path": "items",
                    "empty_title": table.get("empty_title", f"No {table['title'].lower()} yet"),
                    "columns": table["columns"],
                },
            }
        )
    for item in extra_markdown or []:
        widgets.append(
            {
                "id": item["id"],
                "type": "markdown",
                "title": item["title"],
                "options": {"content": item["content"]},
            }
        )

    pages: list[dict[str, Any]] = [
        {
            "id": "dashboard",
            "title": "Today",
            "layout": "dashboard-grid",
            "widgets": _spans(
                ["intro"]
                + ([status["id"]] if status else [])
                + ([tables[0]["id"]] if tables else [])
            ),
        }
    ]
    nav: list[dict[str, str]] = [
        {"id": "dashboard", "page": "dashboard", "title": "Today", "icon": "home"}
    ]
    for table in tables:
        page_id = table.get("page_id", table["source"])
        pages.append(
            {
                "id": page_id,
                "title": table["title"],
                "layout": "split-grid",
                "widgets": _spans(
                    ([form["id"]] if form and form.get("page") == page_id else [])
                    + [table["id"]]
                ),
            }
        )
        nav.append(
            {
                "id": page_id,
                "page": page_id,
                "title": table.get("nav_title", table["title"]),
                "icon": table.get("icon", "list"),
            }
        )
    pages.extend(host_pages())
    nav.extend(nav_contacts_automations())

    ui_dir = app_dir / "ui"
    write(ui_dir / "theme.yaml", render_theme(theme))
    write(ui_dir / "layouts.yaml", default_layouts())
    write(ui_dir / "sources.yaml", render_sources(sources))
    write(ui_dir / "navigation.yaml", render_navigation(nav))
    write(ui_dir / "pages.yaml", "\n".join(emit_list(pages, 0)) + "\n")
    write(ui_dir / "widgets.yaml", "\n".join(emit_list(widgets, 0)) + "\n")


def _spans(widget_ids: list[str]) -> list[dict[str, Any]]:
    out = []
    for wid in widget_ids:
        out.append({"widget": wid, "span": 12})
    return out


def write_http_app(spec: dict[str, Any]) -> Path:
    app_id = spec["id"]
    app_dir = APPS / app_id
    app_dir.mkdir(parents=True, exist_ok=True)

    entities: list[dict[str, Any]] = spec["entities"]
    tools: list[dict[str, Any]] = spec["tools"]
    flows: list[dict[str, Any]] = spec["flows"]
    connection = spec["connection"]

    write(
        app_dir / "manifest.yaml",
        render_manifest(
            {
                "_comments": spec.get("comments", []),
                "id": app_id,
                "name": spec["name"],
                "version": spec.get("version", "0.1.0"),
                "hosting": "runtime",
                "description": spec["description"],
                "category": spec["category"],
                "tags": spec["tags"],
                "channels": spec.get("channels", ["widget", "whatsapp"]),
                "connections": [connection["id"]],
                "http_tools": [t["id"] for t in tools],
                "entities": [e["id"] for e in entities],
                "flows": [f["id"] for f in flows],
                "events": spec["events"],
                "permissions": RUNTIME_PERMISSIONS,
                "capabilities": RUNTIME_CAPABILITIES,
                "triggers": spec["triggers"],
                "conversation_slots": spec["slots"],
                "ui": {"name": spec["name"]},
            }
        ),
    )
    write(app_dir / "connections" / f"{connection['id']}.yaml", render_connection(connection))
    for entity in entities:
        write(
            app_dir / "entities" / f"{entity['id']}.yaml",
            render_entity(
                entity["id"],
                entity["name"],
                entity["description"],
                entity["fields"],
                entity.get("prefix"),
            ),
        )
    for tool in tools:
        write(app_dir / "tools" / f"{tool['id']}.yaml", render_http_tool(tool))
    for flow in flows:
        write(
            app_dir / "workflows" / f"{flow['id']}.yaml",
            render_http_workflow(
                flow["id"],
                flow["name"],
                flow["description"],
                flow["tool"],
                ask=flow.get("ask"),
                extra_asks=flow.get("extra_asks"),
                confirm=flow["confirm"],
            ),
        )
    write_ui(
        app_dir,
        name=spec["name"],
        intro=spec["intro"],
        theme=spec["theme"],
        sources=spec["sources"],
        tables=spec["tables"],
        form=spec.get("form"),
        status=spec.get("status"),
        extra_markdown=spec.get("extra_markdown"),
    )
    write(app_dir / "README.md", spec["readme"])
    return app_dir


def write_vertical_app(spec: dict[str, Any]) -> Path:
    app_id = spec["id"]
    app_dir = APPS / app_id
    app_dir.mkdir(parents=True, exist_ok=True)
    entities: list[dict[str, Any]] = spec["entities"]
    flows: list[dict[str, Any]] = spec["flows"]
    write(
        app_dir / "manifest.yaml",
        render_manifest(
            {
                "_comments": spec.get("comments", []),
                "id": app_id,
                "name": spec["name"],
                "version": spec.get("version", "0.1.0"),
                "hosting": "runtime",
                "description": spec["description"],
                "category": spec["category"],
                "tags": spec["tags"],
                "channels": spec.get("channels", ["widget", "whatsapp"]),
                "entities": [e["id"] for e in entities],
                "flows": [f["id"] for f in flows],
                "events": spec["events"],
                "permissions": RUNTIME_PERMISSIONS,
                "capabilities": RUNTIME_CAPABILITIES,
                "triggers": spec["triggers"],
                "conversation_slots": spec["slots"],
                "ui": {"name": spec["name"]},
            }
        ),
    )
    for entity in entities:
        write(
            app_dir / "entities" / f"{entity['id']}.yaml",
            render_entity(
                entity["id"],
                entity["name"],
                entity["description"],
                entity["fields"],
                entity.get("prefix"),
            ),
        )
    for flow in flows:
        write(
            app_dir / "workflows" / f"{flow['id']}.yaml",
            render_entity_workflow(
                flow["id"],
                flow["name"],
                flow["description"],
                flow["tool"],
                asks=flow["asks"],
                input_map=flow["input_map"],
                confirm=flow["confirm"],
            ),
        )
    write_ui(
        app_dir,
        name=spec["name"],
        intro=spec["intro"],
        theme=spec["theme"],
        sources=spec["sources"],
        tables=spec["tables"],
        form=spec.get("form"),
        status=spec.get("status"),
        extra_markdown=spec.get("extra_markdown"),
    )
    write(app_dir / "README.md", spec["readme"])
    return app_dir
