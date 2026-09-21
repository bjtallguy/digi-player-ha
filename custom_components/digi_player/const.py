"""Constants for the digi-player control integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "digi_player"

CONF_TOKEN_KEY = "token"
DEFAULT_PORT = 9760

# MA-7: current enough to feel live, never faster than the serial transport
# sustains. Every poll costs a real RS-232 state query on the daemon's shared
# lock. Settled on real hardware in V2-7 (2026-09-21): ten polls during live
# playback measured min 36.6 ms, mean 39.8 ms, max 49.5 ms, so at 5 s this is a
# 0.8% duty cycle on that lock -- the transport is not the constraint.
#
# The interval bounds how quickly a change made OUTSIDE Home Assistant reaches
# it: the amplifier's front-panel knob, the Sendspin hook path, or a direct
# daemon API call. A change made through this entity updates from the command
# response and does not wait for a poll. At the previous 15 s, externally driven
# changes lagged visibly in Music Assistant's UI.
SCAN_INTERVAL = timedelta(seconds=5)

# `prepare` powers the amplifier, waits out the transition interlock and the
# output-relay delay, and may retry -- tens of seconds is normal, not a fault.
PREPARE_TIMEOUT_SECONDS = 90
# Everything else is a single command plus its verification round trip.
COMMAND_TIMEOUT_SECONDS = 20
