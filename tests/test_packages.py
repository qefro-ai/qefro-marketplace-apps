"""Validate every Marketplace App package against existing Qefro metadata conventions.

These tests are metadata-only. They do not call vendor APIs and they do not
require Qefro Runtime. Identity, surface, and isolation rules must already be
expressible in YAML; Runtime already enforces the generic counterparts.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("PyYAML is required. pip install pyyaml\n")
    raise

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
FORBIDDEN_HEADER_KEYS = {
    "authorization",
    "api_key",
    "apikey",
    "access_token",
    "secret",
    "password",
    "token",
}
IDENTITY_OVERRIDE_KEYS = {
    "email",
    "phone",
    "person_id",
    "customer_id",
    "workspace_id",
    "tenant_id",
    "external_id",
    "external_customer_id",
    "installation_id",
    "organization_id",
}
PLACEHOLDER_RE = re.compile(r"\{([^{}]+)\}")
CRM_AUTOMATION_ACTION_TYPES = {
    "send_whatsapp",
    "send_email",
    "add_tag",
    "remove_tag",
    "change_contact_status",
    "assign_user",
    "create_followup",
    "create_task",
    "notify_team",
    "delay",
    "delegate_to_agent",
    "send_webhook",
}
TEMPLATE_FORBIDDEN_KEYS = FORBIDDEN_CONNECTION_KEYS | {
    "headers",
    "header",
    "destination_url",
    "endpoint",
    "signing_secret",
    "tenant_id",
    "workspace_id",
    "installation_id",
    "organization_id",
    "person_id",
    "customer_id",
    "code",
    "script",
    "javascript",
    "cel",
    "expr",
    "expression",
    "connection_id",
    "connection",
}
KNOWN_FIELD_TYPES = {
    "string",
    "integer",
    "float",
    "boolean",
    "date",
    "datetime",
    "email",
    "phone",
    "url",
    "uuid",
    "enum",
    "json",
    "person",
    "image",
    "media",
    "relation",
}
KNOWN_STEP_TYPES = {
    "ask",
    "tool",
    "condition",
    "challenge",
    "upload",
    "delay",
    "approval",
    "message",
    "tag",
    "assign",
    "activity",
    "complete",
    "branch",
    "notify",
    "handoff",
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
SECRET_PATTERNS = [
    re.compile(r"sk_live_[A-Za-z0-9]+"),
    re.compile(r"sk_test_[A-Za-z0-9]{8,}"),
    re.compile(r"rk_live_"),
    re.compile(r"whsec_[A-Za-z0-9]+"),
    re.compile(r"xox[baprs]-"),
    re.compile(r"-----BEGIN "),
]


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def app_dirs() -> list[Path]:
    dirs = sorted(p for p in APPS.iterdir() if p.is_dir() and (p / "manifest.yaml").exists())
    if not dirs:
        raise AssertionError(f"no apps found under {APPS}")
    return dirs


def placeholders(value) -> list[str]:
    found: list[str] = []
    if isinstance(value, str):
        found.extend(PLACEHOLDER_RE.findall(value))
    elif isinstance(value, dict):
        for item in value.values():
            found.extend(placeholders(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(placeholders(item))
    return found


def walk_keys(value, prefix=""):
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else key
            yield path, key, item
            yield from walk_keys(item, path)
    elif isinstance(value, list):
        for idx, item in enumerate(value):
            yield from walk_keys(item, f"{prefix}[{idx}]")


class PackageConventionTests(unittest.TestCase):
    def test_every_app_is_runtime_hosted_metadata(self):
        for app in app_dirs():
            with self.subTest(app=app.name):
                manifest = load_yaml(app / "manifest.yaml")
                self.assertEqual(manifest.get("hosting"), "runtime")
                self.assertFalse(manifest.get("endpoint"))
                self.assertTrue(manifest.get("entities"))
                self.assertNotIn("connectors", manifest)
                self.assertFalse((app / "src").exists())
                self.assertFalse(list(app.glob("Dockerfile*")))
                self.assertFalse(list(app.glob("**/*.rs")))
                self.assertFalse(list(app.glob("**/*.ts")))
                self.assertFalse(list(app.glob("**/*.go")))

    def test_manifest_sections_match_files(self):
        for app in app_dirs():
            with self.subTest(app=app.name):
                manifest = load_yaml(app / "manifest.yaml")
                self._match_ids(app, "entities", manifest.get("entities") or [], "entities")
                self._match_ids(app, "workflows", manifest.get("flows") or [], "workflows")
                self._match_ids(app, "tools", manifest.get("http_tools") or [], "tools")
                self._match_ids(app, "connections", manifest.get("connections") or [], "connections")
                for event in manifest.get("events") or []:
                    self.assertIn(".", event)
                    self.assertRegex(event, r"^[a-z0-9][a-z0-9_.-]*$")
                for perm in manifest.get("permissions") or []:
                    self.assertRegex(perm, r"^[a-z][a-z_-]*\.[a-z*_]+$")
                for trig in manifest.get("triggers") or []:
                    self.assertIn(trig["workflow"], manifest.get("flows") or [])
                    self.assertTrue(trig.get("id"))

    def _match_ids(self, app: Path, folder: str, ids: list, label: str):
        directory = app / folder
        files = sorted(p.stem for p in directory.glob("*.yaml")) if directory.exists() else []
        self.assertEqual(sorted(ids), files, f"{app.name} {label} mismatch")

    def test_entities_use_qefro_field_types_and_no_authority_fields(self):
        for app in app_dirs():
            for path in sorted((app / "entities").glob("*.yaml")):
                with self.subTest(path=str(path.relative_to(ROOT))):
                    entity = load_yaml(path)
                    self.assertTrue(entity.get("fields"))
                    names = []
                    for field in entity["fields"]:
                        names.append(field["name"])
                        self.assertIn(field["type"], KNOWN_FIELD_TYPES)
                        self.assertNotIn(
                            field["name"].lower(),
                            {"workspace_id", "tenant_id", "installation_id", "organization_id"},
                        )
                        if field["name"].lower() == "person_id":
                            self.assertEqual(field["type"], "person")
                        if field["type"] == "enum":
                            self.assertTrue(field.get("enum_values"))
                        if field["type"] == "person":
                            self.assertEqual(field.get("ref_entity", "person"), "person")
                        if "unique" in field:
                            self.assertIsInstance(field["unique"], bool)
                            if field["unique"]:
                                self.assertNotIn(
                                    field["type"],
                                    {"person", "relation", "image", "media", "json"},
                                )
                    self.assertEqual(len(names), len(set(names)))

    def test_customer_tools_bind_hub_identity_and_ownership(self):
        for app in app_dirs():
            tools_dir = app / "tools"
            if not tools_dir.exists():
                continue
            for path in sorted(tools_dir.glob("*.yaml")):
                tool = load_yaml(path)
                surfaces = [s.lower() for s in (tool.get("access") or {}).get("surfaces") or []]
                if surfaces != ["customer"]:
                    continue
                with self.subTest(path=str(path.relative_to(ROOT))):
                    identity = tool.get("identity") or {}
                    require_any = identity.get("require_any") or []
                    self.assertTrue(require_any, "customer tools must require Hub identity")
                    for item in require_any:
                        self.assertTrue(item.startswith("person."))
                    ownership = tool.get("ownership") or {}
                    self.assertTrue(ownership.get("paths"), "customer tools must declare ownership paths")
                    joined = placeholders(tool)
                    self.assertTrue(
                        any(p.startswith("person.") for p in joined),
                        "customer tools must send a server-resolved person.* placeholder",
                    )
                    self.assertNotIn("email", placeholders(tool.get("query")))
                    self.assertNotIn("phone", placeholders(tool.get("query")))

    def test_staff_shopwide_tools_are_not_customer_callable(self):
        for app in app_dirs():
            tools_dir = app / "tools"
            if not tools_dir.exists():
                continue
            for path in sorted(tools_dir.glob("*.yaml")):
                tool = load_yaml(path)
                description = tool.get("description") or ""
                surfaces = [s.lower() for s in (tool.get("access") or {}).get("surfaces") or []]
                staff_only = "staff-only" in description.lower() or "shop-wide" in description.lower()
                if staff_only:
                    with self.subTest(path=str(path.relative_to(ROOT))):
                        self.assertEqual(surfaces, ["staff"])

    def test_workflows_are_flowrunner_shapes(self):
        for app in app_dirs():
            for path in sorted((app / "workflows").glob("*.yaml")):
                with self.subTest(path=str(path.relative_to(ROOT))):
                    flow = load_yaml(path)
                    self.assertTrue(flow.get("trigger"))
                    self.assertTrue(flow.get("steps"))
                    types = [step["type"] for step in flow["steps"]]
                    self.assertIn("complete", types)
                    for step in flow["steps"]:
                        self.assertIn(step["type"], KNOWN_STEP_TYPES)
                        if step["type"] == "tool":
                            self.assertTrue(step.get("tool"))
                            self.assertNotIn("storage.", step["tool"])
                            execution = step.get("execution")
                            if step["tool"].startswith("entity."):
                                self.assertEqual(execution, "runtime")
                            else:
                                self.assertEqual(execution, "http")

    def test_http_tools_are_generic_and_connection_scoped(self):
        for app in app_dirs():
            manifest = load_yaml(app / "manifest.yaml")
            tools_dir = app / "tools"
            if not tools_dir.exists():
                self.assertFalse(manifest.get("http_tools"))
                continue
            connections = set(manifest.get("connections") or [])
            for path in sorted(tools_dir.glob("*.yaml")):
                with self.subTest(path=str(path.relative_to(ROOT))):
                    tool = load_yaml(path)
                    self.assertIn(tool["connection"], connections)
                    self.assertIn(tool["method"].upper(), {"GET", "POST", "PUT", "PATCH", "DELETE"})
                    self.assertTrue(tool["path"].startswith("/"))
                    self.assertNotIn("://", tool["path"])
                    self.assertNotIn("/../", tool["path"])
                    query = tool.get("query") or {}
                    headers = tool.get("headers") or {}
                    for key in query:
                        self.assertNotIn(key.lower(), FORBIDDEN_HEADER_KEYS)
                    for key in headers:
                        self.assertNotIn(key.lower(), FORBIDDEN_HEADER_KEYS)
                    for name in placeholders(tool.get("path")) + placeholders(query) + placeholders(tool.get("body")):
                        base = name.split(".")[0]
                        if name.startswith("person."):
                            continue
                        self.assertNotIn(name, IDENTITY_OVERRIDE_KEYS)
                        self.assertNotIn(base, IDENTITY_OVERRIDE_KEYS)

    def test_connections_have_no_secrets_or_destinations(self):
        for app in app_dirs():
            conn_dir = app / "connections"
            if not conn_dir.exists():
                continue
            for path in sorted(conn_dir.glob("*.yaml")):
                with self.subTest(path=str(path.relative_to(ROOT))):
                    connection = load_yaml(path)
                    self.assertTrue(connection.get("id"))
                    for _, key, _ in walk_keys(connection):
                        lower = str(key).lower()
                        if lower in {"client_secret_source", "client_id_source"}:
                            continue
                        self.assertNotIn(lower, FORBIDDEN_CONNECTION_KEYS)
                        self.assertNotIn("secret", lower)
                        self.assertNotIn("access_token", lower)
                    oauth = connection.get("oauth") or {}
                    for url_key in ("authorize_url", "token_url", "revoke_url"):
                        url = oauth.get(url_key)
                        if url:
                            self.assertTrue(url.startswith("https://"))
                    webhooks = connection.get("webhooks") or {}
                    if webhooks:
                        hmac = webhooks.get("hmac") or {}
                        self.assertTrue(hmac.get("algorithm"))
                        self.assertTrue(hmac.get("header"))
                        self.assertIn(hmac.get("encoding"), {"hex", "base64", None})
                        topics = webhooks.get("topics") or {}
                        self.assertTrue(topics)
                        manifest = load_yaml(app / "manifest.yaml")
                        events = set(manifest.get("events") or [])
                        for mapped in topics.values():
                            self.assertIn(mapped, events)

    def test_webhook_topics_do_not_imply_a_package_http_server(self):
        for app in app_dirs():
            self.assertFalse((app / "webhooks").exists(), f"{app.name} must not ship a webhooks/ server")
            for path in app.rglob("*"):
                if path.suffix in {".py", ".rs", ".js", ".ts"} and "scripts" not in path.parts and "tests" not in path.parts:
                    self.fail(f"executable file inside package: {path}")

    def test_ui_uses_host_contacts_and_automations_when_present(self):
        for app in app_dirs():
            ui = app / "ui"
            if not ui.exists():
                continue
            with self.subTest(app=app.name):
                pages = load_yaml(ui / "pages.yaml")
                hosts = {page.get("id"): page.get("host") for page in pages}
                self.assertEqual(hosts.get("contacts"), "contacts")
                self.assertEqual(hosts.get("automations"), "automations")
                nav = load_yaml(ui / "navigation.yaml")
                for item in nav:
                    if item.get("icon"):
                        self.assertIn(item["icon"], ALLOWED_ICONS)
                    page = item.get("page") or item["id"]
                    self.assertTrue(any(p["id"] == page for p in pages))
                widgets = load_yaml(ui / "widgets.yaml")
                manifest = load_yaml(app / "manifest.yaml")
                flows = set(manifest.get("flows") or [])
                for widget in widgets:
                    if widget.get("type") != "form":
                        continue
                    trigger = ((widget.get("options") or {}).get("action") or {}).get("trigger")
                    self.assertIn(trigger, flows)

    def test_no_channel_or_provider_branches_in_metadata(self):
        banned = [
            re.compile(r"if\s+provider\s*=="),
            re.compile(r"if\s+channel\s*=="),
            re.compile(r"if channel =="),
        ]
        for app in app_dirs():
            for path in app.rglob("*.yaml"):
                text = path.read_text(encoding="utf-8")
                for pattern in banned:
                    self.assertIsNone(pattern.search(text), f"{path} contains runtime-style branching")

    def test_no_embedded_secrets(self):
        for app in app_dirs():
            for path in app.rglob("*"):
                if not path.is_file() or path.suffix not in {".yaml", ".md", ".yml"}:
                    continue
                text = path.read_text(encoding="utf-8")
                for pattern in SECRET_PATTERNS:
                    self.assertIsNone(pattern.search(text), f"possible secret in {path}")

    def test_cross_tenant_authority_is_not_package_controlled(self):
        for app in app_dirs():
            for path in app.rglob("*.yaml"):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("workspace_id:", text)
                self.assertNotIn("tenant_id:", text)
                self.assertNotRegex(text, r"\{workspace_id\}")
                self.assertNotRegex(text, r"\{tenant_id\}")

    def test_customer_tools_cannot_take_llm_identity_overrides(self):
        for app in app_dirs():
            tools_dir = app / "tools"
            if not tools_dir.exists():
                continue
            for path in sorted(tools_dir.glob("*.yaml")):
                tool = load_yaml(path)
                surfaces = [s.lower() for s in (tool.get("access") or {}).get("surfaces") or []]
                names = placeholders(tool.get("path")) + placeholders(tool.get("query")) + placeholders(tool.get("body"))
                llm_params = [n for n in names if "." not in n]
                with self.subTest(path=str(path.relative_to(ROOT))):
                    for key in IDENTITY_OVERRIDE_KEYS:
                        self.assertNotIn(key, llm_params)
                    if "customer" in surfaces and "staff" not in surfaces:
                        self.assertNotIn("email", llm_params)
                        self.assertNotIn("phone", llm_params)
                        self.assertTrue(any(n.startswith("person.") for n in names))

    def test_existing_reference_apps_still_present(self):
        names = {p.name for p in app_dirs()}
        for required in (
            "shopify",
            "restaurant-pro",
            "real-estate-pro",
            "clinic-pro",
            "http-catalog",
        ):
            self.assertIn(required, names)

    def test_http_request_encoding_and_root_items(self):
        for app in app_dirs():
            tools_dir = app / "tools"
            if not tools_dir.exists():
                continue
            for path in sorted(tools_dir.glob("*.yaml")):
                tool = load_yaml(path)
                with self.subTest(path=str(path.relative_to(ROOT))):
                    encoding = ((tool.get("request") or {}).get("encoding") or "json").lower()
                    self.assertIn(encoding, {"json", "form"})
                    items = (tool.get("response") or {}).get("items")
                    if items:
                        self.assertNotIn("://", str(items))
                        self.assertTrue(items == "$root" or all(c.isalnum() or c in "._" for c in str(items)))
                    emits = tool.get("emits") or []
                    if isinstance(emits, str):
                        emits = [emits]
                    for entry in emits:
                        name = entry if isinstance(entry, str) else entry.get("event")
                        self.assertIn(".", name)
                    if emits:
                        manifest = load_yaml(app / "manifest.yaml")
                        declared = set(manifest.get("events") or [])
                        for entry in emits:
                            name = entry if isinstance(entry, str) else entry.get("event")
                            self.assertIn(name, declared)

    def test_flow_constants_are_literals(self):
        for app in app_dirs():
            for path in sorted((app / "workflows").glob("*.yaml")):
                flow = load_yaml(path)
                constants = flow.get("constants") or {}
                with self.subTest(path=str(path.relative_to(ROOT))):
                    for key, value in constants.items():
                        self.assertRegex(key, r"^[A-Za-z0-9_]+$")
                        self.assertTrue(isinstance(value, (str, int, float, bool)))
                    for step in flow.get("steps") or []:
                        mapping = step.get("input_map") or {}
                        for source in mapping.values():
                            if isinstance(source, str) and source.startswith("$constants."):
                                name = source.split(".", 1)[1]
                                self.assertIn(name, constants)

    def test_entity_status_events_are_generic(self):
        for app in app_dirs():
            for path in sorted((app / "entities").glob("*.yaml")):
                entity = load_yaml(path)
                events = entity.get("status_events") or {}
                if not events:
                    continue
                with self.subTest(path=str(path.relative_to(ROOT))):
                    field_names = {f["name"] for f in entity["fields"]}
                    status_field = entity.get("status_field") or "status"
                    self.assertIn(status_field, field_names)
                    for status, event in events.items():
                        self.assertTrue(status)
                        self.assertIn(".", event)
                        self.assertNotIn("workspace_id", event)

    def test_connection_auth_and_webhook_metadata(self):
        allowed_auth = {"bearer", "named_header", "basic", "none"}
        for app in app_dirs():
            conn_dir = app / "connections"
            if not conn_dir.exists():
                continue
            for path in sorted(conn_dir.glob("*.yaml")):
                connection = load_yaml(path)
                with self.subTest(path=str(path.relative_to(ROOT))):
                    auth = (connection.get("auth_type") or "named_header").lower()
                    self.assertIn(auth, allowed_auth)
                    oauth = connection.get("oauth") or {}
                    if oauth.get("token_auth_method"):
                        self.assertIn(
                            oauth["token_auth_method"],
                            {"client_secret_post", "client_secret_basic"},
                        )
                    webhooks = connection.get("webhooks") or {}
                    if not webhooks:
                        continue
                    signature = webhooks.get("signature") or webhooks.get("hmac") or {}
                    self.assertTrue(signature.get("header") or (webhooks.get("hmac") or {}).get("header"))
                    identity = webhooks.get("identity") or {}
                    self.assertTrue(identity.get("header") or webhooks.get("identity_header"))
                    if identity.get("source"):
                        self.assertEqual(identity["source"], "header")
                    topic = webhooks.get("topic") or {}
                    source = topic.get("source") or "header"
                    self.assertIn(source, {"header", "json"})
                    if source == "json":
                        self.assertTrue(topic.get("path"))
                    else:
                        self.assertTrue(topic.get("header") or webhooks.get("topic_header"))
                    if signature.get("format"):
                        self.assertIn(signature["format"], {"raw", "timestamped", "prefixed"})
                    if signature.get("encoding") or (webhooks.get("hmac") or {}).get("encoding"):
                        enc = signature.get("encoding") or (webhooks.get("hmac") or {}).get("encoding")
                        self.assertIn(enc, {"hex", "base64"})

    def test_customer_identity_placeholders_are_person_scoped(self):
        for app in app_dirs():
            tools_dir = app / "tools"
            if not tools_dir.exists():
                continue
            for path in sorted(tools_dir.glob("*.yaml")):
                tool = load_yaml(path)
                names = placeholders(tool.get("path")) + placeholders(tool.get("query")) + placeholders(
                    tool.get("body")
                )
                with self.subTest(path=str(path.relative_to(ROOT))):
                    for name in names:
                        if name.startswith("person."):
                            self.assertIn(name, {"person.email", "person.phone", "person.external_id"})
                        self.assertNotIn(name, IDENTITY_OVERRIDE_KEYS)



class NewAppCoverageTests(unittest.TestCase):
    EXPECTED = [
        "stripe",
        "razorpay",
        "woocommerce",
        "google-calendar",
        "google-sheets",
        "freshdesk",
        "zoho-crm",
        "whatsapp-business",
        "calendly",
        "slack",
        "appointment",
        "field-service",
        "education",
        "clinic-pro",
        "logistics",
        "restaurant-pro",
        "real-estate-pro",
    ]

    def test_phase_apps_exist(self):
        names = {p.name for p in app_dirs()}
        missing = [name for name in self.EXPECTED if name not in names]
        self.assertFalse(missing, f"missing apps: {missing}")

    def test_http_phase_apps_declare_webhooks_and_surfaces(self):
        http_apps = self.EXPECTED[:10]
        for name in http_apps:
            app = APPS / name
            if not app.exists():
                continue
            with self.subTest(app=name):
                manifest = load_yaml(app / "manifest.yaml")
                self.assertTrue(manifest.get("http_tools"))
                self.assertTrue(manifest.get("connections"))
                conn = load_yaml(next((app / "connections").glob("*.yaml")))
                if name not in {"google-sheets"}:
                    self.assertTrue((conn.get("webhooks") or {}).get("topics"))
                tools = [load_yaml(p) for p in (app / "tools").glob("*.yaml")]
                surfaces = {
                    s
                    for tool in tools
                    for s in (tool.get("access") or {}).get("surfaces") or []
                }
                self.assertIn("staff", surfaces)
                if name in {
                    "stripe",
                    "razorpay",
                    "woocommerce",
                    "freshdesk",
                    "calendly",
                }:
                    self.assertIn("customer", surfaces)

    def test_vertical_apps_are_entity_native(self):
        for name in self.EXPECTED[10:]:
            app = APPS / name
            if not app.exists():
                continue
            with self.subTest(app=name):
                manifest = load_yaml(app / "manifest.yaml")
                self.assertFalse(manifest.get("http_tools"))
                self.assertFalse(manifest.get("connections"))
                self.assertGreaterEqual(len(manifest.get("entities") or []), 3)
                self.assertGreaterEqual(len(manifest.get("flows") or []), 3)
                person_fields = 0
                for path in (app / "entities").glob("*.yaml"):
                    entity = load_yaml(path)
                    person_fields += sum(1 for f in entity["fields"] if f.get("type") == "person")
                self.assertGreaterEqual(person_fields, 1)
                for path in (app / "workflows").glob("*.yaml"):
                    flow = load_yaml(path)
                    tools = [s.get("tool") for s in flow["steps"] if s.get("type") == "tool"]
                    self.assertTrue(all(t.startswith("entity.") for t in tools if t))


class RealEstateAvailabilitySettingsTests(unittest.TestCase):
    def test_viewing_contract_is_structural_only(self):
        viewing = load_yaml(APPS / "real-estate-pro" / "entities" / "viewing.yaml")
        avail = viewing["availability"]
        self.assertEqual(avail["booking"]["datetime_field"], "scheduled_at")
        self.assertNotIn("duration_minutes", avail["booking"])
        self.assertEqual(avail["capacity"]["mode"], "exclusive")
        self.assertEqual(avail["capacity"]["resource"]["field"], "property_id")
        for operating in (
            "timezone",
            "working_hours",
            "closed_days",
            "date_window_days",
            "blocking_statuses",
        ):
            self.assertNotIn(operating, avail)

    def test_operating_values_live_in_app_settings(self):
        manifest = load_yaml(APPS / "real-estate-pro" / "manifest.yaml")
        schema = load_yaml(APPS / "real-estate-pro" / "settings" / "business.yaml")["settings"]
        keys = [s["key"] if isinstance(s, dict) else s for s in manifest["settings"]]
        expected = {
            "timezone",
            "duration_minutes",
            "start_time",
            "end_time",
            "closed_days",
            "date_window_days",
            "blocking_statuses",
        }
        self.assertEqual(set(keys), expected)
        self.assertEqual(set(schema), expected)
        self.assertEqual(schema["timezone"]["default"], "Asia/Kolkata")
        self.assertEqual(schema["duration_minutes"]["default"], 30)
        self.assertEqual(schema["start_time"]["default"], "09:00")
        self.assertEqual(schema["end_time"]["default"], "18:00")
        self.assertEqual(schema["closed_days"]["default"], "sunday")
        self.assertEqual(schema["date_window_days"]["default"], 5)

    def test_request_viewing_uses_availability_runtime(self):
        flow = load_yaml(APPS / "real-estate-pro" / "workflows" / "request-viewing.yaml")
        tools = [s.get("tool") for s in flow["steps"] if s.get("type") == "tool"]
        self.assertEqual(tools.count("entity.viewing.availability"), 3)
        self.assertIn("entity.viewing.create", tools)
        self.assertNotIn("storage.insert_booking", tools)
        asks = {s["field"]: s for s in flow["steps"] if s.get("type") == "ask"}
        self.assertEqual(asks["date"]["choices_from"], "available_dates")
        self.assertEqual(asks["time"]["choices_from"], "available_slots")
        self.assertEqual(asks["property_id"]["title_field"], "title")
        self.assertEqual(asks["property_id"]["value_field"], "id")
        self.assertEqual(asks["property_id"]["image_field"], "image_url")
        self.assertEqual(asks["property_id"]["description_field"], "city")
        self.assertEqual(asks["city"]["choices_from"], "properties")
        self.assertEqual(asks["property_type"]["choices"][0]["id"], "apartment")

    def test_reschedule_viewing_uses_availability_runtime(self):
        flow = load_yaml(APPS / "real-estate-pro" / "workflows" / "reschedule-viewing.yaml")
        tools = [s.get("tool") for s in flow["steps"] if s.get("type") == "tool"]
        self.assertEqual(tools.count("entity.viewing.availability"), 3)
        self.assertIn("entity.viewing.update", tools)
        asks = {s["field"]: s for s in flow["steps"] if s.get("type") == "ask"}
        self.assertEqual(asks["date"]["choices_from"], "available_dates")
        self.assertEqual(asks["time"]["choices_from"], "available_slots")


class RealEstateDomainTests(unittest.TestCase):
    APP = APPS / "real-estate-pro"

    def _entity(self, name: str):
        return load_yaml(self.APP / "entities" / f"{name}.yaml")

    def _field(self, entity: dict, name: str) -> dict:
        return next(f for f in entity["fields"] if f["name"] == name)

    def test_deal_entity_and_flow_are_gone(self):
        manifest = load_yaml(self.APP / "manifest.yaml")
        self.assertNotIn("deal", manifest["entities"])
        self.assertNotIn("create-deal", manifest["flows"])
        self.assertNotIn("deal.created", manifest.get("events") or [])
        self.assertNotIn("deal.updated", manifest.get("events") or [])
        self.assertNotIn("deal.closed", manifest.get("events") or [])
        self.assertFalse((self.APP / "entities" / "deal.yaml").exists())
        self.assertFalse((self.APP / "workflows" / "create-deal.yaml").exists())
        for path in self.APP.rglob("*.yaml"):
            text = path.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"\bentity\.deal\.")
            self.assertNotIn("target: deal", text)
            self.assertNotIn("entity: deal", text)
            self.assertNotIn("create-deal", text)
            self.assertNotIn("deal.closed", text)

    def test_offer_is_canonical_commercial_lifecycle(self):
        manifest = load_yaml(self.APP / "manifest.yaml")
        self.assertIn("offer", manifest["entities"])
        self.assertIn("create-offer", manifest["flows"])
        self.assertIn("offer.closed", manifest["events"])
        offer = self._entity("offer")
        self.assertEqual(offer["scope"], "customer")
        person = self._field(offer, "person_id")
        self.assertEqual(person["type"], "person")
        self.assertEqual(person["ref_entity"], "person")
        self.assertTrue(person.get("required"))
        property_id = self._field(offer, "property_id")
        self.assertEqual(property_id["type"], "relation")
        self.assertEqual(property_id["ref_entity"], "property")
        self.assertTrue(property_id.get("required"))
        status = self._field(offer, "status")
        for value in ("submitted", "under_contract", "closed", "fallen_through"):
            self.assertIn(value, status["enum_values"])
        self.assertTrue(any(f["name"] == "closed_at" for f in offer["fields"]))
        self.assertEqual(self._field(offer, "agent_id")["type"], "relation")
        self.assertEqual(self._field(offer, "agent_id")["ref_entity"], "agent")
        self.assertEqual(offer["status_events"]["closed"], "offer.closed")
        field_names = {f["name"] for f in offer["fields"]}
        self.assertNotIn("offer_id", field_names)
        self.assertNotIn("email", field_names)
        self.assertNotIn("phone", field_names)
        self.assertNotIn("lead_name", field_names)

    def test_create_offer_binds_the_viewing_customer(self):
        flow = load_yaml(self.APP / "workflows" / "create-offer.yaml")
        tools = [s.get("tool") for s in flow["steps"] if s.get("type") == "tool"]
        self.assertIn("entity.property.list", tools)
        self.assertIn("entity.viewing.get", tools)
        self.assertIn("entity.offer.create", tools)
        asks = {s["field"]: s for s in flow["steps"] if s.get("type") == "ask"}
        self.assertEqual(asks["property_id"]["choices_from"], "properties")
        self.assertEqual(asks["property_id"]["value_field"], "id")
        self.assertEqual(asks["viewing_id"]["choices_from"], "viewings")
        create = next(s for s in flow["steps"] if s.get("tool") == "entity.offer.create")
        mapping = create["input_map"]
        self.assertEqual(mapping["property_id"], "property_id")
        # Staff command chat has no session customer. The person is the one
        # already stored on the viewing, then checked against Customer Hub.
        self.assertEqual(mapping["person_id"], "viewing.person_id")
        self.assertEqual(mapping["currency"], "property.currency")
        self.assertNotIn("email", mapping)
        self.assertNotIn("phone", mapping)
        self.assertNotIn("lead_name", mapping)

    def test_lead_is_person_scoped_pipeline_not_identity(self):
        lead = self._entity("lead")
        self.assertEqual(lead["scope"], "customer")
        person = self._field(lead, "person_id")
        self.assertEqual(person["type"], "person")
        self.assertTrue(person.get("required"))
        names = {f["name"] for f in lead["fields"]}
        self.assertNotIn("email", names)
        self.assertNotIn("phone", names)
        self.assertIn("source", names)
        self.assertIn("status", names)
        flow = load_yaml(self.APP / "workflows" / "create-lead.yaml")
        create = next(s for s in flow["steps"] if s.get("tool") == "entity.lead.create")
        self.assertNotIn("person_id", create["input_map"])
        self.assertNotIn("email", create["input_map"])
        self.assertNotIn("phone", create["input_map"])

    def test_viewing_is_person_and_property_scoped(self):
        viewing = self._entity("viewing")
        self.assertTrue(self._field(viewing, "person_id").get("required"))
        self.assertEqual(self._field(viewing, "person_id")["type"], "person")
        property_id = self._field(viewing, "property_id")
        self.assertEqual(property_id["type"], "relation")
        self.assertEqual(property_id["ref_entity"], "property")
        self.assertTrue(property_id.get("required"))
        flow = load_yaml(self.APP / "workflows" / "request-viewing.yaml")
        create = next(s for s in flow["steps"] if s.get("tool") == "entity.viewing.create")
        self.assertEqual(create["input_map"]["property_id"], "property_id")
        self.assertNotIn("person_id", create["input_map"])

    def test_no_deal_ui_or_navigation(self):
        nav = load_yaml(self.APP / "ui" / "navigation.yaml")
        pages = load_yaml(self.APP / "ui" / "pages.yaml")
        sources = load_yaml(self.APP / "ui" / "sources.yaml")
        widgets = load_yaml(self.APP / "ui" / "widgets.yaml")
        self.assertNotIn("deals", [item["id"] for item in nav])
        self.assertNotIn("deals", [item["id"] for item in pages])
        self.assertNotIn("deals", [item["id"] for item in sources])
        self.assertNotIn("deal_form", [item["id"] for item in widgets])
        self.assertNotIn("metric_deal", [item["id"] for item in widgets])
        self.assertIn("offers", [item["id"] for item in nav])


class BillingProTests(unittest.TestCase):
    APP = APPS / "billing-pro"

    def _entity(self, name: str):
        return load_yaml(self.APP / "entities" / f"{name}.yaml")

    def _field(self, entity: dict, name: str) -> dict:
        return next(f for f in entity["fields"] if f["name"] == name)

    def test_package_is_entity_native_billing_app(self):
        manifest = load_yaml(self.APP / "manifest.yaml")
        self.assertEqual(manifest["id"], "billing-pro")
        self.assertEqual(manifest["hosting"], "runtime")
        self.assertEqual(manifest["category"], "commerce")
        self.assertEqual(manifest["channels"], ["widget", "whatsapp"])
        self.assertFalse(manifest.get("http_tools"))
        self.assertFalse(manifest.get("connections"))
        self.assertFalse(manifest.get("agent"))
        self.assertFalse(manifest.get("goal"))
        self.assertNotIn("agent:", (self.APP / "manifest.yaml").read_text(encoding="utf-8"))
        self.assertEqual(
            manifest["entities"],
            ["product", "invoice", "invoice_item", "payment", "payment_allocation", "follow_up"],
        )
        self.assertEqual(
            sorted(manifest["flows"]),
            [
                "allocate-payment",
                "cancel-invoice",
                "complete-follow-up",
                "create-follow-up",
                "create-invoice",
                "create-product",
                "on-invoice-overdue",
                "record-payment",
            ],
        )
        self.assertFalse((self.APP / "entities" / "customer.yaml").exists())
        self.assertFalse((self.APP / "entities" / "collection_case.yaml").exists())
        self.assertFalse((self.APP / "tools").exists())
        self.assertFalse((self.APP / "src").exists())

    def test_no_payments_collection_pro_package(self):
        self.assertFalse((APPS / "payments-collection-pro").exists())

    def test_person_identity_uses_hub_person_type(self):
        for name in ("invoice", "payment"):
            entity = self._entity(name)
            self.assertEqual(entity["scope"], "customer")
            person = self._field(entity, "person_id")
            self.assertEqual(person["type"], "person")
            self.assertEqual(person["ref_entity"], "person")
            self.assertTrue(person.get("required"))
        follow = self._entity("follow_up")
        self.assertNotEqual(follow.get("scope"), "customer")
        person = self._field(follow, "person_id")
        self.assertEqual(person["type"], "person")
        self.assertEqual(person["ref_entity"], "person")
        product = self._entity("product")
        self.assertNotEqual(product.get("scope"), "customer")
        self.assertFalse(any(f["name"] == "person_id" for f in product["fields"]))
        invoice = self._entity("invoice")
        self.assertFalse(any(f["name"] in {"customer_name", "phone", "email"} for f in invoice["fields"]))

    def test_unique_sku_and_invoice_number(self):
        sku = self._field(self._entity("product"), "sku")
        self.assertTrue(sku.get("unique"))
        self.assertEqual(sku["type"], "string")
        number = self._field(self._entity("invoice"), "invoice_number")
        self.assertTrue(number.get("unique"))
        self.assertEqual(number["type"], "string")
        pay_no = self._field(self._entity("payment"), "payment_number")
        self.assertTrue(pay_no.get("unique"))

    def test_invoice_and_payment_fields(self):
        invoice = self._entity("invoice")
        names = {f["name"] for f in invoice["fields"]}
        self.assertTrue(
            {
                "invoice_number",
                "person_id",
                "issue_date",
                "due_date",
                "status",
                "currency",
                "subtotal",
                "discount",
                "tax",
                "total_amount",
                "paid_amount",
                "outstanding_amount",
                "notes",
            }.issubset(names)
        )
        self.assertEqual(
            self._field(invoice, "status")["enum_values"],
            ["draft", "issued", "partially_paid", "paid", "overdue", "cancelled"],
        )
        self.assertEqual(self._field(invoice, "issue_date").get("default"), "current_date")
        self.assertTrue(self._field(invoice, "person_id").get("required"))
        self.assertEqual(self._field(invoice, "person_id").get("label"), "Customer")
        payment = self._entity("payment")
        self.assertEqual(
            self._field(payment, "method")["enum_values"],
            ["cash", "bank_transfer", "card", "upi", "cheque", "other"],
        )
        self.assertEqual(
            self._field(payment, "status")["enum_values"],
            ["received", "pending", "failed", "reversed"],
        )
        self.assertFalse(any(f["name"] == "invoice_id" for f in payment["fields"]))

    def test_relations_use_relation_primitive(self):
        item = self._entity("invoice_item")
        alloc = self._entity("payment_allocation")
        follow = self._entity("follow_up")
        invoice_id = self._field(item, "invoice_id")
        self.assertEqual(invoice_id["type"], "relation")
        self.assertEqual(invoice_id["ref_entity"], "invoice")
        product_id = self._field(item, "product_id")
        self.assertEqual(product_id["type"], "relation")
        self.assertEqual(product_id["ref_entity"], "product")
        self.assertEqual(self._field(alloc, "payment_id")["ref_entity"], "payment")
        self.assertEqual(self._field(alloc, "invoice_id")["ref_entity"], "invoice")
        self.assertEqual(self._field(follow, "invoice_id")["type"], "relation")
        self.assertEqual(self._field(follow, "invoice_id")["ref_entity"], "invoice")
        self.assertFalse(any(f["name"] == "collection_case_id" for f in follow["fields"]))
        self.assertEqual(self._field(follow, "follow_up_date")["type"], "date")
        person = self._field(follow, "person_id")
        self.assertEqual(person.get("inherit_from"), "invoice_id")
        caps = alloc.get("relation_caps") or []
        self.assertEqual(len(caps), 1)
        self.assertEqual(caps[0]["field"], "amount")
        self.assertEqual(caps[0]["relation"], "payment_id")
        self.assertEqual(caps[0]["parent_field"], "amount")

    def test_status_events_are_facts(self):
        invoice = self._entity("invoice")
        payment = self._entity("payment")
        follow = self._entity("follow_up")
        self.assertEqual(invoice["status_events"]["issued"], "invoice.issued")
        self.assertEqual(invoice["status_events"]["paid"], "invoice.paid")
        self.assertEqual(invoice["status_events"]["cancelled"], "invoice.cancelled")
        self.assertEqual(invoice["status_events"]["overdue"], "invoice.overdue")
        self.assertEqual(payment["status_events"]["received"], "payment.received")
        self.assertEqual(payment["status_events"]["reversed"], "payment.reversed")
        self.assertEqual(follow["status_events"]["completed"], "follow_up.completed")
        manifest = load_yaml(self.APP / "manifest.yaml")
        declared = set(manifest["events"])
        self.assertIn("payment_allocation.created", declared)
        self.assertIn("product.created", declared)
        for events in (
            invoice["status_events"].values(),
            payment["status_events"].values(),
            follow["status_events"].values(),
        ):
            for event in events:
                self.assertIn(event, declared)

    def test_settings_match_install_schema(self):
        manifest = load_yaml(self.APP / "manifest.yaml")
        schema = load_yaml(self.APP / "settings" / "business.yaml")["settings"]
        keys = [s["key"] if isinstance(s, dict) else s for s in manifest["settings"]]
        expected = {
            "currency",
            "invoice_prefix",
            "payment_terms_days",
            "default_tax_rate",
            "follow_up_interval_days",
        }
        self.assertEqual(set(keys), expected)
        self.assertEqual(set(schema), expected)
        self.assertEqual(schema["currency"]["default"], "INR")
        self.assertEqual(schema["invoice_prefix"]["default"], "INV")
        self.assertEqual(schema["payment_terms_days"]["default"], 30)
        self.assertEqual(schema["default_tax_rate"]["default"], 0)
        self.assertEqual(schema["follow_up_interval_days"]["default"], 3)

    def test_flows_use_runtime_entity_tools(self):
        expected = {
            "create-product": ["entity.product.create"],
            "create-invoice": ["entity.invoice.create"],
            "record-payment": [
                "entity.invoice.list",
                "entity.payment.create",
                "entity.payment_allocation.create",
            ],
            "create-follow-up": ["entity.invoice.list", "entity.follow_up.create"],
            "complete-follow-up": ["entity.follow_up.list", "entity.follow_up.update"],
            "allocate-payment": [
                "entity.payment.list",
                "entity.invoice.list",
                "entity.payment_allocation.create",
            ],
            "cancel-invoice": ["entity.invoice.list", "entity.invoice.update"],
        }
        for flow_id, tools_expected in expected.items():
            flow = load_yaml(self.APP / "workflows" / f"{flow_id}.yaml")
            tools = [s.get("tool") for s in flow["steps"] if s.get("type") == "tool"]
            self.assertEqual(tools, tools_expected)
            self.assertTrue(all(s.get("execution") == "runtime" for s in flow["steps"] if s.get("type") == "tool"))
            self.assertEqual(flow["steps"][-1]["type"], "complete")
            self.assertEqual(flow.get("surfaces"), ["staff"])
            self.assertEqual(flow["trigger"]["type"], "conversation")
            self.assertNotIn("storage.insert", str(tools))
            text = str(flow)
            self.assertNotIn("person_id:", text)
            if flow_id in {"record-payment", "allocate-payment"}:
                self.assertNotIn("entity.invoice.update", tools)

    def test_ui_hosts_and_dashboard_metrics(self):
        pages = load_yaml(self.APP / "ui" / "pages.yaml")
        hosts = {page.get("id"): page.get("host") for page in pages}
        self.assertEqual(hosts.get("contacts"), "contacts")
        self.assertEqual(hosts.get("automations"), "automations")
        entities = {page.get("id"): page.get("entity") for page in pages}
        self.assertEqual(entities.get("products"), "product")
        self.assertEqual(entities.get("invoices"), "invoice")
        self.assertEqual(entities.get("payments"), "payment")
        self.assertEqual(entities.get("follow_ups"), "follow_up")
        pages_by_id = {page["id"]: page for page in pages}
        self.assertEqual(pages_by_id["pos"]["widgets"][0]["widget"], "pos_checkout")
        widgets = {w["id"]: w for w in load_yaml(self.APP / "ui" / "widgets.yaml")}
        pos = widgets["pos_checkout"]
        self.assertEqual(pos["type"], "cart_checkout")
        self.assertEqual(pos["options"]["catalog_entity"], "product")
        self.assertEqual(pos["options"]["line_entity"], "invoice_item")
        self.assertEqual(pos["options"]["document_entity"], "invoice")
        self.assertEqual(pos["options"]["payment_entity"], "payment")
        self.assertEqual(pos["options"]["allocation_entity"], "payment_allocation")
        self.assertTrue(pos["options"]["person_required"])
        self.assertEqual(pos["options"]["payment_methods"], ["cash", "upi", "card", "other"])
        nav_ids = [item["id"] for item in load_yaml(self.APP / "ui" / "navigation.yaml")]
        self.assertEqual(nav_ids[:6], ["dashboard", "pos", "invoices", "payments", "products", "follow_ups"])
        self.assertEqual(widgets["metric_total_invoiced"]["options"]["aggregate"], "sum")
        self.assertEqual(widgets["metric_total_invoiced"]["options"]["field"], "total_amount")
        self.assertEqual(widgets["metric_total_paid"]["options"]["field"], "paid_amount")
        self.assertEqual(widgets["metric_outstanding"]["options"]["field"], "outstanding_amount")
        self.assertEqual(widgets["metric_follow_up"]["options"]["filter"]["status"], "pending")
        self.assertEqual(widgets["metric_overdue"]["options"]["filter"]["status"], "overdue")
        self.assertEqual(widgets["metric_overdue"]["options"]["aggregate"], "count")

    def test_consumes_generic_platform_capabilities(self):
        invoice = self._entity("invoice")
        ops = {c["op"] for c in invoice["computed"]}
        self.assertIn("relation_sum", ops)
        self.assertIn("subtract", ops)
        self.assertIn("status_from_number", ops)
        self.assertEqual(invoice["date_events"][0]["event"], "invoice.overdue")
        self.assertEqual(invoice["on_events"][0]["event"], "invoice.paid")
        self.assertEqual(invoice["on_events"][0]["target"], "follow_up")
        self.assertEqual(invoice["on_events"][0]["set"]["status"], "completed")
        self.assertEqual(self._field(invoice, "currency").get("default_from_setting"), "currency")
        self.assertEqual(invoice.get("concurrency"), "optimistic")
        self.assertEqual((invoice.get("delete") or {}).get("mode"), "restrict")
        item = self._entity("invoice_item")
        self.assertEqual(item["computed"][0]["op"], "multiply")
        follow = self._entity("follow_up")
        self.assertEqual(follow["date_events"][0]["event"], "follow_up.due")
        manifest = load_yaml(self.APP / "manifest.yaml")
        self.assertIn("invoice.paid", manifest["events"])
        self.assertIn("follow_up.due", manifest["events"])
        self.assertNotIn("agent", manifest)

    def test_event_triggered_overdue_flow(self):
        flow = load_yaml(self.APP / "workflows" / "on-invoice-overdue.yaml")
        self.assertEqual(flow["trigger"]["type"], "event")
        self.assertEqual(flow["trigger"]["event"], "invoice.overdue")
        tools = [s.get("tool") for s in flow["steps"] if s.get("type") == "tool"]
        self.assertEqual(tools, ["entity.invoice.get", "entity.follow_up.create"])
        self.assertTrue(all(s.get("execution") == "runtime" for s in flow["steps"] if s.get("type") == "tool"))
        self.assertEqual(flow["steps"][-1]["type"], "complete")
        text = (self.APP / "workflows" / "on-invoice-overdue.yaml").read_text(encoding="utf-8")
        self.assertNotIn("person_id:", text)
        self.assertNotIn("notify", [s.get("type") for s in flow["steps"]])
        self.assertNotIn("entity.whatsapp", str(tools))
        manifest = load_yaml(self.APP / "manifest.yaml")
        self.assertIn("on-invoice-overdue", manifest["flows"])
        self.assertIn("invoice.overdue", manifest["events"])

    def test_csv_identity_fields_are_person_not_customer_entity(self):
        invoice = self._entity("invoice")
        self.assertTrue(any(f["type"] == "person" for f in invoice["fields"]))
        self.assertTrue(self._field(invoice, "invoice_number").get("unique"))
        self.assertEqual(invoice["allocate_code"]["prefix"], "INV-")
        self.assertIn("total_amount", {f["name"] for f in invoice["fields"]})
        self.assertIn("outstanding_amount", {f["name"] for f in invoice["fields"]})

    def test_permissions_and_architecture_constraints(self):
        manifest = load_yaml(self.APP / "manifest.yaml")
        self.assertEqual(
            manifest["permissions"],
            [
                "workflow.execute",
                "storage.read",
                "storage.write",
                "storage.update",
                "storage.delete",
            ],
        )
        for path in list((self.APP / "entities").glob("*.yaml")) + list(
            (self.APP / "workflows").glob("*.yaml")
        ):
            text = path.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"if\s+solution\s*==")
            self.assertNotRegex(text, r"if\s+entity\s*==")
            self.assertNotIn("collection_case", text)
            self.assertNotIn("BillingScheduler", text)
            self.assertNotIn("CollectionScheduler", text)
            self.assertNotIn("billing_chat", text)
            self.assertNotIn("pos_agent", text)
        self.assertFalse((self.APP / "entities" / "sale.yaml").exists())
        self.assertFalse((self.APP / "entities" / "order.yaml").exists())


class RestaurantProTests(unittest.TestCase):
    APP = APPS / "restaurant-pro"

    def _entity(self, name: str):
        return load_yaml(self.APP / "entities" / f"{name}.yaml")

    def _field(self, entity: dict, name: str) -> dict:
        return next(f for f in entity["fields"] if f["name"] == name)

    def test_package_is_independent_of_billing_pro(self):
        manifest = load_yaml(self.APP / "manifest.yaml")
        self.assertEqual(manifest["id"], "restaurant-pro")
        self.assertEqual(manifest["hosting"], "runtime")
        self.assertNotIn("billing-pro", str(manifest))
        self.assertNotIn("invoice", manifest.get("entities") or [])
        self.assertFalse((self.APP / "entities" / "invoice.yaml").exists())
        self.assertFalse((self.APP / "entities" / "invoice_item.yaml").exists())
        self.assertFalse((self.APP / "entities" / "payment_allocation.yaml").exists())
        self.assertFalse((self.APP / "entities" / "product.yaml").exists())
        for path in self.APP.rglob("*.yaml"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("billing-pro", text)
            self.assertNotRegex(text, r"if\s+solution\s*==")

    def test_menu_item_uses_generic_image_field(self):
        item = self._entity("menu_item")
        image = self._field(item, "image")
        self.assertEqual(image["type"], "image")
        field_names = [f["name"] for f in item["fields"]]
        self.assertNotIn("food_image", field_names)
        self.assertNotIn("image_url", field_names)
        self.assertEqual(self._field(item, "availability")["enum_values"], ["available", "sold_out", "seasonal"])

    def test_order_total_uses_generic_computed_relation(self):
        order = self._entity("order")
        self.assertEqual(order["computed"][0]["op"], "relation_sum")
        self.assertEqual(order["computed"][0]["relation"], "order_item")
        self.assertEqual(order["computed"][0]["foreign_key"], "order_id")
        self.assertEqual(order["computed"][0]["sum_field"], "amount")
        item = self._entity("order_item")
        self.assertEqual(self._field(item, "order_id")["type"], "relation")
        self.assertEqual(self._field(item, "order_id").get("required"), True)
        self.assertNotEqual(self._field(item, "order_code").get("required"), True)
        self.assertEqual(self._field(item, "menu_item_id")["type"], "relation")
        self.assertEqual(item["computed"][0]["op"], "multiply")
        self.assertEqual(item["computed"][0]["left"], "quantity")
        self.assertEqual(item["computed"][0]["right"], "unit_price")
        self.assertIn("unit_price", [f["name"] for f in item["fields"]])

    def test_person_remains_optional_for_walk_in(self):
        order = self._entity("order")
        person = self._field(order, "person_id")
        self.assertEqual(person["type"], "person")
        self.assertNotEqual(person.get("required"), True)
        payment = self._entity("payment")
        self.assertNotEqual(self._field(payment, "person_id").get("required"), True)

    def test_customers_page_is_hub_person_not_duplicate_identity(self):
        pages = {page["id"]: page for page in load_yaml(self.APP / "ui" / "pages.yaml")}
        self.assertEqual(pages["customers"]["host"], "contacts")
        self.assertNotEqual(pages["customers"].get("entity"), "customer")
        customer = self._entity("customer")
        self.assertIn("DEPRECATED", customer["description"])
        flow = load_yaml(self.APP / "workflows" / "create-customer.yaml")
        self.assertIs(flow.get("enabled"), False)
        self.assertIn("entity.customer.create", str(flow))

    def test_payment_methods_come_from_metadata(self):
        payment = self._entity("payment")
        self.assertEqual(self._field(payment, "method")["enum_values"], ["cash", "card", "upi"])
        self.assertEqual(self._field(payment, "order_id")["type"], "relation")
        self.assertEqual(self._field(payment, "order_id").get("required"), True)
        self.assertNotEqual(self._field(payment, "order_code").get("required"), True)

    def test_payment_received_completes_pending_order(self):
        payment = self._entity("payment")
        self.assertEqual(payment["status_events"]["completed"], "payment.received")
        rule = payment["on_events"][0]
        self.assertEqual(rule["event"], "payment.received")
        self.assertEqual(rule["target"], "order")
        self.assertEqual(rule["match_field"], "id")
        self.assertEqual(rule["match_from"], "order_id")
        self.assertEqual(rule["set"]["status"], "completed")
        manifest = load_yaml(self.APP / "manifest.yaml")
        self.assertIn("payment.received", manifest["events"])

    def test_pos_binds_restaurant_entities_on_cart_checkout(self):
        pages = {page["id"]: page for page in load_yaml(self.APP / "ui" / "pages.yaml")}
        self.assertEqual(pages["pos"]["widgets"][0]["widget"], "pos_checkout")
        widgets = {w["id"]: w for w in load_yaml(self.APP / "ui" / "widgets.yaml")}
        pos = widgets["pos_checkout"]
        self.assertEqual(pos["type"], "cart_checkout")
        options = pos["options"]
        self.assertEqual(options["catalog_entity"], "menu_item")
        self.assertEqual(options["line_entity"], "order_item")
        self.assertEqual(options["document_entity"], "order")
        self.assertEqual(options["payment_entity"], "payment")
        self.assertNotIn("allocation_entity", options)
        self.assertFalse(options.get("person_required"))
        self.assertEqual(options["catalog_category_field"], "category_name")
        self.assertEqual(options["catalog_unavailable_values"], ["sold_out"])
        self.assertEqual(options["payment_methods"], ["cash", "card", "upi"])
        nav_ids = [item["id"] for item in load_yaml(self.APP / "ui" / "navigation.yaml")]
        self.assertIn("pos", nav_ids)
        self.assertEqual(nav_ids[1], "pos")

    def test_existing_order_workflow_unchanged(self):
        flow = load_yaml(self.APP / "workflows" / "create-order.yaml")
        tools = [s.get("tool") for s in flow["steps"] if s.get("type") == "tool"]
        self.assertEqual(tools, ["entity.order.create"])
        self.assertEqual(flow["steps"][-1]["type"], "complete")
        self.assertNotIn("entity.invoice.create", tools)

    def test_one_venue_per_workspace_no_branch_model(self):
        manifest = load_yaml(self.APP / "manifest.yaml")
        self.assertNotIn("branch", manifest.get("entities") or [])
        self.assertFalse((self.APP / "entities" / "branch.yaml").exists())
        self.assertFalse((self.APP / "entities" / "location.yaml").exists())
        for name in ("table", "reservation", "order", "menu_item", "payment"):
            entity = self._entity(name)
            names = {f["name"] for f in entity["fields"]}
            self.assertNotIn("restaurant_id", names)
            self.assertNotIn("branch_id", names)
            self.assertNotIn("venue_id", names)
        table_location = self._field(self._entity("table"), "location")
        self.assertEqual(table_location["type"], "string")
        for path in self.APP.rglob("*.yaml"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("restaurant_id", text)
            self.assertNotRegex(text, r"\bbranch_id\b")

    def test_reservation_uses_generic_availability(self):
        reservation = self._entity("reservation")
        avail = reservation["availability"]
        self.assertEqual(avail["booking"]["datetime_field"], "reservation_at")
        self.assertEqual(avail["capacity"]["mode"], "exclusive")
        self.assertEqual(avail["capacity"]["resource"]["field"], "table_id")
        self.assertEqual(self._field(reservation, "table_id")["type"], "relation")
        self.assertEqual(self._field(reservation, "table_id")["ref_entity"], "table")
        flow = load_yaml(self.APP / "workflows" / "book-table.yaml")
        tools = [s.get("tool") for s in flow["steps"] if s.get("type") == "tool"]
        self.assertEqual(tools.count("entity.reservation.availability"), 3)
        self.assertIn("entity.reservation.create", tools)

    def test_whatsapp_flow_overlay_is_thin_and_generic(self):
        allowed = {
            "SIGN_UP",
            "SIGN_IN",
            "APPOINTMENT_BOOKING",
            "LEAD_GENERATION",
            "CONTACT_US",
            "CUSTOMER_SUPPORT",
            "SURVEY",
            "OTHER",
        }
        samples = [
            APPS / "restaurant-pro" / "workflows" / "book-table.yaml",
            APPS / "clinic-pro" / "workflows" / "book-appointment.yaml",
            APPS / "real-estate-pro" / "workflows" / "request-viewing.yaml",
        ]
        for path in samples:
            flow = load_yaml(path)
            overlay = flow.get("whatsapp_flow") or {}
            self.assertIn(overlay.get("category"), allowed)
            self.assertNotIn("tenant_id", overlay)
            self.assertNotIn("workspace_id", overlay)
            self.assertNotIn("access_token", overlay)
            self.assertNotIn("endpoint", overlay)
            self.assertNotIn("url", overlay)

    def test_payment_uses_relation_caps_and_person_inherit(self):
        payment = self._entity("payment")
        self.assertEqual(payment["relation_caps"][0]["relation"], "order_id")
        self.assertEqual(payment["relation_caps"][0]["parent_field"], "total_amount")
        self.assertEqual(self._field(payment, "person_id").get("inherit_from"), "order_id")
        self.assertTrue(self._field(payment, "order_id").get("required"))
        self.assertEqual(self._entity("order").get("concurrency"), "optimistic")


class CompatibilityContractTests(unittest.TestCase):
    """Every Marketplace App against the current metadata contract."""

    PLATFORM_REF = {"person"}

    def test_every_package_is_audited(self):
        names = {p.name for p in app_dirs()}
        self.assertGreaterEqual(len(names), 22)
        for required in (
            "appointment",
            "billing-pro",
            "calendly",
            "clinic-pro",
            "education",
            "field-service",
            "freshdesk",
            "google-calendar",
            "google-sheets",
            "http-catalog",
            "logistics",
            "project-tracker",
            "razorpay",
            "real-estate-pro",
            "restaurant-pro",
            "shopify",
            "slack",
            "stripe",
            "travel-agency-pro",
            "whatsapp-business",
            "woocommerce",
            "zoho-crm",
        ):
            self.assertIn(required, names)

    def test_no_agent_or_goal_metadata(self):
        for app in app_dirs():
            with self.subTest(app=app.name):
                text = (app / "manifest.yaml").read_text(encoding="utf-8")
                self.assertNotIn("\nagent:", text)
                manifest = load_yaml(app / "manifest.yaml")
                self.assertFalse(manifest.get("agent"))
                self.assertFalse(manifest.get("goal"))

    def test_entity_fields_are_canonical_lists(self):
        for app in app_dirs():
            entity_ids = {p.stem for p in (app / "entities").glob("*.yaml")}
            for path in sorted((app / "entities").glob("*.yaml")):
                with self.subTest(path=str(path.relative_to(ROOT))):
                    entity = load_yaml(path)
                    fields = entity.get("fields")
                    self.assertIsInstance(fields, list, f"{path} fields must be a list")
                    self.assertTrue(fields)
                    for field in fields:
                        self.assertIsInstance(field, dict)
                        self.assertIn(field["type"], KNOWN_FIELD_TYPES)
                        if field["type"] == "relation":
                            ref = field.get("ref_entity")
                            self.assertTrue(ref)
                            if ref not in self.PLATFORM_REF:
                                self.assertIn(
                                    ref,
                                    entity_ids,
                                    f"{path} relation {field['name']} refs missing entity {ref}",
                                )
                        if field["type"] == "person":
                            self.assertEqual(field.get("ref_entity", "person"), "person")
                    if entity.get("scope") == "customer":
                        self.assertTrue(any(f.get("type") == "person" for f in fields))

    def test_status_events_are_declared_on_the_manifest(self):
        for app in app_dirs():
            manifest = load_yaml(app / "manifest.yaml")
            declared = set(manifest.get("events") or [])
            for path in sorted((app / "entities").glob("*.yaml")):
                entity = load_yaml(path)
                events = entity.get("status_events") or {}
                date_events = entity.get("date_events") or []
                with self.subTest(path=str(path.relative_to(ROOT))):
                    for event in events.values():
                        self.assertIn(event, declared, f"{path} status event {event} missing from manifest")
                    for spec in date_events:
                        self.assertIn(spec["event"], declared)

    def test_flows_use_supported_triggers(self):
        allowed = {"conversation", "event", "schedule", "webhook"}
        for app in app_dirs():
            for path in sorted((app / "workflows").glob("*.yaml")):
                with self.subTest(path=str(path.relative_to(ROOT))):
                    flow = load_yaml(path)
                    trigger = flow.get("trigger") or {}
                    self.assertIn(trigger.get("type"), allowed)
                    if trigger.get("type") == "event":
                        self.assertTrue(trigger.get("event"))

    def test_restaurant_and_billing_remain_independent(self):
        restaurant = APPS / "restaurant-pro"
        billing = APPS / "billing-pro"
        r_manifest = load_yaml(restaurant / "manifest.yaml")
        b_manifest = load_yaml(billing / "manifest.yaml")
        self.assertNotEqual(r_manifest["id"], b_manifest["id"])
        self.assertNotIn("invoice", r_manifest.get("entities") or [])
        self.assertNotIn("menu_item", b_manifest.get("entities") or [])
        self.assertNotIn("payment_allocation", r_manifest.get("entities") or [])
        for path in restaurant.rglob("*.yaml"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("billing-pro", text)
            self.assertNotIn("invoice_item", text)
        for path in billing.rglob("*.yaml"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("restaurant-pro", text)
            self.assertNotIn("menu_item", text)
            self.assertNotIn("order_item", text)


class AppointmentAvailabilityTests(unittest.TestCase):
    APP = APPS / "appointment"

    def test_appointment_contract_is_structural_only(self):
        appointment = load_yaml(self.APP / "entities" / "appointment.yaml")
        avail = appointment["availability"]
        self.assertEqual(avail["booking"]["datetime_field"], "scheduled_at")
        self.assertEqual(avail["capacity"]["mode"], "exclusive")
        self.assertEqual(avail["capacity"]["resource"]["field"], "staff_id")
        for operating in ("timezone", "working_hours", "closed_days", "date_window_days", "blocking_statuses"):
            self.assertNotIn(operating, avail)

    def test_create_and_reschedule_use_availability_runtime(self):
        create = load_yaml(self.APP / "workflows" / "create-appointment.yaml")
        reschedule = load_yaml(self.APP / "workflows" / "reschedule-appointment.yaml")
        create_tools = [s.get("tool") for s in create["steps"] if s.get("type") == "tool"]
        reschedule_tools = [s.get("tool") for s in reschedule["steps"] if s.get("type") == "tool"]
        self.assertEqual(create_tools.count("entity.appointment.availability"), 3)
        self.assertEqual(reschedule_tools.count("entity.appointment.availability"), 3)

    def test_location_entity_and_flow_are_gone(self):
        manifest = load_yaml(self.APP / "manifest.yaml")
        self.assertNotIn("location", manifest["entities"])
        self.assertNotIn("create-location", manifest.get("flows") or [])
        self.assertFalse((self.APP / "entities" / "location.yaml").exists())
        self.assertFalse((self.APP / "workflows" / "create-location.yaml").exists())
        appointment = load_yaml(self.APP / "entities" / "appointment.yaml")
        self.assertFalse(any(f["name"] in {"location_id", "location"} for f in appointment["fields"]))
        nav = load_yaml(self.APP / "ui" / "navigation.yaml")
        pages = load_yaml(self.APP / "ui" / "pages.yaml")
        sources = load_yaml(self.APP / "ui" / "sources.yaml")
        self.assertNotIn("locations", [item["id"] for item in nav])
        self.assertNotIn("locations", [item["id"] for item in pages])
        self.assertNotIn("locations", [item["id"] for item in sources])
        for path in self.APP.rglob("*.yaml"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("create-location", text)
            self.assertNotIn("target: location", text)
            self.assertNotIn("entity: location", text)

    def test_customer_entity_and_flow_are_gone(self):
        manifest = load_yaml(self.APP / "manifest.yaml")
        self.assertNotIn("customer", manifest["entities"])
        self.assertNotIn("create-customer", manifest.get("flows") or [])
        self.assertNotIn("customer.created", manifest.get("events") or [])
        self.assertFalse((self.APP / "entities" / "customer.yaml").exists())
        self.assertFalse((self.APP / "workflows" / "create-customer.yaml").exists())
        appointment = load_yaml(self.APP / "entities" / "appointment.yaml")
        self.assertFalse(any(f["name"] in {"customer_id", "customer"} for f in appointment["fields"]))
        person = next(f for f in appointment["fields"] if f["name"] == "person_id")
        self.assertEqual(person["type"], "person")
        nav = load_yaml(self.APP / "ui" / "navigation.yaml")
        pages = load_yaml(self.APP / "ui" / "pages.yaml")
        sources = load_yaml(self.APP / "ui" / "sources.yaml")
        widgets = load_yaml(self.APP / "ui" / "widgets.yaml")
        self.assertNotIn("customers", [item["id"] for item in nav])
        self.assertNotIn("customers", [item["id"] for item in pages])
        self.assertNotIn("customers", [item["id"] for item in sources])
        self.assertNotIn("customer_form", [item["id"] for item in widgets])
        self.assertNotIn("customers_table", [item["id"] for item in widgets])
        for path in self.APP.rglob("*.yaml"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("create-customer", text)
            self.assertNotIn("entity.customer.", text)
            self.assertNotIn("target: customer", text)
            self.assertNotIn("entity: customer", text)
            self.assertNotIn("customer.created", text)
            self.assertNotIn("customer_id", text)


class ClinicProTests(unittest.TestCase):
    APP = APPS / "clinic-pro"

    def test_appointment_uses_generic_availability(self):
        appointment = load_yaml(self.APP / "entities" / "appointment.yaml")
        avail = appointment["availability"]
        self.assertEqual(avail["booking"]["datetime_field"], "scheduled_at")
        self.assertEqual(avail["capacity"]["resource"]["field"], "practitioner_id")
        self.assertEqual(
            next(f for f in appointment["fields"] if f["name"] == "practitioner_id")["type"],
            "relation",
        )
        flow = load_yaml(self.APP / "workflows" / "book-appointment.yaml")
        tools = [s.get("tool") for s in flow["steps"] if s.get("type") == "tool"]
        self.assertEqual(tools.count("entity.appointment.availability"), 3)
        self.assertNotIn("entity.invoice.create", tools)

    def test_invoice_uses_date_watch_not_custom_scheduler(self):
        invoice = load_yaml(self.APP / "entities" / "invoice.yaml")
        self.assertEqual(invoice["date_events"][0]["event"], "invoice.overdue")
        manifest = load_yaml(self.APP / "manifest.yaml")
        self.assertIn("invoice.overdue", manifest["events"])
        self.assertNotIn("agent", manifest)

    def test_patient_keeps_clinical_state_without_hub_identity_fields(self):
        patient = load_yaml(self.APP / "entities" / "patient.yaml")
        names = {f["name"] for f in patient["fields"]}
        self.assertEqual(patient["scope"], "customer")
        person = next(f for f in patient["fields"] if f["name"] == "person_id")
        self.assertEqual(person["type"], "person")
        self.assertTrue(person.get("required"))
        for clinical in ("date_of_birth", "blood_group", "emergency_contact"):
            self.assertIn(clinical, names)
        for identity in ("name", "email", "phone"):
            self.assertNotIn(identity, names)
        flow = load_yaml(self.APP / "workflows" / "create-patient.yaml")
        create = next(s for s in flow["steps"] if s.get("tool") == "entity.patient.create")
        mapped = create["input_map"]
        self.assertNotIn("name", mapped)
        self.assertNotIn("email", mapped)
        self.assertNotIn("phone", mapped)
        self.assertNotIn("person_id", mapped)
        for clinical in ("date_of_birth", "blood_group", "emergency_contact"):
            self.assertIn(clinical, mapped)

    def test_treatment_and_prescription_keep_visit_code_without_invented_fk(self):
        for name in ("treatment", "prescription"):
            entity = load_yaml(self.APP / "entities" / f"{name}.yaml")
            names = {f["name"] for f in entity["fields"]}
            self.assertIn("visit_code", names)
            self.assertNotIn("visit_id", names)
        visit = load_yaml(self.APP / "entities" / "visit.yaml")
        self.assertEqual(visit["id"], "visit")
        self.assertFalse(any(f["name"] == "vitals" for f in visit["fields"]))
        self.assertFalse((self.APP / "entities" / "vitals.yaml").exists())


class TravelAgencyProTests(unittest.TestCase):
    APP = APPS / "travel-agency-pro"

    def test_assigned_agent_targets_in_app_entity(self):
        booking = load_yaml(self.APP / "entities" / "booking.yaml")
        agent_field = next(f for f in booking["fields"] if f["name"] == "assigned_agent")
        self.assertEqual(agent_field["type"], "relation")
        self.assertEqual(agent_field["ref_entity"], "agent")
        self.assertTrue((self.APP / "entities" / "agent.yaml").exists())
        manifest = load_yaml(self.APP / "manifest.yaml")
        self.assertIn("agent", manifest["entities"])

    def test_totals_use_generic_computed_fields(self):
        booking = load_yaml(self.APP / "entities" / "booking.yaml")
        item = load_yaml(self.APP / "entities" / "booking_item.yaml")
        payment = load_yaml(self.APP / "entities" / "payment.yaml")
        self.assertEqual(booking["computed"][0]["op"], "relation_sum")
        self.assertEqual(item["computed"][0]["op"], "multiply")
        self.assertEqual(payment["relation_caps"][0]["relation"], "booking")

    def test_itinerary_and_booking_item_both_remain(self):
        manifest = load_yaml(self.APP / "manifest.yaml")
        self.assertIn("itinerary", manifest["entities"])
        self.assertIn("booking_item", manifest["entities"])
        self.assertTrue((self.APP / "entities" / "itinerary.yaml").exists())
        self.assertTrue((self.APP / "entities" / "booking_item.yaml").exists())
        itinerary = load_yaml(self.APP / "entities" / "itinerary.yaml")
        item = load_yaml(self.APP / "entities" / "booking_item.yaml")
        self.assertNotEqual(itinerary["id"], item["id"])
        self.assertIn("booking", [f["name"] for f in itinerary["fields"]])


class EducationStudentRemovalTests(unittest.TestCase):
    APP = APPS / "education"

    def test_student_entity_and_event_are_gone(self):
        manifest = load_yaml(self.APP / "manifest.yaml")
        self.assertNotIn("student", manifest["entities"])
        self.assertNotIn("student.created", manifest.get("events") or [])
        self.assertFalse((self.APP / "entities" / "student.yaml").exists())
        for path in self.APP.rglob("*.yaml"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("entity.student.", text)
            self.assertNotIn("target: student", text)
            self.assertNotIn("entity: student", text)
            self.assertNotIn("student.created", text)
            self.assertNotIn("student_id", text)

    def test_student_ui_is_gone(self):
        nav = load_yaml(self.APP / "ui" / "navigation.yaml")
        pages = load_yaml(self.APP / "ui" / "pages.yaml")
        sources = load_yaml(self.APP / "ui" / "sources.yaml")
        widgets = load_yaml(self.APP / "ui" / "widgets.yaml")
        self.assertNotIn("students", [item["id"] for item in nav])
        self.assertNotIn("students", [item["id"] for item in pages])
        self.assertNotIn("students", [item["id"] for item in sources])
        self.assertNotIn("students_table", [item["id"] for item in widgets])

    def test_enrollment_remains_person_scoped(self):
        enrollment = load_yaml(self.APP / "entities" / "enrollment.yaml")
        self.assertEqual(enrollment["id"], "enrollment")
        self.assertEqual(enrollment["scope"], "customer")
        person = next(f for f in enrollment["fields"] if f["name"] == "person_id")
        self.assertEqual(person["type"], "person")
        self.assertEqual(person.get("ref_entity"), "person")
        names = {f["name"] for f in enrollment["fields"]}
        self.assertNotIn("student_id", names)
        manifest = load_yaml(self.APP / "manifest.yaml")
        self.assertIn("enrollment", manifest["entities"])
        self.assertIn("enroll-student", manifest["flows"])

    def test_enroll_student_still_creates_enrollment(self):
        flow = load_yaml(self.APP / "workflows" / "enroll-student.yaml")
        tools = [s.get("tool") for s in flow["steps"] if s.get("type") == "tool"]
        self.assertIn("entity.enrollment.create", tools)
        self.assertNotIn("entity.student.create", tools)
        create = next(s for s in flow["steps"] if s.get("tool") == "entity.enrollment.create")
        self.assertNotIn("person_id", create["input_map"])
        self.assertNotIn("student_id", create["input_map"])

    def test_other_education_entities_remain(self):
        manifest = load_yaml(self.APP / "manifest.yaml")
        for name in ("course", "session", "assignment", "instructor"):
            self.assertIn(name, manifest["entities"])
            self.assertTrue((self.APP / "entities" / f"{name}.yaml").exists())
            entity = load_yaml(self.APP / "entities" / f"{name}.yaml")
            self.assertFalse(any(f["name"] == "student_id" for f in entity["fields"]))

    def test_no_student_runtime_branching_in_education_package(self):
        self.assertFalse(list(self.APP.glob("**/*.rs")))
        self.assertFalse((self.APP / "src").exists())
        for path in self.APP.rglob("*.yaml"):
            text = path.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"if\s+solution\s*==")
            self.assertNotRegex(text, r"if\s+entity\s*==")


class LogisticsUnresolvedRelationshipTests(unittest.TestCase):
    APP = APPS / "logistics"

    def test_keep_consignment_shipment_driver_warehouse(self):
        manifest = load_yaml(self.APP / "manifest.yaml")
        for entity in ("consignment", "shipment", "driver", "warehouse"):
            self.assertIn(entity, manifest["entities"])
            self.assertTrue((self.APP / "entities" / f"{entity}.yaml").exists())

    def test_no_speculative_shipment_relationships(self):
        shipment = load_yaml(self.APP / "entities" / "shipment.yaml")
        names = {f["name"] for f in shipment["fields"]}
        self.assertNotIn("consignment_id", names)
        self.assertNotIn("driver_id", names)
        self.assertNotIn("warehouse_id", names)
        for path in self.APP.rglob("*.yaml"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("consignment_id", text)
            self.assertNotIn("driver_id", text)
            self.assertNotIn("warehouse_id", text)

    def test_consignment_strips_duplicate_identity_name(self):
        consignment = load_yaml(self.APP / "entities" / "consignment.yaml")
        names = {f["name"] for f in consignment["fields"]}
        self.assertIn("reference", names)
        self.assertIn("weight", names)
        self.assertIn("person_id", names)
        self.assertNotIn("customer_name", names)
        person = next(f for f in consignment["fields"] if f["name"] == "person_id")
        self.assertEqual(person["type"], "person")
        flow = load_yaml(self.APP / "workflows" / "create-consignment.yaml")
        create = next(s for s in flow["steps"] if s.get("tool") == "entity.consignment.create")
        self.assertNotIn("customer_name", create["input_map"])
        self.assertNotIn("person_id", create["input_map"])


class FieldServiceCustomerRemovalTests(unittest.TestCase):
    APP = APPS / "field-service"

    def test_customer_entity_and_event_are_gone(self):
        manifest = load_yaml(self.APP / "manifest.yaml")
        self.assertNotIn("customer", manifest["entities"])
        self.assertNotIn("create-customer", manifest.get("flows") or [])
        self.assertNotIn("customer.created", manifest.get("events") or [])
        self.assertFalse((self.APP / "entities" / "customer.yaml").exists())
        self.assertFalse((self.APP / "workflows" / "create-customer.yaml").exists())
        for path in self.APP.rglob("*.yaml"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("entity.customer.", text)
            self.assertNotIn("target: customer", text)
            self.assertNotIn("entity: customer", text)
            self.assertNotIn("customer.created", text)
            self.assertNotIn("customer_id", text)

    def test_customer_ui_is_gone(self):
        nav = load_yaml(self.APP / "ui" / "navigation.yaml")
        pages = load_yaml(self.APP / "ui" / "pages.yaml")
        sources = load_yaml(self.APP / "ui" / "sources.yaml")
        widgets = load_yaml(self.APP / "ui" / "widgets.yaml")
        self.assertNotIn("customers", [item["id"] for item in nav])
        self.assertNotIn("customers", [item["id"] for item in pages])
        self.assertNotIn("customers", [item["id"] for item in sources])
        self.assertNotIn("customer_form", [item["id"] for item in widgets])
        self.assertNotIn("customers_table", [item["id"] for item in widgets])

    def test_work_order_remains_person_scoped(self):
        work_order = load_yaml(self.APP / "entities" / "work_order.yaml")
        self.assertEqual(work_order["id"], "work_order")
        self.assertEqual(work_order["scope"], "customer")
        person = next(f for f in work_order["fields"] if f["name"] == "person_id")
        self.assertEqual(person["type"], "person")
        self.assertEqual(person.get("ref_entity"), "person")
        names = {f["name"] for f in work_order["fields"]}
        self.assertNotIn("customer_id", names)
        manifest = load_yaml(self.APP / "manifest.yaml")
        self.assertIn("work_order", manifest["entities"])
        self.assertIn("create-work-order", manifest["flows"])

    def test_other_field_service_entities_remain(self):
        manifest = load_yaml(self.APP / "manifest.yaml")
        for name in ("site", "technician", "part", "service_category"):
            self.assertIn(name, manifest["entities"])
            self.assertTrue((self.APP / "entities" / f"{name}.yaml").exists())
            entity = load_yaml(self.APP / "entities" / f"{name}.yaml")
            self.assertFalse(any(f["name"] == "customer_id" for f in entity["fields"]))

    def test_no_customer_runtime_branching_in_field_service_package(self):
        self.assertFalse(list(self.APP.glob("**/*.rs")))
        self.assertFalse((self.APP / "src").exists())
        for path in self.APP.rglob("*.yaml"):
            text = path.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"if\s+solution\s*==")
            self.assertNotRegex(text, r"if\s+entity\s*==")


class MarketplaceArchitectureTests(unittest.TestCase):
    def test_no_app_specific_rust_or_solution_branching_in_packages(self):
        for app in app_dirs():
            with self.subTest(app=app.name):
                self.assertFalse(list(app.glob("**/*.rs")))
                self.assertFalse((app / "src").exists())
                for path in app.rglob("*.yaml"):
                    text = path.read_text(encoding="utf-8")
                    self.assertNotRegex(text, r"if\s+solution\s*==")
                    self.assertNotRegex(text, r"if\s+entity\s*==")


class CatalogOverlayContractTests(unittest.TestCase):
    """Entity `catalog:` overlays are metadata mappings, not runtime branches."""

    FORBIDDEN = {
        "access_token",
        "verify_token",
        "app_secret",
        "endpoint",
        "base_url",
        "tenant_id",
        "workspace_id",
        "installation_id",
        "person_id",
        "waba_id",
        "catalog_id",
        "meta_flow_id",
    }
    FIXTURES = Path(__file__).resolve().parent / "fixtures" / "catalog"

    def _assert_overlay(self, entity):
        overlay = entity.get("catalog") or {}
        self.assertTrue(overlay.get("enabled"))
        self.assertIn(overlay.get("type"), ("product", "service"))
        mapping = overlay.get("mapping") or {}
        self.assertTrue(mapping.get("title"))
        field_names = {f["name"] for f in entity.get("fields") or []}
        for source in mapping.values():
            self.assertIn(source, field_names)
        for key in overlay:
            self.assertNotIn(key, self.FORBIDDEN)

    def test_four_app_fixtures_share_the_same_overlay_shape(self):
        expected = {
            "listing": "service",
            "menu_item": "product",
            "care_service": "service",
            "job_service": "service",
        }
        for entity_id, catalog_type in expected.items():
            path = self.FIXTURES / f"{entity_id}.yaml"
            with self.subTest(entity=entity_id):
                entity = load_yaml(path)
                self.assertEqual(entity["id"], entity_id)
                self._assert_overlay(entity)
                self.assertEqual(entity["catalog"]["type"], catalog_type)

    def test_real_estate_property_uses_catalog_overlay(self):
        path = APPS / "real-estate-pro" / "entities" / "property.yaml"
        entity = load_yaml(path)
        self.assertEqual(entity["id"], "property")
        self._assert_overlay(entity)
        self.assertEqual(entity["catalog"]["type"], "service")
        self.assertEqual(entity["catalog"]["mapping"]["title"], "title")


class BillingProImageTests(unittest.TestCase):
    def test_product_uses_generic_image_field(self):
        product = load_yaml(APPS / "billing-pro" / "entities" / "product.yaml")
        image = next(f for f in product["fields"] if f["name"] == "image")
        self.assertEqual(image["type"], "image")


def _walk_forbidden_template_keys(node, path=""):
    found = []
    if isinstance(node, dict):
        for key, value in node.items():
            lowered = str(key).lower()
            if lowered in TEMPLATE_FORBIDDEN_KEYS:
                found.append(f"{path}.{key}" if path else key)
            found.extend(_walk_forbidden_template_keys(value, f"{path}.{key}" if path else key))
    elif isinstance(node, list):
        for i, value in enumerate(node):
            found.extend(_walk_forbidden_template_keys(value, f"{path}[{i}]"))
    elif isinstance(node, str):
        lowered = node.lower()
        if "://" in lowered or lowered.startswith("http:") or "javascript:" in lowered:
            found.append(path or "string")
    return found


def validate_automation_templates(manifest, entities_by_id):
    """Fail closed. Returns a list of error strings."""
    errors = []
    templates = manifest.get("automation_templates") or []
    if templates and not isinstance(templates, list):
        return ["automation_templates must be a list"]
    seen = set()
    declared_events = set(manifest.get("events") or [])
    for idx, tpl in enumerate(templates):
        tid = (tpl or {}).get("id") or ""
        if not tid:
            errors.append(f"automation_templates[{idx}] missing id")
            continue
        if tid in seen:
            errors.append(f"duplicate automation_templates id {tid}")
        seen.add(tid)
        extra = set((tpl or {}).keys()) - {"id", "name", "description", "trigger", "actions"}
        if extra:
            errors.append(f"{tid}: unknown fields {sorted(extra)}")
        event = ((tpl or {}).get("trigger") or {}).get("event")
        if not event:
            errors.append(f"{tid}: trigger.event required")
        elif event not in declared_events:
            errors.append(f"{tid}: event {event} is not declared")
        actions = (tpl or {}).get("actions") or []
        if not actions:
            errors.append(f"{tid}: actions required")
        for action in actions:
            forbidden = _walk_forbidden_template_keys(action)
            if forbidden:
                errors.append(f"{tid}: forbidden {forbidden}")
            atype = (action or {}).get("type")
            if atype not in CRM_AUTOMATION_ACTION_TYPES:
                errors.append(f"{tid}: unknown action type {atype}")
            if atype == "send_whatsapp":
                if any(k in (action or {}) for k in ("phone", "to", "from", "wa_id")):
                    errors.append(f"{tid}: send_whatsapp must not declare a recipient address")
                tpl = (action or {}).get("template")
                if tpl is not None and not re.fullmatch(r"[a-z0-9_]+", str(tpl)):
                    errors.append(f"{tid}: template must be a Meta template name")
            if atype == "send_webhook":
                if any(k in (action or {}) for k in ("url", "headers", "secret", "connection_id", "authorization")):
                    errors.append(f"{tid}: send_webhook must not declare destination/secrets")
                mapping = (action or {}).get("payload_mapping") or (action or {}).get("payload")
                if not mapping:
                    errors.append(f"{tid}: send_webhook requires payload_mapping")
                for row in mapping or []:
                    param = (row or {}).get("event_parameter") or ""
                    if param.startswith("contact.") or param.startswith("data."):
                        continue
                    if "." in param:
                        entity_id, field = param.split(".", 1)
                        if field in {"id", "code", "status", "name", "amount", "total", "total_amount"}:
                            continue
                        entity = entities_by_id.get(entity_id) or {}
                        names = {f["name"] for f in entity.get("fields") or []}
                        if field not in names:
                            errors.append(f"{tid}: unknown field {param}")
                        if field in {"person_id", "tenant_id", "workspace_id", "installation_id", "customer_id"}:
                            errors.append(f"{tid}: authority field {field}")
    return errors


class AutomationTemplateTests(unittest.TestCase):
    def test_installed_app_examples_are_valid(self):
        expected = {
            "billing-pro": {"overdue_invoice_reminder", "send_invoice_created_webhook"},
            "restaurant-pro": {"notify_team_order_created", "order_ready_whatsapp"},
            "real-estate-pro": {"follow_up_lead_created", "viewing_booked_whatsapp"},
            "clinic-pro": {"follow_up_patient_created", "appointment_booked_whatsapp"},
        }
        for app_id, ids in expected.items():
            app = APPS / app_id
            manifest = load_yaml(app / "manifest.yaml")
            entities = {
                p.stem: load_yaml(p) for p in (app / "entities").glob("*.yaml")
            }
            errors = validate_automation_templates(manifest, entities)
            self.assertEqual(errors, [], errors)
            got = {t["id"] for t in manifest.get("automation_templates") or []}
            self.assertEqual(got, ids)

    def test_rejects_secrets_and_urls(self):
        manifest = {
            "events": ["invoice.created"],
            "automation_templates": [
                {
                    "id": "bad",
                    "name": "Bad",
                    "trigger": {"event": "invoice.created"},
                    "actions": [
                        {
                            "type": "send_webhook",
                            "url": "https://evil.test/hook",
                            "secret": "shh",
                            "payload_mapping": [
                                {"output_key": "status", "event_parameter": "invoice.status"}
                            ],
                        }
                    ],
                }
            ],
        }
        errors = validate_automation_templates(manifest, {})
        self.assertTrue(errors)
        self.assertTrue(any("send_webhook" in e or "forbidden" in e or "url" in e.lower() for e in errors))

    def test_rejects_unknown_event_and_action(self):
        manifest = {
            "events": ["invoice.created"],
            "automation_templates": [
                {
                    "id": "bad",
                    "name": "Bad",
                    "trigger": {"event": "not.an.event"},
                    "actions": [{"type": "run_javascript", "code": "1+1"}],
                }
            ],
        }
        errors = validate_automation_templates(manifest, {})
        self.assertTrue(any("not.an.event" in e for e in errors))
        self.assertTrue(any("run_javascript" in e or "forbidden" in e for e in errors))

    def test_rejects_invalid_whatsapp_template_and_recipient(self):
        manifest = {
            "events": ["invoice.overdue"],
            "automation_templates": [
                {
                    "id": "bad_tpl",
                    "name": "Bad",
                    "trigger": {"event": "invoice.overdue"},
                    "actions": [
                        {
                            "type": "send_whatsapp",
                            "template": "Invoice Overdue!",
                            "phone": "+15551212",
                        }
                    ],
                }
            ],
        }
        errors = validate_automation_templates(manifest, {})
        self.assertTrue(any("Meta template name" in e for e in errors))
        self.assertTrue(any("recipient" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
