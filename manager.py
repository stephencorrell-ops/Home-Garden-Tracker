"""Home Assistant wrapper around the pure garden model."""
from __future__ import annotations

import json
from pathlib import Path

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import SIGNAL_STRUCTURE, SIGNAL_UPDATE, STORAGE_KEY, STORAGE_VERSION
from .model import GardenModel


class GardenManager(GardenModel):
    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__({}, lambda: dt_util.now().date(), self._on_change, self._on_structure)
        self.hass = hass
        self._store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._ph_unsub = None
        self._ready = False

    async def async_load(self) -> None:
        self.load(await self._store.async_load())
        path = Path(__file__).parent / "species.json"
        text = await self.hass.async_add_executor_job(path.read_text, "utf-8")
        self.presets = {k: v for k, v in json.loads(text).items() if not k.startswith("_")}
        self._ready = True
        self.refresh_ph_listeners()

    async def async_shutdown(self) -> None:
        if self._ph_unsub:
            self._ph_unsub()
            self._ph_unsub = None
        await self._store.async_save(self.data)

    # ---- model callbacks ------------------------------------------------------
    def _on_change(self) -> None:
        if not self._ready:
            return
        self._store.async_delay_save(lambda: self.data, 5)
        async_dispatcher_send(self.hass, SIGNAL_UPDATE)

    def _on_structure(self) -> None:
        if not self._ready:
            return
        self.refresh_ph_listeners()
        async_dispatcher_send(self.hass, SIGNAL_STRUCTURE)

    # ---- soil pH sensors -------------------------------------------------------
    def refresh_ph_listeners(self) -> None:
        if self._ph_unsub:
            self._ph_unsub()
            self._ph_unsub = None
        by_entity: dict[str, list[str]] = {}
        for g in self.data["gardens"].values():
            if g.get("ph_entity"):
                by_entity.setdefault(g["ph_entity"], []).append(g["id"])
        if not by_entity:
            return

        @callback
        def _changed(event) -> None:
            for gid in by_entity.get(event.data["entity_id"], []):
                self._ingest_ph(gid, event.data.get("new_state"))

        self._ph_unsub = async_track_state_change_event(self.hass, list(by_entity), _changed)
        for ent, gids in by_entity.items():
            for gid in gids:
                self._ingest_ph(gid, self.hass.states.get(ent))

    def _ingest_ph(self, gid: str, state) -> None:
        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return
        try:
            self.record_sensor_ph(gid, float(state.state))
        except ValueError:
            return
