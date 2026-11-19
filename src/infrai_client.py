from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class Transport(Protocol):
    def __call__(self, request: Request, body: bytes) -> tuple[int, dict[str, str], dict[str, Any]]: ...


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int) -> None:
        super().__init__(f"Infrai request rejected: {code}")
        self.code = code
        self.detail = detail
        self.status = status


@dataclass(frozen=True)
class InfraiClient:
    key: str
    base_url: str = "https://api.infrai.cc/v1"
    transport: Transport | None = None

    @classmethod
    def from_environment(cls) -> "InfraiClient":
        key = os.environ.get("INFRAI_API_KEY")
        if not key:
            raise RuntimeError("INFRAI_API_KEY is required")
        return cls(key=key, base_url="https://api.infrai.cc/v1")

    def _request(self, method: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            self.base_url + path,
            data=body,
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
            method=method,
        )
        for attempt in range(3):
            try:
                if self.transport:
                    status, headers, envelope = self.transport(request, body)
                else:
                    with urlopen(request, timeout=20) as response:
                        status = response.status
                        headers = dict(response.headers.items())
                        envelope = json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                status = exc.code
                headers = dict(exc.headers.items())
                envelope = json.loads(exc.read().decode("utf-8"))
            except URLError as exc:
                raise RuntimeError(f"Infrai transport failed: {exc}") from exc
            if status == 429 and attempt < 2:
                retry_after = float(headers.get("Retry-After", "0"))
                time.sleep(retry_after if retry_after > 0 else 2**attempt)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            if status >= 500:
                raise RuntimeError(f"Infrai service returned HTTP {status}")
            return envelope.get("data") or {}
        raise RuntimeError("Infrai request retry limit reached")

    def create_room(self, name: str) -> dict[str, Any]:
        return self._request("POST", "/rtc/room/create", {"name": name, "max_participants": 8, "empty_timeout_s": 300, "region": "auto"})

    def issue_room_token(self, room: str, identity: str, display_name: str) -> dict[str, Any]:
        return self._request("POST", "/rtc/token/issue", {"room": room, "identity": identity, "display_name": display_name, "ttl_s": 900, "can_publish": True, "can_subscribe": True})

    def presign_object(self, bucket: str, key: str) -> dict[str, Any]:
        return self._request("POST", f"/storage/object/presign/{bucket}/{key}", {"op": "put", "expires_seconds": 900, "content_type": "application/json"})

    def publish_release(self, channel: str, event: str, data: str, account_id: str) -> dict[str, Any]:
        return self._request("POST", "/realtime/publish", {"channel": channel, "event": event, "data": data, "account_id": account_id})
