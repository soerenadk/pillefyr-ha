"""Blackstar/NBE pillefyr via Stokercloud API. Bygget af Amber, sep 22."""
import json
import logging
from datetime import timedelta

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

DOMAIN = "pillefyr"
LOGGER = logging.getLogger(__name__)

BASE = "https://stokercloud.dk/v2/dataout2"
MENUS = ["boiler", "advanced", "notification", "setup", "cleaning", "ext_feed", "fan", "screen"]
SCAN_INTERVAL = timedelta(minutes=5)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


class PilleFyrAPI:
    """Lille HTTP-klient omkring Stokerclouds dataout2-endpoints."""

    def __init__(self, session, username, password):
        self._session = session
        self._username = username
        self._password = password
        self.token = None

    async def login(self):
        url = f"{BASE}/login.php?user={self._username}&ctrlpassword={self._password}"
        async with self._session.get(url, timeout=30) as resp:
            data = await resp.json(content_type=None)
        if data.get("status") != 0:
            raise UpdateFailed(f"Login fejlede: {data}")
        self.token = data["token"]
        return self.token

    async def get_menu(self, menu):
        if not self.token:
            await self.login()
        url = f"{BASE}/getmenudata.php?menu={menu}&token={self.token}"
        text = await self._get(url)
        if not text.strip().startswith("{"):
            LOGGER.info("Token udløbet (menu %s) — logger ind igen", menu)
            await self.login()
            text = await self._get(f"{BASE}/getmenudata.php?menu={menu}&token={self.token}")
        try:
            return json.loads(text)
        except ValueError:
            raise UpdateFailed(f"Ugyldigt svar fra {menu}: {text[:120]}")

    async def _get(self, url):
        async with self._session.get(url, timeout=30) as resp:
            return await resp.text()

    async def set_value(self, name, value):
        if not self.token:
            await self.login()
        text = await self._get(f"{BASE}/updatevalue.php?name={name}&value={value}&token={self.token}")
        LOGGER.info("set_value %s=%s -> %s", name, value, text[:100])
        return text


async def async_setup(hass: HomeAssistant, config):
    conf = config[DOMAIN]
    session = async_get_clientsession(hass)
    api = PilleFyrAPI(session, conf[CONF_USERNAME], conf[CONF_PASSWORD])

    async def async_fetch():
        data = {}
        for menu in MENUS:
            try:
                values = await api.get_menu(menu)
            except Exception as err:
                LOGGER.warning("Menu %s fejlede: %s", menu, err)
                continue
            for key, spec in (values or {}).items():
                if isinstance(spec, dict) and "val" in spec:
                    val = spec["val"]
                    try:
                        val = float(val) if "." in str(val) else int(val)
                    except (TypeError, ValueError):
                        pass
                    data[key] = val
        if not data:
            raise UpdateFailed("Ingen data fra nogen menuer")
        return data

    coordinator = DataUpdateCoordinator(
        hass, LOGGER, name="pillefyr", update_method=async_fetch,
        update_interval=SCAN_INTERVAL,
    )
    hass.data[DOMAIN] = {"api": api, "coordinator": coordinator, "bypass": False}
    await coordinator.async_refresh()

    async def svc_start(call):
        """misc.start — lægger fyret under timeren.
        ignorer_ur: true => timer slås midlertidigt FRA og restores ved næste stop
        (kommandoen "tænd fyret uanset uret")."""
        if call.data.get("ignorer_ur"):
            data = coordinator.data or {}
            if data.get("boiler.timer") == 1:
                await api.set_value("boiler.timer", 0)
                hass.data[DOMAIN]["bypass"] = True
        await api.set_value("misc.start", call.data.get("value", 1))

    async def svc_stop(call):
        """misc.stop = hård off. Restorer timeren hvis en bypass-start havde slået den fra."""
        await api.set_value("misc.stop", call.data.get("value", 1))
        if hass.data[DOMAIN].get("bypass"):
            await api.set_value("boiler.timer", 1)
            hass.data[DOMAIN]["bypass"] = False

    async def svc_timer(call):
        """boiler.timer on/off — slå urstyringen fra/til (vinterdrift)."""
        await api.set_value("boiler.timer", 1 if call.data.get("aktiv") else 0)

    async def svc_set(call):
        await api.set_value(call.data["name"], call.data["value"])

    async def svc_reset_alarm(call):
        await api.set_value("misc.reset_alarm", 1)

    hass.services.async_register(DOMAIN, "start", svc_start)
    hass.services.async_register(DOMAIN, "stop", svc_stop)
    hass.services.async_register(DOMAIN, "timer", svc_timer)
    hass.services.async_register(DOMAIN, "set_value", svc_set)
    hass.services.async_register(DOMAIN, "reset_alarm", svc_reset_alarm)
    return True
