# Tuya IPC P2P

[![CI](https://github.com/roquerodrigo/ha-tuya-ipc-p2p/actions/workflows/ci.yml/badge.svg)](https://github.com/roquerodrigo/ha-tuya-ipc-p2p/actions/workflows/ci.yml)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

[![Open your Home Assistant instance and open the repository inside HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=roquerodrigo&repository=ha-tuya-ipc-p2p&category=integration)

---

Home Assistant integration for the **native P2P video** of Tuya IPC cameras — the
path the vendor app uses, spoken directly. No vendor SDK, no external process
and no cloud RTSP: Home Assistant logs in, negotiates the session, decrypts the
media and gets MJPEG video and JPEG snapshots.

The official Tuya integration streams these cameras over a cloud RTSP link,
which several devices — pet feeders and other low-cost IPC hardware among
them — do not offer. This integration speaks the P2P protocol those devices
*do* answer.

> ⚠️ **Unofficial.** Not affiliated with, endorsed by or supported by Tuya. It
> targets the mobile API gateway and the P2P protocol their app uses; the
> vendor can change either side at any time.

## Entities

One device per camera, each with:

| Entity | Platform | What it is |
|---|---|---|
| Camera | `camera` | Live video and JPEG snapshots, straight from the device |
| Motion | `binary_sensor` | Motion derived from the frames the camera already sends |

## Install

Through [HACS](https://hacs.xyz/): add this repository as a custom repository
of category **Integration**, install it, and restart Home Assistant. Then add
**Tuya IPC P2P** from **Settings → Devices & services**.

## Configure

The flow asks for the account the cameras belong to:

| Field | What to enter |
|---|---|
| Email | The Tuya / Smart Life account email |
| Password | Its password |
| Country code | The calling code of the account's country, without a plus sign — `1` for the US, `55` for Brazil |
| Region | The Tuya data centre the account lives in (`us` by default) |

Every device on the account is then probed once, and the ones that answer the
IPC config API are imported as cameras. Nothing has to be copied out of the app
by hand: the device ids and local keys come from the account.

The camera list is stored on the config entry rather than rediscovered on every
restart, because the probe is one cloud call per device on the account. When a
camera is added or removed, run **Reconfigure** from the integration's
three-dot menu to refresh it.

## Options

| Option | Default | What it does |
|---|---|---|
| Keep connected | on | Holds the camera session open so video and snapshots are ready instantly |
| Motion sensitivity | 6 | How far above typical a frame has to land to count as motion |
| Scan interval | 300 s | How often the account is polled for camera names, availability and rotated local keys |

**Cameras serve one client at a time.** While this integration holds a session
the vendor app cannot connect to that camera, and while the app holds it the
integration cannot. That is what **Keep connected** trades: with it on, video is
ready the instant it is asked for; with it off, the session comes up on demand
and is released a minute after the last viewer leaves, so the Tuya app can have
the camera back.

Bringing a cold session up takes several seconds — login, signaling, relay, the
channel-0 handshake — so with **Keep connected** off the first snapshot after an
idle period answers with the last frame the camera produced while the session
comes up behind it.

The scan interval does not affect the video, which the camera pushes.

## Motion

These cameras report no motion of their own. A JPEG is only as large as its
content is complex, so how much each frame differs in size from the one before
it is a direct measure of how much the scene changed — and it costs nothing,
because the frames arrive either way.

Measured against a still scene on real hardware, consecutive frames differ by
0.2 % in daylight and 0.41 % at night, where sensor noise is higher. The typical
difference is tracked continuously rather than fixed, so the threshold follows
the camera from day into night, and **Motion sensitivity** sets how far above
typical a frame has to land. Two frames in a row have to exceed it: anything
really moving stays in shot longer than one frame, while the camera's own
exposure adjustments show up as a single frame that differs sharply from both
its neighbours.

It cannot tell a cat from the lights coming on. On a still scene at night — the
noisiest case — the default settles at about one event every ten minutes; raise
the sensitivity if that is too eager.

Motion is read from the frames a session delivers, so the sensor is unavailable
while the camera is not connected. With **Keep connected** on, that is only
while the camera itself is unreachable.

## How it works

The protocol lives in the companion SDK,
[`tuya-ipc-p2p-sdk`](https://github.com/roquerodrigo/tuya-ipc-p2p-sdk), which
this integration pins exactly in `manifest.json`. In short: a signed, encrypted
call to the mobile gateway logs in and returns a server-coordinated P2P session;
an SDP offer/answer is exchanged over MQTT; media then flows over a TCP relay
that multiplexes KCP conversations, decrypting into JPEG frames.

Home Assistant is handed those frames directly, and the camera entity serves
them two ways. Its own preview and snapshots are the JPEGs as they arrive, with
none of the analysis an RTSP source has to go through first. Everything built
on ffmpeg — Home Assistant's HLS pipeline, the HomeKit bridges — gets a
loopback URL instead, where the frames are encoded to H.264 on the fly.

That transcode is not optional. These cameras only ever produce MJPEG, and
handing MJPEG to those consumers produces an HLS playlist advertising
`CODECS="mp4v"` that no browser decodes, and a HomeKit accessory with nothing
to show. The loopback server also feeds the encoder at a fixed rate, repeating
the last frame when the camera goes quiet: a JPEG sequence carries no
timestamps, so without a declared rate the encoder invents one and playback
runs several times faster than the clock.

One encoder runs per connected consumer, and nothing is spawned — nor is any
port bound — until something actually asks for a stream. At 640×480 and a
couple of frames a second that costs very little.

## HomeKit

The camera publishes an H.264 stream source, so it can be added to HomeKit
through Home Assistant's own HomeKit Bridge or any integration that builds on
`stream`. Pair the motion sensor with it: HomeKit only offers **recording** for
a camera that reports motion, and these cameras report none of their own — the
`binary_sensor` this integration creates is what fills that gap.

## Troubleshooting

- **No camera found during setup.** Only devices that answer the IPC config API
  are imported. A camera the Tuya app streams over cloud RTSP rather than P2P
  will not appear.
- **The camera is unavailable.** The account reports it offline. Nothing this
  integration does can bring a session up against hardware that is not on the
  network.
- **The Tuya app cannot connect.** That is **Keep connected** holding the
  session. Turn it off to share the camera.
- **The picture stops and comes back.** Sessions end on transport close, a
  device disconnect or a stall; the SDK refetches a fresh config and starts
  over with a backoff. A `close_reason=12` in the log is the device saying it
  still holds the previous session; the next attempt gets it.
- **HomeKit will not record.** HomeKit only offers recording for a camera that
  reports motion — point the bridge at this integration's motion sensor.

Attach the integration's diagnostics dump to any issue — it carries the entry,
what the last poll saw and what each stream is doing, with the account and every
local key redacted.

## Development

```bash
scripts/setup      # create the .venv
scripts/develop    # run Home Assistant with the integration loaded
scripts/lint       # ruff format, ruff check, mypy, pytest
```

Conventions live in [`CODE_STYLE.md`](./CODE_STYLE.md); architectural notes for
agents in [`CLAUDE.md`](./CLAUDE.md).

## License

MIT — see [`LICENSE`](./LICENSE).
