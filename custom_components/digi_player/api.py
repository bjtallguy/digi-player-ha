"""Thin async client for `digi-playerd`'s control API.

This integration is a *control surface*: it never opens the serial port and
never imports `arcam.fmj`. Exactly one process owns the SR250's RS-232
connection, and that process is `digi-playerd` (requirements V2-3, V2-4).
Every amplifier fact here comes from the daemon over HTTP.
"""

from __future__ import annotations

from dataclasses import dataclass

import aiohttp


class DigiPlayerError(Exception):
    """The daemon could not be reached, or refused the request."""


class DigiPlayerAuthError(DigiPlayerError):
    """The bearer token was missing or wrong."""


@dataclass(frozen=True, slots=True)
class AmplifierStatus:
    """One `/v1/state` response.

    ``powered`` is the daemon's *derived* readiness -- verified on, relay
    ready, correct source, safe volume -- not the amplifier's raw power bit.
    MA-5a requires the entity's power state to reflect this, which is why
    ``physical_power`` is carried alongside but only ever displayed as a
    diagnostic.
    """

    powered: bool
    physical_power: bool | None
    source: str | None
    volume: int | None
    muted: bool
    idle_standby_pending: bool

    @classmethod
    def from_payload(cls, payload: dict) -> AmplifierStatus:
        return cls(
            powered=bool(payload.get("powered")),
            physical_power=payload.get("physical_power"),
            source=payload.get("source"),
            volume=payload.get("volume"),
            # The daemon-owned logical mute, never `physical_muted`: a volume
            # of zero the user dialled in by hand is not a mute.
            muted=bool(payload.get("muted")),
            idle_standby_pending=bool(payload.get("idle_standby_pending")),
        )


class DigiPlayerClient:
    """Speak the small, named-operation control API and nothing else."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int,
        token: str,
    ) -> None:
        self._session = session
        self._base = f"http://{host}:{port}"
        self._token = token

    async def get_state(self, timeout: float) -> AmplifierStatus:
        return await self._request("GET", "/v1/state", timeout)

    async def prepare(self, timeout: float) -> AmplifierStatus:
        return await self._request("POST", "/v1/prepare", timeout)

    async def playback_stopped(self, timeout: float) -> None:
        # Returns {"ok": true} rather than a state body; the coordinator's
        # next refresh picks up the resulting state.
        await self._request("POST", "/v1/playback-stopped", timeout, expect_state=False)

    async def set_volume(self, volume: int, timeout: float) -> AmplifierStatus:
        return await self._request("POST", f"/v1/set-volume?volume={volume}", timeout)

    async def set_muted(self, muted: bool, timeout: float) -> AmplifierStatus:
        value = "true" if muted else "false"
        return await self._request("POST", f"/v1/mute?muted={value}", timeout)

    async def _request(
        self,
        method: str,
        target: str,
        timeout: float,
        *,
        expect_state: bool = True,
    ) -> AmplifierStatus | None:
        try:
            async with self._session.request(
                method,
                f"{self._base}{target}",
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as response:
                if response.status == 401:
                    raise DigiPlayerAuthError("digi-playerd rejected the API token")
                if response.status != 200:
                    # 503 means the daemon refused an unsafe or failed control
                    # operation. Surfacing it as an error is deliberate: the
                    # caller must not treat a stale state as success.
                    raise DigiPlayerError(
                        f"digi-playerd returned HTTP {response.status} for {target}"
                    )
                payload = await response.json(content_type=None)
        except DigiPlayerError:
            raise
        except Exception as error:  # aiohttp errors, timeouts, bad JSON
            raise DigiPlayerError(f"digi-playerd request failed: {error}") from error
        if not expect_state:
            return None
        return AmplifierStatus.from_payload(payload)
