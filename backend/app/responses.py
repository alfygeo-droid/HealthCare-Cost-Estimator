from __future__ import annotations


def ok(data=None, warnings=None, assumptions=None, **extra):
    payload = {
        "success": True,
        "data": data if data is not None else {},
        "warnings": warnings or [],
        "assumptions": assumptions or [],
    }
    payload.update(extra)
    return payload


def fail(message: str, warnings=None, status: int = 400):
    body = {
        "success": False,
        "data": {},
        "warnings": warnings or [message],
        "assumptions": [],
        "error": message,
    }
    return body, status
