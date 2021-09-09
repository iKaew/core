"""Integration for Buffalo LinkStation NAS."""

from datetime import timedelta
import logging
import typing

from linkstation import LinkStation
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_DISKS,
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_MANUAL,
    DEFAULT_NAME,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    LINKSTATION_REFRESH_SERVICE,
    LINKSTATION_RESTART_SERVICE,
    PLATFORMS,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    vol.All(
        {
            DOMAIN: vol.Schema(
                {
                    vol.Required(CONF_HOST): cv.string,
                    vol.Required(CONF_PASSWORD): cv.string,
                    vol.Required(CONF_USERNAME): cv.string,
                    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=timedelta(minutes=DEFAULT_UPDATE_INTERVAL),
                    ): cv.positive_time_period,
                    vol.Optional(CONF_MANUAL, default=False): cv.boolean,
                }
            )
        },
    ),
    extra=vol.ALLOW_EXTRA,
)


async def get_data(hass: HomeAssistant):
    """Get data."""
    coordinator = LinkStation("kaew", "dmf93kZl", "192.168.1.102")
    # pctUsed = await coordinator.get_disk_pct_used("disk2")
    await coordinator.close()

    # _LOGGER.warning("pctUsed %s", pctUsed)


"""
async def async_setup(hass: HomeAssistant, config_entry: ConfigEntry):

    # States are in the format DOMAIN.OBJECT_ID.

    hass.services.async_register(DOMAIN, LINKSTATION_REFRESH_SERVICE, get_data)

    # Return boolean to indicate that initialization was successfully.
    return True
"""


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up the LinkStation component."""

    coordinator = LinkStationDataCoordinator(hass, config_entry)
    await coordinator.async_setup()

    hass.data[DOMAIN] = coordinator
    hass.config_entries.async_setup_platforms(config_entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload LinkStation Entry from config_entry."""
    hass.services.async_remove(DOMAIN, LINKSTATION_RESTART_SERVICE)

    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )
    if unload_ok:
        hass.data.pop(DOMAIN)
    return unload_ok


async def options_updated_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    if entry.options[CONF_MANUAL]:
        hass.data[DOMAIN].update_interval = None
        return

    hass.data[DOMAIN].update_interval = timedelta(
        minutes=entry.options[CONF_SCAN_INTERVAL]
    )
    await hass.data[DOMAIN].async_request_refresh()


class LinkStationDataCoordinator(DataUpdateCoordinator):
    """Coordinator to get the latest info from LinkStation."""

    def __init__(self, hass: HomeAssistant, config_entry) -> None:
        """Initialize the data object."""

        name = config_entry[CONF_NAME]
        host = config_entry[CONF_HOST]
        username = config_entry[CONF_USERNAME]
        password = config_entry[CONF_PASSWORD]
        disks = config_entry[CONF_DISKS]
        interval = config_entry[CONF_SCAN_INTERVAL]

        self.hass = hass
        self.config_entry: ConfigEntry = config_entry
        self.api = LinkStation(username, password, host)
        self.name = name
        self.disks = disks

        super().__init__(
            self.hass,
            _LOGGER,
            name=name,
            update_method=self.async_update,
            update_interval=interval,
        )

    async def update_data(self):
        """Update data."""
        diskUsedPct = await self.api.get_disk_pct_used("disk2")
        self.api.close()
        return {"pctUsed": diskUsedPct}

    async def async_update(self) -> typing.Dict[str, str]:
        """Update LinkStation data."""
        return await self.hass.async_add_executor_job(self.update_data)

    async def async_set_options(self):
        """Set options for entry."""
        if not self.config_entry.options:
            data = {**self.config_entry.data}
            options = {
                CONF_SCAN_INTERVAL: data.pop(
                    CONF_SCAN_INTERVAL, DEFAULT_UPDATE_INTERVAL
                ),
                CONF_MANUAL: data.pop(CONF_MANUAL, False),
            }
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=data, options=options
            )

    async def async_setup(self) -> None:
        """Set up LinkStation."""

        async def request_update(call):
            """Request update."""
            await self.async_update()

        await self.async_set_options()

        self.hass.services.async_register(
            DOMAIN, LINKSTATION_REFRESH_SERVICE, request_update
        )

        self.config_entry.async_on_unload(
            self.config_entry.add_update_listener(options_updated_listener)
        )
