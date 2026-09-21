# digi-player amplifier control

A Home Assistant `media_player` **control surface** for an amplifier driven by
[`digi-playerd`](https://github.com/bjtallguy/digi-player) over RS-232.

This integration does not play anything. It exposes power, volume and mute for
an amplifier that `digi-playerd` already owns, so that Music Assistant can bind
them through its `PlayerControl` mechanism (`power_control`, `volume_control`,
`mute_control`) to the player that actually streams the audio.

## What it is, and what it is not

- **It never opens the serial port.** It speaks HTTP to `digi-playerd`, which
  remains the single owner of the RS-232 connection to the amplifier.
- **It is not a player.** It deliberately does not declare `PLAY_MEDIA`. It
  declares exactly four features: `TURN_ON`, `TURN_OFF`, `VOLUME_SET` and
  `VOLUME_MUTE`.
- **It has no Python dependencies.** `manifest.json` declares
  `"requirements": []`, so Home Assistant installs nothing at startup.

### Do not point `arcam_fmj` at the same amplifier

Exactly one process may own the serial connection. If you also configure Home
Assistant's stock `arcam_fmj` integration against the same serial device, the
two will fight over it. This integration cannot cause that on its own — it has
no serial access at all — but it is the moment someone is most tempted to add
`arcam_fmj` "to see the amp".

## Requirements

- A running `digi-playerd` instance reachable over your LAN, with its HTTP API
  enabled and an API token configured.
- Home Assistant 2026.2 or newer.

## Installation

### HACS (recommended)

1. HACS → Integrations → three-dot menu → **Custom repositories**.
2. Add `https://github.com/bjtallguy/digi-player-ha`, category **Integration**.
3. Install "digi-player amplifier control", then restart Home Assistant.

### Manual

Copy `custom_components/digi_player/` into your Home Assistant `config`
directory so it lands at `/config/custom_components/digi_player/`, then restart.

## Configuration

Settings → Devices & Services → **Add Integration** → "digi-player amplifier
control", then supply:

| Field | Value |
|---|---|
| Host | the address of the machine running `digi-playerd` |
| Port | `9760` |
| Token | the contents of `/etc/digi-player/api-token` |

All three are validated against the live daemon before anything is stored, so a
typo is rejected at this step rather than becoming a broken entity.

## Behaviour worth knowing

- **Power reflects the daemon's derived readiness, not raw amplifier power.**
  An amplifier that is switched on but on the wrong source still reads `off`,
  so Music Assistant performs a real preparation rather than assuming it can
  play.
- **An unreachable daemon makes the entity `unavailable`**, which Music
  Assistant treats as off. A daemon that cannot be reached never looks ready.
- **Turning it off follows the daemon's idle policy** rather than issuing an
  instant standby.
- `physical_power`, `source` and `idle_standby_pending` are exposed as
  diagnostic attributes.

## Licence

Apache 2.0 — see [LICENSE](LICENSE).
