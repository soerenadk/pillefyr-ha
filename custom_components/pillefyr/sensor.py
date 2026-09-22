"""Sensore for pillefyret — platform: pillefyr i configuration.yaml."""
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN

LOGGER = logging.getLogger(__name__)

# de vigtigste værdier får egne entiteter; resten lander som attributter
MAIN = [
    ("advanced.actual_boiler_temp", "Pillefyr temperatur", "°C", "temperature"),
    ("advanced.boiler_setpoint", "Pillefyr setpunkt", "°C", "temperature"),
    ("advanced.boiler_diff", "Pillefyr diff", "°C", None),
    ("boiler.temp", "Pillefyr boiler setpunkt", "°C", None),
    ("misc.wifi_network_status", "Pillefyr netværk", None, None),
    ("vacuum.output_auger", "Pillefyr snegle", "%", None),
    ("vacuum.output_vacuum", "Pillefyr vacuum", "%", None),
    ("misc.dl_version", "Pillefyr firmware", None, None),
]


async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    coordinator = hass.data[DOMAIN]["coordinator"]

    class PilleFyrSensor(CoordinatorEntity, SensorEntity):
        def __init__(self, key, name, unit, dev_class):
            super().__init__(coordinator)
            self._key = key
            self._attr_name = name
            self._attr_unique_id = f"pillefyr_{key.replace('.', '_')}"
            self._attr_native_unit_of_measurement = unit
            self._attr_device_class = dev_class

        @property
        def native_value(self):
            return self._state_value()

        def _state_value(self):
            return (self.coordinator.data or {}).get(self._key)

        @property
        def extra_state_attributes(self):
            return {k: v for k, v in (self.coordinator.data or {}).items()
                    if k != self._key}

    class PilleFyrTilstand(CoordinatorEntity, SensorEntity):
        """Afledt tilstand: I drift / Tænder op / Stoppet af ur / Off."""
        _attr_name = "Pillefyr tilstand"
        _attr_unique_id = "pillefyr_tilstand"

        def __init__(self, coordinator):
            super().__init__(coordinator)

        def _d(self, key):
            return (self.coordinator.data or {}).get(key)

        @property
        def native_value(self):
            temp = self._d("advanced.actual_boiler_temp")
            o2 = self._d("advanced.oxygen")
            auger = self._d("vacuum.output_auger") or self._d("advanced.auger_run") or 0
            timer = self._d("boiler.timer")
            burning = (auger and auger > 0) or (o2 is not None and o2 < 20.5 and temp and temp > 25)
            warm = temp is not None and temp > 30
            if burning or warm:
                return "I drift"
            if temp is not None and temp > 22:
                return "Tænder op"
            return "Stoppet af ur" if timer == 1 else "Off"

        @property
        def extra_state_attributes(self):
            data = self.coordinator.data or {}
            return {"ur_aktiv": data.get("boiler.timer"), "bypass_laases_op": hass.data[DOMAIN].get("bypass", False)}

    entities = [PilleFyrSensor(key, name, unit, dc) for key, name, unit, dc in MAIN]
    entities.append(PilleFyrTilstand(coordinator))
    add_entities(entities, update_before_add=True)
    LOGGER.info("Pillefyr: %d sensore oprettet", len(entities))
