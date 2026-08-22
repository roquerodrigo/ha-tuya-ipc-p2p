# CLAUDE.md

Guidance for Claude Code (claude.ai/code) agents working in this repository.

Home Assistant integration for the **native P2P video** of Tuya IPC cameras. The
protocol itself lives in the companion SDK,
[`tuya-ipc-p2p-sdk`](https://github.com/roquerodrigo/tuya-ipc-p2p-sdk); this
repository is the Home Assistant side only — config entries, entities and the
lifecycle around them.

## Always read `CODE_STYLE.md` first

Before creating, renaming or restructuring any file/class/function, **read
[`CODE_STYLE.md`](./CODE_STYLE.md)**. It is the single source of truth for
conventions: language, file organisation, naming, typing, properties vs
`__init__`, imports, docstrings, comments, coordinator pattern, diagnostics
layout, translations, lint workflow.

For user-facing topics (entities, setup, options, troubleshooting), see
[`README.md`](./README.md).

## Verification workflow

**After every code change, always run lint then tests, in that order, before
declaring the task done.** Either run `scripts/lint` (a thin wrapper that only
chains the four commands) or run them directly:

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy custom_components/tuya_ipc_p2p
uv run pytest
```

`pytest` enforces a **90 % coverage gate**. Both gates mirror CI
(`.github/workflows/ci.yml`). Skip this only when the change literally cannot
affect lint or tests (e.g. README-only edits).

## Bumping the Home Assistant version

The Home Assistant version is pinned in two places and **must be updated
together**, otherwise CI, HACS and the test harness drift apart:

1. `pyproject.toml` `[dependency-groups] dev` — `homeassistant==<X.Y.Z>` **and**
   `pytest-homeassistant-custom-component==<matching release>` (the harness
   ships its own pinned `homeassistant`; the two pins must come from the same
   HA release, otherwise lint and tests resolve different cores).
2. `hacs.json` — `"homeassistant": "<X.Y.Z>"` (the minimum HACS enforces).

`tests/test_manifest.py` pins the `hacs.json` value to the tested release, so a
half-done bump fails the suite rather than CI.

## Bumping the SDK

`manifest.json` pins `tuya-ipc-p2p-sdk` **exactly**, and `pyproject.toml`'s dev
group pins the same version — `tests/test_manifest.py` keeps them honest, so CI
never runs green against a version users do not have. A fix that has to reach
Home Assistant travels SDK release first, bump pull request here second.

## Architecture

```
config_flow.py    validates the account, discovers its cameras, creates the entry
__init__.py       builds the client, the coordinator and one stream per camera
coordinator.py    polls the account's device list; refreshes names, availability, local keys
camera.py         one camera entity per camera: MJPEG, snapshots, stream source
stream_server.py  loopback H.264 for the ffmpeg consumers that cannot take MJPEG
binary_sensor.py  one motion sensor per camera
entity.py         the shared base: device info, availability, the stream accessor
api.py            the SDK boundary; nothing above it catches an SDK exception
```

### The video path does not go through the coordinator

The coordinator polls the *cloud*, not the camera. Video is pushed: each
`CameraStream` supervises its own session and calls the entities back through
`add_state_listener`. So a slow or failing poll never interrupts the video, and
the scan interval has nothing to do with the frame rate.

### One stream per camera, on `runtime_data`

`TuyaIpcP2pData.streams` holds one supervised stream per configured camera,
because the camera entity and its motion sensor read the same one. They are
stopped in `async_unload_entry` whether or not the platforms unload cleanly:
each holds a relay connection and a broker session, and a camera that is never
released refuses the next offer until its own timer fires.

### Discovery happens in the flow, not at setup

Discovery probes the IPC config API once per device on the account — one cloud
call each. That is too heavy for a restart, so the camera list is persisted on
the config entry and refreshed through the flow's reconfigure step. Reauth
deliberately does **not** rediscover: the cameras have not changed just because
the password did.

### Cameras serve one client at a time

While a session is up the vendor app cannot connect, and vice versa. That is
what the `keep_connected` option trades, and why the on-demand path releases the
session a minute after the last viewer leaves.

### The stream source has to be H.264, paced, and square-pixelled

The device only ever produces MJPEG. Home Assistant's own preview and snapshots
take that as it is, but everything reached through `stream_source` is a
separate ffmpeg process, and those consumers do not accept MJPEG: the HLS
playlist comes out as `CODECS="mp4v"`, which no browser decodes, and a HomeKit
accessory ends up with nothing to show. `stream_server.py` therefore encodes to
H.264 over MPEG-TS on a loopback port.

It feeds the encoder at a **fixed rate**, repeating the last frame when the
camera goes quiet. A JPEG sequence carries no timestamps, so an encoder given
frames as they happen invents a rate and stream time runs several times faster
than the clock — the picture plays back at a sprint and HomeKit rejects what it
did not negotiate.

It also forces **square pixels** (`-vf setsar=1`). The camera writes a JFIF
density of 640x480 in "aspect ratio" units, which decodes as a pixel aspect
ratio of 4:3, so a 640x480 frame claims a 16:9 display and every player
stretches it. Snapshots never show the fault — an `<img>` ignores the field —
so this only ever surfaces once the stream plays, which is what makes it easy
to reintroduce.

Nothing binds a port or spawns an encoder until `stream_source` is called, and
one encoder runs per consumer rather than one shared by all: at this
resolution and frame rate an encoder is cheap, and a late joiner gets a clean
start instead of the middle of someone else's stream.

### `camera_stream`, not `stream`

Home Assistant's `Camera` writes an attribute named `stream` for its own stream
worker. The base entity's accessor is `camera_stream` so a read-only property
does not shadow it — mypy catches the collision if this is ever renamed back.

### Entry typing

The `data/` package holds one TypedDict/dataclass per file. `data/__init__.py`
defines the `type` aliases — `TuyaIpcP2pConfigEntry`, `TuyaIpcP2pPayload`,
`JsonPrimitive`/`JsonValue`/`JsonObject` — and re-exports every symbol. State
lives on `entry.runtime_data` (auto-discarded on unload), never on `hass.data`.

Keys of a `TypedDict` must be written as literals, not through constants —
mypy rejects `data[CONF_EMAIL]`. The `CONF_*` constants in `const.py` are
therefore only the *option* keys, which are plain mappings.

### Diagnostics

`diagnostics.py` redacts the account **and every local key**, in the entry data
and in the coordinator payload alike: the local key encrypts the signaling and
derives the channel-0 credential, so it belongs in a dump no more than the
password does.
