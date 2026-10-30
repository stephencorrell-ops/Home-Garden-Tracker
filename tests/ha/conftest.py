"""Runs the integration inside a real Home Assistant test instance. Run from the repo root:
    pip install -r tests/ha/requirements.txt && python -m pytest -c tests/ha/pytest.ini tests/ha

This folder has no __init__.py on purpose, so the plain unittest run of the core tests leaves it out."""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import custom_components.garden_tracker  # noqa: E402,F401
import custom_components.garden_tracker.websocket  # noqa: E402,F401
from pytest_homeassistant_custom_component.common import MockConfigEntry  # noqa: E402

pytest_plugins = ["pytest_homeassistant_custom_component"]
DOMAIN = "garden_tracker"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
async def entry(hass):
    """Garden Tracker set up with sensor.out as the outdoor temperature. The card file and its websocket need the
    frontend, which the test instance doesn't have, so those two are stubbed."""
    for c in ("frontend", "http", "websocket_api", "recorder"):
        hass.config.components.add(c)
    hass.http = MagicMock(async_register_static_paths=AsyncMock())
    hass.states.async_set("sensor.out", "50", {"unit_of_measurement": "°F"})
    e = MockConfigEntry(domain=DOMAIN, data={"temperature_entity": "sensor.out"}, unique_id=DOMAIN)
    e.add_to_hass(hass)
    with patch("custom_components.garden_tracker.add_extra_js_url"), \
         patch("custom_components.garden_tracker.websocket.async_register"):
        assert await hass.config_entries.async_setup(e.entry_id)
        await hass.async_block_till_done()
    return e


@pytest.fixture
def call(hass):
    async def _call(service, **data):
        await hass.services.async_call(DOMAIN, service, data, blocking=True)
        await hass.async_block_till_done()
    return _call
