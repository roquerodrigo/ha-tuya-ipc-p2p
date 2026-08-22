from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.tuya_ipc_p2p.const import ATTRIBUTION, DOMAIN
from custom_components.tuya_ipc_p2p.entity import TuyaIpcP2pEntity
from tests.doubles import DEVICE_ID


def _entity(data=None) -> TuyaIpcP2pEntity:
    coordinator = MagicMock()
    coordinator.data = data
    coordinator.last_update_success = True
    return TuyaIpcP2pEntity(
        coordinator=coordinator, device_id=DEVICE_ID, fallback_name="Feeder"
    )


def test_attribution_and_entity_naming():
    entity = _entity()
    assert entity._attr_attribution == ATTRIBUTION
    assert entity._attr_has_entity_name is True
    assert entity.device_id == DEVICE_ID


def test_the_device_falls_back_to_the_configured_name_before_the_first_poll():
    info = _entity().device_info
    assert info["name"] == "Feeder"
    assert (DOMAIN, DEVICE_ID) in info["identifiers"]


def test_the_device_takes_the_name_the_poll_reports():
    entity = _entity({DEVICE_ID: {"name": "Renamed", "online": True, "local_key": "k"}})
    assert entity.device_info["name"] == "Renamed"


def test_an_entity_without_a_poll_yet_is_unavailable():
    assert _entity().available is False


def test_an_entity_whose_camera_is_missing_from_the_poll_is_unavailable():
    assert _entity({}).available is False


def test_an_online_camera_is_available():
    entity = _entity({DEVICE_ID: {"name": "Feeder", "online": True, "local_key": "k"}})
    assert entity.available is True


def test_an_offline_camera_is_unavailable():
    entity = _entity({DEVICE_ID: {"name": "Feeder", "online": False, "local_key": "k"}})
    assert entity.available is False


def test_the_stream_is_read_from_the_runtime_data():
    entity = _entity()
    entity.coordinator.config_entry.runtime_data.streams = {DEVICE_ID: "the-stream"}
    assert entity.camera_stream == "the-stream"
