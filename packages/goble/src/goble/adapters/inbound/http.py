"""Helpers compartidos por los adapters de entrada HTTP (API Gateway -> Lambda)."""

import json
from typing import Any


def response(status_code: int, body: Any) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body, default=str),
    }


def parse_body(event: dict[str, Any]) -> dict[str, Any]:
    body = event.get("body") or "{}"
    return json.loads(body) if isinstance(body, str) else body
