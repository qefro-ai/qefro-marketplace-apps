#!/usr/bin/env python3
"""Publish remaining runtime apps to solution-service."""
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

APPS_TO_PUBLISH = [
    "appointment-runtime",
    "logistics-runtime",
    "field-service-runtime",
    "education-runtime",
    "freshdesk-runtime",
    "woocommerce-runtime",
    "razorpay-runtime",
]


def load_yaml(p: Path):
    return yaml.safe_load(p.read_text())


def load_list_or_map(p: Path):
    if not p.exists():
        return []
    data = load_yaml(p)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [{"id": k, **v} if isinstance(v, dict) else {"id": k, "value": v} for k, v in data.items()]
    return []


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
        "entities": entities,
        "events": events,
        "ui": ui,
    }
    return manifest, components


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def package_checksum(manifest, components) -> str:
    root = {"manifest": manifest, "components": components}
    return hashlib.sha256(canonical_json(root).encode("utf-8")).hexdigest()


def load_private_key():
    with open(PRIVATE_KEY_HEX) as f:
        return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(f.read().strip()))


def sign(solution_id: str, version: str, checksum: str) -> str:
    private_key = load_private_key()
    message = f"{solution_id}|{version}|{checksum}".encode()
    return private_key.sign(message).hex()


def http_json(method: str, url: str, body, headers: dict) -> tuple[int, dict]:
    data = canonical_json(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


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
    status, data = http_json(
        "POST",
        f"{SOLUTION_SERVICE}/v1/solutions/publish",
        body,
        {"x-qefro-admin-id": PUBLISHER_ID, "Authorization": f"Bearer {os.environ.get('QEFRO_INTERNAL_BEARER')}"},
    )
    if status == 201:
        print(f"OK {app_id}: {data}")
    elif status == 409:
        print(f"SKIP {app_id} (already published)")
    else:
        print(f"FAILED {app_id}: {status} {data}")


if __name__ == "__main__":
    for app_id in APPS_TO_PUBLISH:
        publish_one(app_id)
