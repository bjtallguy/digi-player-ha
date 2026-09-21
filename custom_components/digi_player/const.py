"""Constants for the digi-player control integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "digi_player"

CONF_TOKEN_KEY = "token"
DEFAULT_PORT = 9760

# MA-7: current enough to feel live, never faster than the serial transport
# sustains. Every poll costs a real RS-232 state query on the daemon's shared
# lock, so this stays conservative until V2-7 settles it on real hardware.
SCAN_INTERVAL = timedelta(seconds=15)

# `prepare` powers the amplifier, waits out the transition interlock and the
# output-relay delay, and may retry -- tens of seconds is normal, not a fault.
PREPARE_TIMEOUT_SECONDS = 90
# Everything else is a single command plus its verification round trip.
COMMAND_TIMEOUT_SECONDS = 20
