"""Timer-switch: slå urstyringen af/på (vinterdrift = altid fra)."""
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN
from .const import LOGGER

DEVICE_INFO = lambda username: {
    "identifiers": {(DOMAIN, username)},
    "name": "Pillefyr",
    "manufacturer": "NBE / Stokercloud",
    "model": "Pillefyr (Blackstar/NBE via Stokercloud)",
}


async def async_setup_entry(hass, entry, add_entities):
    add_entities([PilleFyrTimerSwitch(hass)])


async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    """YAML-sti."""
    add_entities([PilleFyrTimerSwitch(hass)])


class PilleFyrTimerSwitch(CoordinatorEntity, SwitchEntity):
    _attr_name = "Pillefyr urstyring"
    _attr_unique_id = "pillefyr_timer_switch"
    _attr_icon = "mdi:clock-outline"

    def __init__(self, hass):
        super().__init__(hass.data[DOMAIN]["coordinator"])
        self._hass = hass
        self._attr_device_info = DEVICE_INFO(hass.data[DOMAIN].get("username", "stove"))

    @property
    def is_on(self):
        return (self.coordinator.data or {}).get("boiler.timer") == 1

    async def async_turn_on(self, **kwargs):
        await self._hass.data[DOMAIN]["api"].set_value("boiler.timer", 1)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        await self._hass.data[DOMAIN]["api"].set_value("boiler.timer", 0)
        await self.coordinator.async_request_refresh()
