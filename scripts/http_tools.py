"""Shared HTTP tool builders for Marketplace metadata packages."""

from __future__ import annotations

import re
from typing import Any

from gen_lib import customer_identity, pagination, staff_access


def get_tool(
    tool_id: str,
    description: str,
    connection: str,
    path: str,
    *,
    items: str | None = None,
    item: str | None = None,
    query: dict[str, Any] | None = None,
    scopes: list[str] | None = None,
    staff: bool = True,
    customer: dict[str, Any] | None = None,
    both: bool = False,
    limit_param: str = "limit",
    paginate: bool | None = None,
    choice_id_prefix: str | None = None,
) -> dict[str, Any]:
    spec: dict[str, Any] = {
        "id": tool_id,
        "description": description,
        "connection": connection,
        "method": "GET",
        "path": path,
        "timeout_seconds": 15,
    }
    if query:
        spec["query"] = query
    path_params = [p for p in re.findall(r"\{([^{}]+)\}", path) if not p.startswith("person.")]
    use_pagination = paginate if paginate is not None else bool(items) and not path_params
    if use_pagination:
        spec["pagination"] = pagination(limit_param=limit_param)
    if items:
        spec["response"] = {"items": items}
        if choice_id_prefix:
            spec["response"]["choice_id_prefix"] = choice_id_prefix
    elif item:
        spec["response"] = {"item": item}
    if scopes:
        spec["required_scopes"] = scopes
    if customer:
        spec.update(customer)
    elif both:
        spec["access"] = {"surfaces": ["staff", "customer"]}
    elif staff:
        spec["access"] = staff_access()
    return spec


def write_tool(
    tool_id: str,
    description: str,
    connection: str,
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
    query: dict[str, Any] | None = None,
    scopes: list[str] | None = None,
    staff: bool = True,
) -> dict[str, Any]:
    spec: dict[str, Any] = {
        "id": tool_id,
        "description": description,
        "connection": connection,
        "method": method,
        "path": path,
        "timeout_seconds": 15,
    }
    if query:
        spec["query"] = query
    if body:
        spec["body"] = body
    if scopes:
        spec["required_scopes"] = scopes
    if staff:
        spec["access"] = staff_access()
    return spec


def owned_customer(
    paths: list[str],
    require_any: list[str] | None = None,
    also: list[dict[str, Any]] | None = None,
    collect: str | None = "email_otp",
) -> dict[str, Any]:
    return customer_identity(paths, require_any=require_any, also=also, collect=collect)
