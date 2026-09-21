"""The `media_player` entity Music Assistant binds its player controls to.

The feature set and state shape here are not arbitrary. Music Assistant's
`hass` plugin decides what an entity can serve as by reading
`supported_features` (see `get_control_capabilities` in MA 2.10):

* power  -- requires TURN_ON *and* TURN_OFF; read from the entity state,
            against OFF_STATES = ("unavailable", "unknown", "standby", "off")
* volume -- requires VOLUME_SET; read from `volume_level`, multiplied by 100
* mute   -- requires VOLUME_MUTE; read from `is_volume_muted`

MA calls `volume_set` with `volume_level` as 0.0-1.0 while the daemon speaks
0-100, so the scaling boundary lives here. The daemon's ceiling is applied
after it, in the control path, and is not duplicated here -- a UI-side cap is
not a safety mechanism (V2-6b).
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import DigiPlayerError
from .const import COMMAND_TIMEOUT_SECONDS, DOMAIN, PREPARE_TIMEOUT_SECONDS
from .coordinator import DigiPlayerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: DigiPlayerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DigiPlayerMediaPlayer(coordinator, entry)])


class DigiPlayerMediaPlayer(CoordinatorEntity[DigiPlayerCoordinator], MediaPlayerEntity):
    """An amplifier exposed as a control surface, not as a player.

    It deliberately declares no PLAY_MEDIA and carries no media state: audio
    routing belongs to the Sendspin player, and this entity exists only so
    power, volume and mute can be bound to it.
    """

    _attr_has_entity_name = True
    _attr_name = None
    _attr_device_class = MediaPlayerDeviceClass.RECEIVER
    _attr_supported_features = (
        MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_MUTE
    )

    def __init__(self, coordinator: DigiPlayerCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Arcam",
            model="SR250 (via digi-player)",
        )

    @property
    def state(self) -> MediaPlayerState:
        """Report the daemon's derived readiness, never raw amplifier power.

        MA-5a: an amplifier that is physically on but on the wrong source, or
        at an unsafe volume, is not ready for playback. Reporting OFF in that
        case makes Music Assistant call `turn_on` and wait for a real
        preparation, which is exactly the behaviour we want.
        """
        status = self.coordinator.data
        if status is None:
            return MediaPlayerState.OFF
        return MediaPlayerState.ON if status.powered else MediaPlayerState.OFF

    @property
    def volume_level(self) -> float | None:
        status = self.coordinator.data
        if status is None or status.volume is None:
            return None
        return min(max(status.volume, 0), 100) / 100

    @property
    def is_volume_muted(self) -> bool | None:
        status = self.coordinator.data
        return None if status is None else status.muted

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Diagnostics only -- never the basis for a control decision."""
        status = self.coordinator.data
        if status is None:
            return {}
        return {
            "physical_power": status.physical_power,
            "source": status.source,
            "idle_standby_pending": status.idle_standby_pending,
        }

    async def async_turn_on(self) -> None:
        """Prepare the amplifier for playback and wait for verification.

        Music Assistant awaits this before `play_media`, so returning early
        would defeat the ordering that makes the first seconds audible.
        """
        await self._command(
            self.coordinator.client.prepare(PREPARE_TIMEOUT_SECONDS), "turn on"
        )

    async def async_turn_off(self) -> None:
        """Start the daemon's existing idle policy; never an instant standby.

        V2-5: this reuses the already-validated idle path rather than adding a
        new safety-relevant code path for switch-like UX. The amplifier goes
        to standby when the daemon's grace period expires, not immediately.
        """
        await self._command(
            self.coordinator.client.playback_stopped(COMMAND_TIMEOUT_SECONDS),
            "turn off",
        )

    async def async_set_volume_level(self, volume: float) -> None:
        amplifier_volume = round(min(max(volume, 0.0), 1.0) * 100)
        await self._command(
            self.coordinator.client.set_volume(
                amplifier_volume, COMMAND_TIMEOUT_SECONDS
            ),
            "set volume",
        )

    async def async_mute_volume(self, mute: bool) -> None:
        await self._command(
            self.coordinator.client.set_muted(mute, COMMAND_TIMEOUT_SECONDS),
            "mute" if mute else "unmute",
        )

    async def _command(self, awaitable, description: str) -> None:
        """Run one control call, then refresh from the daemon.

        The daemon is authoritative, so the entity never assumes a command
        succeeded: it re-reads state afterwards. A failure is raised to the
        caller rather than swallowed, so Music Assistant and the Home
        Assistant UI both see that the amplifier did not do what was asked.
        """
        try:
            await awaitable
        except DigiPlayerError as error:
            raise HomeAssistantError(
                f"digi-player could not {description}: {error}"
            ) from error
        finally:
            await self.coordinator.async_request_refresh()
