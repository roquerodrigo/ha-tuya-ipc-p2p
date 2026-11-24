# Tuya IPC P2P

<!-- ha-marketplace:exclude-start -->
[![CI](https://github.com/roquerodrigo/ha-tuya-ipc-p2p/actions/workflows/ci.yml/badge.svg)](https://github.com/roquerodrigo/ha-tuya-ipc-p2p/actions/workflows/ci.yml)
[![GitHub release](https://img.shields.io/github/v/release/roquerodrigo/ha-tuya-ipc-p2p)](https://github.com/roquerodrigo/ha-tuya-ipc-p2p/releases/latest)
[![Sponsor](https://img.shields.io/badge/Sponsor-%E2%9D%A4-db61a2?logo=githubsponsors&logoColor=white)](https://github.com/sponsors/roquerodrigo)

[![Open your Home Assistant instance and open a repository in the Marketplace.](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=roquerodrigo&repository=ha-tuya-ipc-p2p&category=integration)
<!-- ha-marketplace:exclude-end -->

Watch your Tuya and Smart Life cameras in Home Assistant, including the ones
the official Tuya integration cannot stream. Pet feeders and other low-cost
Tuya cameras often have no cloud RTSP link, so the official integration shows
no picture for them. This integration opens the same peer-to-peer video
session the Tuya app uses, and gives you live video, snapshots and a motion
sensor for each camera. The protocol lives in the companion library
[tuya-ipc-p2p-sdk](https://github.com/roquerodrigo/tuya-ipc-p2p-sdk).

This is an unofficial integration. It is not affiliated with or supported by
Tuya, and it uses the same cloud API and video protocol as the Tuya app, which
Tuya can change at any time.

## Features

- See live video and snapshots from every camera on your Tuya account, added
  automatically when you sign in.
- Get a motion sensor for each camera, even though these cameras report no
  motion of their own. Use it in automations, or to let HomeKit record.
- Add the cameras to HomeKit through the HomeKit Bridge, and play them in any
  dashboard card that uses Home Assistant's video stream.
- Choose between instant video and sharing the camera with the Tuya app.
- Get a repair notice when a camera stops answering and has to be unplugged.

## Requirements

- Home Assistant 2026.8.2 or newer.
- A Tuya or Smart Life account that signs in with an email and a password,
  with the cameras added to it.
- Internet access for Home Assistant. The account, the camera list and the
  video all go through Tuya's cloud.

<!-- ha-marketplace:exclude-start -->
## Installation

### Home Assistant Marketplace (recommended)

1. Select the **Open your Home Assistant instance** button above, or go to
   **Settings → Marketplace**, select **Add from link** in the upper right
   corner, enter `roquerodrigo/ha-tuya-ipc-p2p` and select **Add**.
2. Select **Install**.
3. Restart Home Assistant.

The Marketplace comes with Home Assistant 2026.11 and later. On older
versions, add this repository to HACS as a custom repository of type
**Integration** and install it from there.

### Manual

1. Download `tuya_ipc_p2p.zip` from the
   [latest release](https://github.com/roquerodrigo/ha-tuya-ipc-p2p/releases/latest).
2. Extract it into `config/custom_components/tuya_ipc_p2p/`.
3. Restart Home Assistant.
<!-- ha-marketplace:exclude-end -->

## Configuration

Go to **Settings → Devices & services → Add integration**, search for
**Tuya IPC P2P** and sign in with the account the cameras belong to.

| Field        | What to enter                                                                  | Default       |
|--------------|--------------------------------------------------------------------------------|---------------|
| Email        | The email you use to sign in to the Tuya or Smart Life app                     |               |
| Password     | The password of that account                                                   |               |
| Country code | The calling code of the account's country, without the plus sign: 1 for the US, 55 for Brazil |  |
| Region       | The Tuya data center of the account: United States, Europe, Western Europe, China or India | United States |

Home Assistant then checks every device on the account once and adds the ones
that answer as cameras. Setup fails if none of them does.

The camera list is kept, not checked again at every restart. When you add a
camera to the account or remove one, open the integration and select
**Reconfigure** to refresh the list. Reconfigure also lets you change the
password, country code or region, as long as you sign in to the same account.
After a camera leaves the list, you can delete its device from the device
page.

If Tuya stops accepting the stored password, Home Assistant asks you to sign
in again. Your cameras are kept.

## Options

Open the integration and select **Configure**. Changes apply right away.

| Option             | Default | Range                     | Effect |
|--------------------|---------|---------------------------|--------|
| Keep connected     | On      | On or off                 | Keeps each camera connected, so video and snapshots are ready instantly. While it is on, the Tuya app cannot connect to the cameras. |
| Motion sensitivity | 6       | 1 to 60, in steps of 0.5  | How much a frame has to stand out from a quiet scene to count as motion. Lower catches more and gives more false alarms. |
| Scan interval      | 300 s   | 60 s or more              | How often the account is checked for camera names, online state and new keys. It does not affect the video. |

These cameras accept one connection at a time. With **Keep connected** off, Home
Assistant connects when you open the camera and lets go of it a minute after
the last viewer leaves, so the Tuya app can use it again. The first snapshot
after an idle period shows the last picture the camera sent while it
reconnects, which takes several seconds.

## Entities

Each camera becomes a device with the name it has in the Tuya app.

| Entity      | Type          | Shows                  | Notes |
|-------------|---------------|------------------------|-------|
| Camera name | Camera        | Live video, snapshots  | Also offers a video stream for HomeKit and dashboard cards |
| Motion      | Binary sensor | Detected or Clear      | Stays on for 12 seconds after the last movement. Unavailable while the camera is not connected. |

Both entities are unavailable while the Tuya account reports the camera as
offline.

## How it works

Home Assistant signs in to your Tuya account and checks it at every scan
interval for the name and online state of each camera. When you re-pair a
camera, it gets a new key, and Home Assistant picks it up on the next check.
If Tuya's cloud stops answering for less than five minutes, your cameras keep
their last known state instead of turning unavailable.

The video does not depend on that check. Each camera sends its pictures
through Tuya's relay as soon as it is connected, and Home Assistant decrypts
them. The camera produces a sequence of JPEG pictures and no sound. For
HomeKit and for players that need H.264 video, Home Assistant converts the
pictures with its own ffmpeg, only while something is watching and only on an
address that other computers cannot reach.

When the connection drops, Home Assistant reconnects on its own, waiting a
little longer after each failed attempt.

The cameras report no motion, so the motion sensor reads it from the pictures.
A picture of a busy scene takes more space than a picture of a quiet one, so
the sensor compares the size of each picture with the one before. It learns
how much a quiet scene varies, following the camera from day into night, and
turns on when two pictures in a row stand out by more than **Motion
sensitivity** times that amount.

## Troubleshooting

**Sign-in fails with "The email, password, country code or region is wrong".**
Check that the country code has no plus sign and that the region is the one
your account was created in.

**Setup says no device on the account answers.** None of the devices on the
account answered as a camera this integration can stream. Check that you
signed in with the account the cameras belong to.

**A camera I added to the account does not appear.** The camera list is only
refreshed when you select **Reconfigure** on the integration.

**The camera is unavailable.** The Tuya account reports it as offline. Check
that it has power and Wi-Fi.

**The motion sensor is unavailable.** Motion is only known while the camera is
connected. With **Keep connected** off, that is only while someone is
watching it.

**The Tuya app cannot connect to the camera.** **Keep connected** is holding
the camera. Turn it off to share the camera with the app.

**The picture stops and comes back.** The connection dropped and Home
Assistant reconnected. A log line with `close_reason=12` means the camera
was still holding the previous connection, and a later attempt gets through.

**A repair says the camera needs to be power cycled.** After 10 refused
attempts in a row, these cameras stop answering anyone, the Tuya app included,
until they are unplugged. Unplug the camera for a few seconds and plug it back
in. Meanwhile Home Assistant only tries again every 15 minutes, and the notice
goes away once video returns.

**Motion triggers too often, or misses movement.** Raise **Motion
sensitivity** to get fewer false alarms, or lower it to catch more. The sensor
cannot tell a cat from the lights coming on.

**HomeKit does not offer recording.** HomeKit only records cameras that have a
motion sensor. In the HomeKit Bridge options for the camera, link it to the
camera's **Motion** sensor.

**Something else is wrong.** Download the diagnostics from the integration's
menu and attach them to an
[issue](https://github.com/roquerodrigo/ha-tuya-ipc-p2p/issues), along with
the log after you select **Enable debug logging** on the integration. The
email, password, country code and camera keys are removed from the
diagnostics.

## Known limitations

- A camera accepts one connection at a time, so Home Assistant and the Tuya
  app cannot use it at the same time.
- Video only, with no sound and no camera controls.
- The motion sensor reacts to any change in the picture, not only to people or
  animals.
- Tuya can change its cloud API or the video protocol at any time, which can
  break the integration until it is updated.

## Support

This integration is built and maintained on personal time, on hardware bought
for the purpose. If it is useful to you, consider
[sponsoring the work](https://github.com/sponsors/roquerodrigo). It keeps the
devices, the testing and the releases coming.

Report bugs and request features on the
[issue tracker](https://github.com/roquerodrigo/ha-tuya-ipc-p2p/issues).

<!-- ha-marketplace:exclude-start -->
## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development setup and
workflow, and [CODE_STYLE.md](CODE_STYLE.md) for the code conventions.

## License

[MIT](LICENSE)
<!-- ha-marketplace:exclude-end -->
