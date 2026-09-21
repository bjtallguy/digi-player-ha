"""Local-only Home Assistant integration for a digi-player appliance.

Never submitted to Home Assistant core (requirements V2-3). It exists so
Music Assistant can bind power, volume and mute to a real entity through MA's
own `PlayerControl` mechanism, without a native MA provider.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TOKEN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import DigiPlayerClient
from .const import DOMAIN
from .coordinator import DigiPlayerCoordinator

PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one amplifier from a config entry."""
    client = DigiPlayerClient(
        async_get_clientsession(hass),
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data[CONF_TOKEN],
    )
    coordinator = DigiPlayerCoordinator(hass, client, entry)
    # Fail setup loudly if the daemon is unreachable now, rather than
    # presenting an entity that silently never works.
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Tear the entry down cleanly, leaving the amplifier untouched.

    Removing this integration must never change amplifier state: the daemon
    owns the amplifier and keeps running regardless of Home Assistant.
    """
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN, None)
    return unloaded


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
