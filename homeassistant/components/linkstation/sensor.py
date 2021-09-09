"""Support for monitoring the LinkStation client."""
from __future__ import annotations

from datetime import timedelta
import logging
import sys

from linkstation import LinkStation
import voluptuous as vol

from homeassistant.components.linkstation.const import (
    DEFAULT_NAME,
    DEFAULT_UPDATE_INTERVAL,
)
from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    STATE_CLASS_MEASUREMENT,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import (
    CONF_DISKS,
    CONF_HOST,
    CONF_MONITORED_VARIABLES,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    DATA_GIGABYTES,
    PERCENTAGE,
)
from homeassistant.exceptions import PlatformNotReady
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)
_THROTTLED_REFRESH = None

SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="current_status",
        name="Status",
    ),
    SensorEntityDescription(
        key="disk_capacity",
        name="Disk Capacity",
        native_unit_of_measurement=DATA_GIGABYTES,
        state_class=STATE_CLASS_MEASUREMENT,
    ),
    SensorEntityDescription(
        key="disk_used",
        name="Disk Used",
        native_unit_of_measurement=DATA_GIGABYTES,
        state_class=STATE_CLASS_MEASUREMENT,
    ),
    SensorEntityDescription(
        key="disk_free",
        name="Disk Space Free",
        native_unit_of_measurement=DATA_GIGABYTES,
        state_class=STATE_CLASS_MEASUREMENT,
    ),
    SensorEntityDescription(
        key="disk_used_pct",
        name="Disk Used Pct",
        native_unit_of_measurement=PERCENTAGE,
        state_class=STATE_CLASS_MEASUREMENT,
    ),
)

SENSOR_KEYS: list[str] = [desc.key for desc in SENSOR_TYPES]

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Optional(
            CONF_SCAN_INTERVAL,
            default=timedelta(minutes=DEFAULT_UPDATE_INTERVAL),
        ): cv.positive_time_period,
        vol.Optional(CONF_DISKS, default=[]): vol.All(),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_MONITORED_VARIABLES, default=[]): vol.All(
            cv.ensure_list, [vol.In(SENSOR_KEYS)]
        ),
    }
)


async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Linkstation sensors."""
    name = config[CONF_NAME]
    host = config[CONF_HOST]
    username = config[CONF_USERNAME]
    password = config[CONF_PASSWORD]
    # disks = config[CONF_DISKS]

    linkstation_api = LinkStation(username, password, host)
    try:
        await linkstation_api.get_disks_info()
        disks = await linkstation_api.get_active_disks()
    except Exception:
        _LOGGER.error("Connection to LinkStation failed")
        raise PlatformNotReady

    monitored_variables = config[CONF_MONITORED_VARIABLES]
    entities = []

    for disk in disks:
        for description in SENSOR_TYPES:
            if description.key in monitored_variables:
                entities.append(
                    LinkStationSensor(linkstation_api, name, description, disk)
                )
    add_entities(entities)


class LinkStationSensor(SensorEntity):
    """Representation of a LinkStation sensor."""

    def __init__(
        self,
        linkstation_client: LinkStation,
        client_name,
        description: SensorEntityDescription,
        disk: str,
    ):
        """Initialize the sensor."""
        self.entity_description = description
        self.client = linkstation_client
        self.data = None
        self.disk = disk

        self._attr_available = False
        self._attr_name = f"{client_name} {description.name} - {disk}"
        # self._attr_should_poll = True

    async def async_update(self):
        """Get the latest data from LinkStation and updates the state."""
        try:
            self.data = await self.client.get_disk_status(self.disk)
            self._attr_available = True
        except Exception:
            _LOGGER.error("Connection to LinkStation Failed")
            _LOGGER.error("Oops! %s occurred.", sys.exc_info()[0])
            self._attr_available = False
            return

        sensor_type = self.entity_description.key
        if sensor_type == "current_status":
            self._attr_native_value = self.data
            self._attr_icon = "mdi:harddisk"
            return

        if self.data and self.data.startswith("normal"):
            if sensor_type == "disk_capacity":
                self._attr_native_value = await self.client.get_disk_capacity(self.disk)
                self._attr_icon = "mdi:folder-outline"

            elif sensor_type == "disk_used":
                self._attr_native_value = await self.client.get_disk_amount_used(
                    self.disk
                )
                self._attr_icon = "mdi:folder-outline"

            elif sensor_type == "disk_used_pct":
                self._attr_native_value = await self.client.get_disk_pct_used(self.disk)
                self._attr_icon = "mdi:gauge"

            elif sensor_type == "disk_free":

                self._attr_native_value = await self.client.get_disk_capacity(
                    self.disk
                ) - await self.client.get_disk_amount_used(self.disk)
                self._attr_icon = "mdi:folder-outline"
        else:
            self._attr_available = False
