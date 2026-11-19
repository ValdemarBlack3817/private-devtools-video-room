from __future__ import annotations

import json
import os
from dataclasses import dataclass

from .infrai_client import InfraiClient


@dataclass(frozen=True)
class SessionRequest:
    session_id: str
    identity: str
    display_name: str


@dataclass(frozen=True)
class ReleaseEvent:
    version: str
    status: str


@dataclass(frozen=True)
class SessionAccess:
    room: str
    token: str
    artefact_key: str
    upload_url: str


def start_session(request: SessionRequest, client: InfraiClient, bucket: str) -> SessionAccess:
    room = request.session_id
    client.create_room(room)
    token_data = client.issue_room_token(room, request.identity, request.display_name)
    artefact_key = f"sessions/{request.session_id}/transcript.json"
    presign_data = client.presign_object(bucket, artefact_key)
    return SessionAccess(room=room, token=token_data["token"], artefact_key=artefact_key, upload_url=presign_data["url"])


def publish_release(client: InfraiClient, request: SessionRequest, release: ReleaseEvent) -> None:
    client.publish_release(request.session_id, "release", json.dumps({"version": release.version, "status": release.status}), request.identity)


def main() -> None:
    client = InfraiClient.from_environment()
    request = SessionRequest(session_id=os.environ.get("DEVTOOLS_SESSION", "case-42"), identity="engineer-7", display_name="Healthtech engineer")
    access = start_session(request, client, os.environ.get("INFRAI_BUCKET", "developer-sessions"))
    print(json.dumps({"room": access.room, "token": access.token, "artefact_key": access.artefact_key, "upload_url": access.upload_url}))


if __name__ == "__main__":
    main()
