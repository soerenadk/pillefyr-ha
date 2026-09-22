"""Blackstar/NBE pillefyr via Stokercloud API. Bygget af Amber, sep 22.

v1.2: UI-opsætning via config flow (Tilføj integration) + knapper og
timer-switch. Gamle YAML-opsætning virker stadig som før.
"""
import json
import logging
from datetime import timedelta

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import BASE, DOMAIN, LOGGER, MENUS, PLATFORMS, SCAN_INTERVAL

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
        text = await self._get(
            f"{BASE}/updatevalue.php?name={name}&value={value}&token={self.token}"
        )
        LOGGER.info("set_value %s=%s -> %s", name, value, text[:100])
        return text


def make_coordinator(hass, api):
    """Bygger DataUpdateCoordinator der læser alle menuer."""

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

    return DataUpdateCoordinator(
        hass, LOGGER, name="pillefyr", update_method=async_fetch,
        update_interval=SCAN_INTERVAL,
    )


def ensure_state(hass, api=None):
    """Sikrer at hass.data[DOMAIN] har api + coordinator (genbruges på tværs af YAML/entry)."""
    hass.data.setdefault(DOMAIN, {})
    data = hass.data[DOMAIN]
    if api is not None and "api" not in data:
        data["api"] = api
    if "coordinator" not in data and api is not None:
        data["coordinator"] = make_coordinator(hass, api)
    data.setdefault("bypass", False)
    return data


async def do_start(hass, value=1, ignorer_ur=False):
    """misc.start — lægger fyret under timeren.
    ignorer_ur: true => timer slås midlertidigt FRA og restores ved næste stop
    (kommandoen "tænd fyret uanset uret")."""
    data = hass.data[DOMAIN]
    api = data["api"]
    if ignorer_ur:
        state = (data["coordinator"].data or {}).get("boiler.timer")
        if state == 1:
            await api.set_value("boiler.timer", 0)
            data["bypass"] = True
    await api.set_value("misc.start", value)
    await data["coordinator"].async_request_refresh()


async def do_stop(hass, value=1):
    """misc.stop = hård off. Restorer timeren hvis en bypass-start havde slået den fra."""
    data = hass.data[DOMAIN]
    api = data["api"]
    await api.set_value("misc.stop", value)
    if data.get("bypass"):
        await api.set_value("boiler.timer", 1)
        data["bypass"] = False
    await data["coordinator"].async_request_refresh()


def ensure_services(hass: HomeAssistant):
    """Registrér tjenester én gang (YAML- eller entry-sti, whichever kommer først)."""
    data = hass.data[DOMAIN]
    if data.get("services_ok"):
        return
    data["services_ok"] = True

    async def svc_start(call):
        await do_start(hass, call.data.get("value", 1), call.data.get("ignorer_ur", False))

    async def svc_stop(call):
        await do_stop(hass, call.data.get("value", 1))

    async def svc_timer(call):
        await hass.data[DOMAIN]["api"].set_value(
            "boiler.timer", 1 if call.data.get("aktiv") else 0
        )

    async def svc_set(call):
        await hass.data[DOMAIN]["api"].set_value(call.data["name"], call.data["value"])

    async def svc_reset_alarm(call):
        await hass.data[DOMAIN]["api"].set_value("misc.reset_alarm", 1)

    hass.services.async_register(DOMAIN, "start", svc_start)
    hass.services.async_register(DOMAIN, "stop", svc_stop)
    hass.services.async_register(DOMAIN, "timer", svc_timer)
    hass.services.async_register(DOMAIN, "set_value", svc_set)
    hass.services.async_register(DOMAIN, "reset_alarm", svc_reset_alarm)


async def async_setup(hass: HomeAssistant, config):
    """Gammel YAML-sti: pillefyr: i configuration.yaml."""
    conf = config[DOMAIN]
    session = async_get_clientsession(hass)
    api = PilleFyrAPI(session, conf[CONF_USERNAME], conf[CONF_PASSWORD])
    data = ensure_state(hass, api)
    if "coordinator" in data:
        await data["coordinator"].async_refresh()
    ensure_services(hass)
    data.setdefault("username", conf[CONF_USERNAME])
    return True


async def async_setup_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry):
    """UI-sti: Tilføj integration."""
    session = async_get_clientsession(hass)
    api = PilleFyrAPI(
        session, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD]
    )
    try:
        await api.login()
    except UpdateFailed as err:
        raise ConfigEntryNotReady(str(err)) from err

    data = ensure_state(hass, api)
    data.setdefault("username", entry.data[CONF_USERNAME])
    if "coordinator" in data:
        coordinator = data["coordinator"]
    else:
        coordinator = make_coordinator(hass, api)
        data["coordinator"] = coordinator
        await coordinator.async_refresh()
    ensure_services(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry):
    """Losser platforme; lad koordinatoren køre hvis YAML-stien også er aktiv."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
