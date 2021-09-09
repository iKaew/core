"""The linkstation component constants."""

from typing import Final

DOMAIN: Final = "linkstation"
PLATFORMS: Final = ["sensor"]

DEFAULT_NAME = "LinkStation"

LINKSTATION_RESTART_SERVICE: Final = "restart_linkstation"
LINKSTATION_REFRESH_SERVICE: Final = "refresh_linkstation"


CONF_MANUAL: Final = "manual"


DEFAULT_NAS_LANGUAGE: Final = "en"
DEFAULT_PROTOCOL: Final = "http"
DEFAULT_UPDATE_INTERVAL: Final = 30
