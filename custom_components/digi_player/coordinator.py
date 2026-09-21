"""Polling coordinator for one digi-player appliance."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AmplifierStatus, DigiPlayerAuthError, DigiPlayerClient, DigiPlayerError
from .const import COMMAND_TIMEOUT_SECONDS, DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class DigiPlayerCoordinator(DataUpdateCoordinator[AmplifierStatus]):
    """Keep one amplifier's state current without out-running the serial link."""

    def __init__(
        self, hass: HomeAssistant, client: DigiPlayerClient, entry: ConfigEntry
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {entry.title}",
            update_interval=SCAN_INTERVAL,
        )
        self.client = client
        self.entry = entry

    async def _async_update_data(self) -> AmplifierStatus:
        try:
            return await self.client.get_state(COMMAND_TIMEOUT_SECONDS)
        except DigiPlayerAuthError as error:
            # Prompt re-authentication rather than retrying a token that the
            # daemon has already refused.
            raise ConfigEntryAuthFailed(str(error)) from error
        except DigiPlayerError as error:
            # UpdateFailed marks the entity unavailable. That is the safe
            # reading: Music Assistant treats "unavailable" as off, so a
            # daemon we cannot reach never looks ready for playback.
            raise UpdateFailed(str(error)) from error
