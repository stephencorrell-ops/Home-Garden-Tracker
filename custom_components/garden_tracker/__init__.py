"""Garden Tracker: gardens, plant varieties, harvests, adjuncts, soil pH, sprays and degree days."""
from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_change
from homeassistant.helpers.typing import ConfigType

from . import websocket
from .const import CARD_URL, CONF_TEMP_ENTITY, DOMAIN, SIGNAL_STRUCTURE, SIGNAL_UPDATE
from .manager import GardenManager
from .services import async_register_services

PLATFORMS = [Platform.SENSOR, Platform.CLIMATE, Platform.BINARY_SENSOR]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    async_register_services(hass)
    websocket.async_register(hass)
    card = Path(__file__).parent / "www" / "garden-card.js"
    await hass.http.async_register_static_paths([StaticPathConfig(CARD_URL, str(card), False)])
    add_extra_js_url(hass, f"{CARD_URL}?v=0.31.3")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    mgr = GardenManager(hass)
    source = entry.options.get(CONF_TEMP_ENTITY, entry.data[CONF_TEMP_ENTITY])
    mgr.outdoor_entity = source
    mgr.home_lat = hass.config.latitude
    await mgr.async_load()
    hass.data[DOMAIN] = mgr

    @callback
    def _on_temp(event: Event) -> None:
        mgr.record_outdoor()

    entry.async_on_unload(async_track_state_change_event(hass, [source], _on_temp))
    mgr.record_outdoor()

    @callback
    def _midnight(now) -> None:
        async_dispatcher_send(hass, SIGNAL_UPDATE)

    entry.async_on_unload(async_track_time_change(hass, _midnight, hour=0, minute=0, second=10))

    @callback
    def _sync_devices() -> None:
        """Remove devices for plants that were archived or deleted, and for deleted gardens."""
        snap = mgr.snapshot()
        keep = {f"garden:{g['id']}" for g in snap["gardens"]}
        keep |= {f"variety:{v['id']}" for v in snap["varieties"] if not v["archived"]}
        reg = dr.async_get(hass)
        for dev in dr.async_entries_for_config_entry(reg, entry.entry_id):
            ids = {i[1] for i in dev.identifiers if i[0] == DOMAIN}
            if ids and not ids & keep:
                reg.async_remove_device(dev.id)

    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_STRUCTURE, _sync_devices))
    entry.async_on_unload(entry.add_update_listener(_reload))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _sync_devices()
    return True


async def _reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        mgr: GardenManager = hass.data.pop(DOMAIN)
        await mgr.async_shutdown()
    return ok
