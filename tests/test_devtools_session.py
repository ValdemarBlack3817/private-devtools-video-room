from src.devtools_session import SessionRequest, start_session
from src.infrai_client import InfraiClient


def test_http_error_preserves_response_envelope(monkeypatch) -> None:
    import io
    import json
    from urllib.error import HTTPError

    import pytest

    from src.infrai_client import InfraiError

    detail = {"code": "INSUFFICIENT_CREDIT", "message": "Insufficient credit", "balance": 0}

    def reject(request, timeout):
        raise HTTPError(request.full_url, 402, "Payment Required", {},
                        io.BytesIO(json.dumps({"ok": False, "error": detail}).encode()))

    monkeypatch.setattr("src.infrai_client.urlopen", reject)
    with pytest.raises(InfraiError) as caught:
        InfraiClient("test-key").create_room("case-42")

    assert caught.value.code == "INSUFFICIENT_CREDIT"
    assert caught.value.detail == detail
    assert caught.value.status == 402


def test_session_access_scopes_room_token_and_artefact() -> None:
    calls: list[tuple[str, str, dict]] = []

    def fake_transport(request, body):
        import json
        payload = json.loads(body)
        calls.append((request.method, request.full_url, payload))
        if request.full_url.endswith("/rtc/room/create"):
            return 200, {}, {"ok": True, "data": {"room": "case-42"}}
        if request.full_url.endswith("/rtc/token/issue"):
            return 200, {}, {"ok": True, "data": {"token": "scoped-token"}}
        return 200, {}, {"ok": True, "data": {"url": "https://upload.example/signed"}}

    request = SessionRequest("case-42", "engineer-7", "Healthtech engineer")
    result = start_session(request, InfraiClient("test-key", transport=fake_transport), "developer-sessions")

    assert result.room == "case-42"
    assert result.token == "scoped-token"
    assert result.artefact_key == "sessions/case-42/transcript.json"
    assert [call[0] for call in calls] == ["POST", "POST", "POST"]
    assert calls[1][2]["room"] == "case-42"
    assert calls[2][2]["op"] == "put"
