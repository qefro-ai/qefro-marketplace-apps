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
            "shopify-runtime",
            "restaurant-pro-runtime",
            "real-estate-runtime",
            "http-catalog-runtime",
        ):
            self.assertIn(required, names)


class NewAppCoverageTests(unittest.TestCase):
    EXPECTED = [
        "stripe-runtime",
        "razorpay-runtime",
        "woocommerce-runtime",
        "google-calendar-runtime",
        "google-sheets-runtime",
        "freshdesk-runtime",
        "zoho-crm-runtime",
        "whatsapp-business-runtime",
        "calendly-runtime",
        "slack-runtime",
        "appointment-runtime",
        "field-service-runtime",
        "education-runtime",
        "clinic-runtime",
        "logistics-runtime",
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
                if name not in {"google-sheets-runtime"}:
                    self.assertTrue((conn.get("webhooks") or {}).get("topics"))
                tools = [load_yaml(p) for p in (app / "tools").glob("*.yaml")]
                surfaces = {
                    s
                    for tool in tools
                    for s in (tool.get("access") or {}).get("surfaces") or []
                }
                self.assertIn("staff", surfaces)
                if name in {
                    "stripe-runtime",
                    "razorpay-runtime",
                    "woocommerce-runtime",
                    "freshdesk-runtime",
                    "calendly-runtime",
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


if __name__ == "__main__":
    unittest.main()
