"""Konstanter for pillefyr-integrationen."""
import logging
from datetime import timedelta

DOMAIN = "pillefyr"
LOGGER = logging.getLogger(__package__)

BASE = "https://stokercloud.dk/v2/dataout2"
MENUS = [
    "boiler", "advanced", "notification", "setup",
    "cleaning", "ext_feed", "fan", "screen",
]
PLATFORMS = ["sensor", "switch", "button"]
SCAN_INTERVAL = timedelta(minutes=5)
