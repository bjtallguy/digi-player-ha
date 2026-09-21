"""The integration's daemon-facing parsing.

Only the parts that need no Home Assistant are covered here; the entity itself
is validated against a real `homeassistant` package.

Moved here from the digi-player project on 2026-09-21, when this repository
became the single source of truth for the integration.

`api.py` is loaded directly from its path rather than imported as
`custom_components.digi_player.api`. Importing it through the package runs the
package's `__init__`, which imports `homeassistant` -- so a module that needs
only `aiohttp` would drag the whole of Home Assistant in, and these tests would
error anywhere HA is not installed. That is not hypothetical: this module
previously guarded on `aiohttp` alone, so wherever `aiohttp` was missing it
skipped and looked healthy, and wherever `aiohttp` was present it failed on the
`homeassistant` import. It never once ran.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

_API_PATH = Path(__file__).resolve().parents[1] / "custom_components" / "digi_player" / "api.py"


def _load_api():
    """Load api.py in isolation, bypassing the package __init__.

    The module must be registered in `sys.modules` *before* it is executed:
    `@dataclass` resolves `sys.modules[cls.__module__]` while processing the
    class, and an unregistered module makes that lookup return None, failing
    with `AttributeError: 'NoneType' object has no attribute '__dict__'`.
    """
    name = "_digi_player_api"
    spec = importlib.util.spec_from_file_location(name, _API_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        del sys.modules[name]
        raise
    return module


try:  # pragma: no cover - environment dependent
    _API = _load_api()
    REASON = ""
except ImportError as error:  # pragma: no cover - environment dependent
    _API = None
    REASON = f"api.py could not be loaded: {error}"


@unittest.skipIf(_API is None, REASON or "api.py unavailable")
class AmplifierStatusTests(unittest.TestCase):
    @staticmethod
    def _parse(payload: dict):
        return _API.AmplifierStatus.from_payload(payload)

    def test_parses_a_full_state_body(self) -> None:
        status = self._parse(
            {
                "powered": True,
                "physical_power": True,
                "source": "STB",
                "volume": 40,
                "muted": False,
                "physical_muted": False,
                "idle_standby_pending": False,
            }
        )
        self.assertTrue(status.powered)
        self.assertEqual("STB", status.source)
        self.assertEqual(40, status.volume)

    def test_mute_comes_from_the_logical_field_not_the_physical_one(self) -> None:
        """A volume of zero the user dialled in by hand is not a mute."""
        status = self._parse({"muted": False, "physical_muted": True, "volume": 0})
        self.assertFalse(status.muted)

        status = self._parse({"muted": True, "physical_muted": False, "volume": 0})
        self.assertTrue(status.muted)

    def test_powered_is_not_taken_from_physical_power(self) -> None:
        """MA-5a: physically on but not prepared is not ready for playback."""
        status = self._parse({"powered": False, "physical_power": True})
        self.assertFalse(status.powered)
        self.assertTrue(status.physical_power)

    def test_absent_fields_do_not_raise(self) -> None:
        """A daemon that omits a field must not break the coordinator."""
        status = self._parse({})
        self.assertFalse(status.powered)
        self.assertIsNone(status.volume)
        self.assertFalse(status.muted)

    def test_unknown_volume_stays_none(self) -> None:
        # None must reach the entity as an unknown volume_level, never as 0,
        # which would read as "silent" rather than "not known".
        self.assertIsNone(self._parse({"volume": None}).volume)


if __name__ == "__main__":
    unittest.main()
