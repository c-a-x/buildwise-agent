from __future__ import annotations

from fastapi import Request


def request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "REQ-local"))


def ok(data, request: Request, message: str = "success") -> dict[str, object]:
    return {"success": True, "message": message, "data": data, "request_id": request_id(request)}
