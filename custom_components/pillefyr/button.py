"""Knapper: start, stop, nulstil alarm."""
import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import do_start, do_stop
from .const import DOMAIN, LOGGER
from .switch import DEVICE_INFO


async def async_setup_entry(hass, entry, add_entities):
    add_entities([
        PilleFyrStartButton(hass),
        PilleFyrStopButton(hass),
        PilleFyrAlarmButton(hass),
    ])


async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    """YAML-sti."""
    add_entities([
        PilleFyrStartButton(hass),
        PilleFyrStopButton(hass),
        PilleFyrAlarmButton(hass),
    ])


class _PilleFyrButton(CoordinatorEntity, ButtonEntity):
    def __init__(self, hass, unique_id, name, icon):
        super().__init__(hass.data[DOMAIN]["coordinator"])
        self._hass = hass
        self._attr_unique_id = unique_id
        self._attr_name = name
        self._attr_icon = icon
        self._attr_device_info = DEVICE_INFO(hass.data[DOMAIN].get("username", "stove"))

    async def async_press(self):
        raise NotImplementedError


class PilleFyrStartButton(_PilleFyrButton):
    """Tænder fyret under timeren (samme semantik som pillefyr.start)."""

    def __init__(self, hass):
        super().__init__(hass, "pillefyr_btn_start", "Pillefyr tænd", "mdi:fire")

    async def async_press(self):
        await do_start(self._hass)


class PilleFyrStopButton(_PilleFyrButton):
    """Hård sluk + evt. timer-restore (samme semantik som pillefyr.stop)."""

    def __init__(self, hass):
        super().__init__(hass, "pillefyr_btn_stop", "Pillefyr sluk", "mdi:fire-extinguisher")

    async def async_press(self):
        await do_stop(self._hass)


class PilleFyrAlarmButton(_PilleFyrButton):
    def __init__(self, hass):
        super().__init__(hass, "pillefyr_btn_alarm", "Pillefyr nulstil alarm", "mdi:alarm-check")

    async def async_press(self):
        await self._hass.data[DOMAIN]["api"].set_value("misc.reset_alarm", 1)
        await self.coordinator.async_request_refresh()
