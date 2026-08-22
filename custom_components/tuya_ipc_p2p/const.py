"""Constants for tuya_ipc_p2p."""

from __future__ import annotations

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "tuya_ipc_p2p"
ATTRIBUTION = "Data provided by the Tuya cloud"
MANUFACTURER = "Tuya"
MODEL = "IPC camera (native P2P)"

CONF_KEEP_CONNECTED = "keep_connected"
CONF_MOTION_SENSITIVITY = "motion_sensitivity"

DEFAULT_SCAN_INTERVAL_SECONDS = 300
MIN_SCAN_INTERVAL_SECONDS = 60

# Holding the session open means video and snapshots are ready the instant they
# are asked for. The cost is that these cameras serve one client at a time, so
# while it is on the vendor app cannot connect to them.
DEFAULT_KEEP_CONNECTED = True

# How long an on-demand session stays up after the last viewer leaves, so a
# snapshot or a quick reconnect does not pay for a whole new session.
IDLE_SHUTDOWN_SECONDS = 60

# How long a snapshot waits for a cold session before answering with whatever
# the camera last produced. Callers give up long before a full cold start, so
# it is better to answer with a stale frame and let the session finish coming
# up behind it.
SNAPSHOT_WARMUP_SECONDS = 5

MJPEG_BOUNDARY = "tuyaipcp2pframe"
