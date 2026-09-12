#!/usr/bin/env python3
"""Publish clinic/restaurant/real-estate Pro Runtime packages to solution-service.

Usage:
  SOLUTION_SERVICE=http://127.0.0.1:8105 \\
  QEFRO_SIGNING_PRIVATE_HEX=/path/to/signing_private.hex \\
  python3 tmp/publish_pro_runtime_apps.py [--with-install]

Signing key defaults to /root/qefro-plugin-keys/signing_private.hex (server).
If SOLUTION_PUBLIC_KEY is empty on the server (dev), set QEFRO_PUBLISH_OPEN=true
or leave signature verification off.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
APPS = ROOT / "apps"
SOLUTION_SERVICE = os.environ.get("SOLUTION_SERVICE", "http://127.0.0.1:8105")
PRIVATE_KEY_HEX = os.environ.get(
    "QEFRO_SIGNING_PRIVATE_HEX", "/root/qefro-plugin-keys/signing_private.hex"
)
SIGNATURE_KID = os.environ.get("SIGNATURE_KID", "k1")
PUBLISHER_ID = os.environ.get("PUBLISHER_ID", "11111111-2222-3333-4444-555555555555")
TEST_TENANT = os.environ.get("TEST_TENANT", "440ce4dc-4422-425d-9419-b2a293131dc1")
TEST_ORG = os.environ.get("TEST_ORG", "41775b2c-e808-5c79-a255-eb07276a9136")
TEST_WORKSPACE = os.environ.get("TEST_WORKSPACE", "3733d4a7-e40c-4645-a256-856b2a653fd8")

APPS_TO_PUBLISH = [
    "clinic-pro-runtime",
    "restaurant-pro-runtime",
    "real-estate-pro-runtime",
    "travel-agency-pro-runtime",
]
OLD_TO_YANK = [
    "clinic-runtime",
    "real-estate-runtime",
    "clinic-pro",  # legacy SDK id if present
]


def load_yaml(path: Path):
    with path.open() as fh:
        return yaml.safe_load(fh)


def load_list_or_map(path: Path):
    if not path.exists():
        return []
    data = load_yaml(path)
    return data if data is not None else []


def canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def package_checksum(manifest, components) -> str:
    root = {"manifest": manifest, "components": components}
    return hashlib.sha256(canonical_json(root).encode("utf-8")).hexdigest()


def assemble(pkg: Path) -> tuple[dict, dict]:
    manifest = load_yaml(pkg / "manifest.yaml")
    workflows = []
    for flow in manifest.get("flows") or []:
        fid = flow if isinstance(flow, str) else flow["id"]
        workflows.append(load_yaml(pkg / "workflows" / f"{fid}.yaml"))
    entities = []
    for ent in manifest.get("entities") or []:
        eid = ent if isinstance(ent, str) else ent["id"]
        entities.append(load_yaml(pkg / "entities" / f"{eid}.yaml"))
    events = []
    for ev in manifest.get("events") or []:
        events.append(ev if isinstance(ev, str) else ev["name"])
    ui_dir = pkg / "ui"
    theme = load_yaml(ui_dir / "theme.yaml") if (ui_dir / "theme.yaml").exists() else {}
    navigation_layout = None
    if isinstance(theme, dict) and "navigation_layout" in theme:
        navigation_layout = theme.pop("navigation_layout")
    ui = {
        "name": (manifest.get("ui") or {}).get("name", manifest.get("name")),
        "logo": (manifest.get("ui") or {}).get("logo"),
        "icon": (manifest.get("ui") or {}).get("icon"),
        "theme": theme,
        "navigation_layout": navigation_layout,
        "navigation": load_list_or_map(ui_dir / "navigation.yaml"),
        "layouts": load_list_or_map(ui_dir / "layouts.yaml"),
        "pages": load_list_or_map(ui_dir / "pages.yaml"),
        "widgets": load_list_or_map(ui_dir / "widgets.yaml"),
        "sources": load_list_or_map(ui_dir / "sources.yaml"),
        "capabilities": manifest.get("capabilities") or [],
        "routes": [],
    }
    components = {
        "workflows": workflows,
        "prompts": [],
        "settings": {"settings": {}},
        "onboarding": [],
        "policies": [],
        "channels": {},
        "migrations": [],
        "ui": ui,
        "entities": entities,
        "events": events,
    }
    return manifest, components


def sign(solution_id: str, version: str, checksum: str) -> str:
    key_path = Path(PRIVATE_KEY_HEX)
    if not key_path.is_file():
        if os.environ.get("ALLOW_UNSIGNED") == "1":
            return "0" * 128
        raise FileNotFoundError(
            f"signing key not found: {key_path}. Set QEFRO_SIGNING_PRIVATE_HEX or ALLOW_UNSIGNED=1"
        )
    seed = bytes.fromhex(key_path.read_text().strip())
    sk = Ed25519PrivateKey.from_private_bytes(seed)
    msg = f"{solution_id}|{version}|{checksum}".encode()
    return sk.sign(msg).hex()


def http_json(method: str, url: str, body=None, headers=None, timeout=120):
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    bearer = os.environ.get("QEFRO_INTERNAL_BEARER", "").strip()
    if bearer:
        req.add_header("Authorization", f"Bearer {bearer}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            print(method, url, resp.status, raw[:800])
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print("FAILED", method, url, e.code, err[:1200])
        raise SystemExit(1)
    except urllib.error.URLError as e:
        print("UNREACHABLE", url, e)
        raise SystemExit(2)


def publish_one(app_id: str) -> None:
    pkg = APPS / app_id
    manifest, components = assemble(pkg)
    assert manifest["id"] == app_id, manifest["id"]
    checksum = package_checksum(manifest, components)
    signature = sign(manifest["id"], manifest["version"], checksum)
    print(f"==> publish {app_id}@{manifest['version']} checksum={checksum[:16]}…")
    body = {
        "manifest": manifest,
        "components": components,
        "checksum": checksum,
        "signature": signature,
        "signature_kid": SIGNATURE_KID,
        "publisher_id": PUBLISHER_ID,
    }
    try:
        http_json(
            "POST",
            f"{SOLUTION_SERVICE}/v1/solutions/publish",
            body,
            {"x-qefro-admin-id": PUBLISHER_ID},
        )
    except SystemExit as e:
        if e.code == 1:
            print(f"SKIP {app_id} (already published or conflict)")
            return
        raise


def yank(app_id: str) -> None:
    # Best-effort: list versions then set status yanked when API allows.
    print(f"==> yank attempt {app_id}")
    try:
        status, data = http_json(
            "GET",
            f"{SOLUTION_SERVICE}/v1/solutions/{app_id}/versions",
            None,
            {"x-qefro-admin-id": PUBLISHER_ID},
        )
    except SystemExit as e:
        if e.code == 2:
            raise
        print(f"skip yank {app_id} (not found or list failed)")
        return
    versions = data.get("items") or data.get("versions") or []
    for item in versions:
        ver = item.get("version") if isinstance(item, dict) else None
        if not ver:
            continue
        try:
            http_json(
                "POST",
                f"{SOLUTION_SERVICE}/v1/solutions/{app_id}/versions/{ver}/status",
                {"status": "yanked"},
                {"x-qefro-admin-id": PUBLISHER_ID},
            )
        except SystemExit:
            print(f"could not yank {app_id}@{ver}")


def install(app_id: str, version: str) -> None:
    http_json(
        "POST",
        f"{SOLUTION_SERVICE}/v1/tenant/solutions/install",
        {
            "solution_name": app_id,
            "version": version,
            "settings": {},
            "workspace_id": TEST_WORKSPACE,
        },
        {
            "x-qefro-tenant-id": TEST_TENANT,
            "x-qefro-organization-id": TEST_ORG,
            "x-qefro-workspace-id": TEST_WORKSPACE,
            "x-qefro-admin-id": PUBLISHER_ID,
        },
    )


if __name__ == "__main__":
    if "--yank-old" in sys.argv or "--all" in sys.argv:
        for old in OLD_TO_YANK:
            yank(old)
    for app_id in APPS_TO_PUBLISH:
        publish_one(app_id)
        if "--with-install" in sys.argv:
            ver = load_yaml(APPS / app_id / "manifest.yaml")["version"]
            install(app_id, ver)
    print("done")
