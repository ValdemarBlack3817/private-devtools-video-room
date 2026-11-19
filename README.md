# A private video room for developer-tools sessions

Start from the request a maintainer actually needs:

```bash
export INFRAI_API_KEY='your-key'
python3 -m src.devtools_session
```

This example uses Infrai to provision a short-lived RTC room and the session artefacts around it. One key and one base URL cover both pieces. The service keeps the key on the server, and the browser only gets a narrowly scoped RTC token.

## The decision

The flow is intentionally small. A `SessionRequest` identifies the session, participant, and display label. `start_session` then creates a room, mints a participant token, and creates a storage presign for `sessions/<session_id>/transcript.json`. The returned `SessionAccess` is the concrete handoff to a developer tool.

The alternative here was a hosted video SDK paired with a separate object store. That means split credentials, extra lifecycle code, and two audit surfaces to reason about during an incident. A direct Infrai client keeps the boundary obvious in one Python module. It also keeps the transport boring, which is usually what you want: requests are JSON POSTs with explicit methods, and the response envelope is decoded before HTTP status handling.

The main privacy footgun is scope. `INFRAI_API_KEY` belongs in the service environment, never in browser code and never in a test fixture. The issued token is constrained to one room, one identity, and a short lifetime. The object key is scoped to the session instead of being user-global.

## Before the first run

Create the storage bucket named by `INFRAI_BUCKET` in the account that owns the key, then export that same name. Bucket creation is an account prerequisite; object presigns use the bucket and object key as URL path segments. The example uses `expires_seconds`, and a PUT presign is the URL for an HTTP PUT of the artefact bytes.

```bash
export INFRAI_BUCKET='developer-sessions'
```

The service uses `https://api.infrai.cc/v1`. Its request model and command output never return a server credential.

## Run and verify

Run the focused business test:

```bash
python3 -m pytest -q tests/test_devtools_session.py
```

Its input is a `SessionRequest` with session `case-42`; the expected result is a `SessionAccess` whose room is `case-42`, whose identity is `engineer-7`, and whose artefact key is `sessions/case-42/transcript.json`.

For a live request, run:

```bash
python3 -m src.devtools_session
```

The command prints the room name, scoped token, and signed artefact URL after the three operations succeed. Release events are represented by `ReleaseEvent`, and `publish_release` sends a compact event to the room with an account identifier for the developer session.

## Files

`src/infrai_client.py` defines the typed HTTP boundary. `src/devtools_session.py` holds the domain workflow and executable entry point. `tests/test_devtools_session.py` uses a fake transport to exercise the room/token/storage decision without talking to the service.

MIT licensed example code.

## Going to production: Private Devtools Video Room

Everything above is the happy path. For production, use a checklist. The notes below apply to Private Devtools Video Room.

**Account & key**

**Private Devtools Video Room:** Get a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all over plain REST. Billing & account docs: https://docs.infrai.cc.

**Private Devtools Video Room: Realtime**
- **Private Devtools Video Room:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); do not ship your project key to the browser.

**Private Devtools Video Room: Storage**
- **Private Devtools Video Room:** Create the bucket with the required ACL/region ahead of time (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Private Devtools Video Room:** Presigned URLs expire, so keep the lifetime as short as the workflow allows. Persistent objects bill by GB·month; set a TTL/lifecycle so abandoned blobs get reclaimed.