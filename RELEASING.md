# Release strategy

This repository is public and installable through HACS. A release here lands on
other people's Home Assistant instances, so the rules below are about their
instances, not this bench.

## Branches

- **`main` is the release branch.** It is what HACS resolves when someone
  installs from the default branch, and what releases are cut from.
- **All work happens on a branch.** No direct commits to `main`, including
  documentation and including "trivial" fixes.
- **Merging to `main` needs BJ's explicit approval**, every time. An agent never
  merges to `main` or cuts a release on its own judgement.

Branch naming is not policed; something readable is enough
(`fix/mute-latch`, `feat/v2-6-playercontrol`).

## What actually ships to users

Publishing a **GitHub release** is the act that ships. HACS offers users the
latest release, so:

- Merging to `main` stages a change. Tagging a release delivers it.
- Both need approval, and they are separate decisions — a merge is not standing
  permission to release.
- HACS refreshes custom repositories only about every 48 hours. After a release,
  `update_information` forces it to notice immediately.

## Versioning

`custom_components/digi_player/manifest.json` carries the version, and its value
must match the release tag (`0.1.0` ↔ `v0.1.0`). HACS reads the tag; Home
Assistant reads the manifest. If they disagree, users get confusing version
reporting.

Semantic versioning, with the config entry in mind:

- **patch** — fixes that change no behaviour users configured.
- **minor** — new capability that an existing config entry survives.
- **major** — anything requiring users to reconfigure, or a changed minimum
  Home Assistant version (`hacs.json`'s `homeassistant` key).

## Before every push: scan for secrets

`scripts/scan-secrets.sh` runs automatically from the `pre-push` hook, on every
push, to every branch — not just releases.

Enable the hook after cloning:

```bash
git config core.hooksPath scripts
```

Run it by hand against the working tree at any time:

```bash
scripts/scan-secrets.sh
```

**Why every branch, not just `main`:** a secret pushed to any branch of a public
repo is published the moment it lands. Rewriting history does not un-publish it
— the commit stays reachable through the GitHub API, and through any fork or
clone made in between. The only real remedy is rotating the credential.

**Do not bypass it with `--no-verify`.** If the scanner is wrong, add the case
to `ALLOW` in the script with a comment explaining why it is safe, so the
exception is reviewed rather than invisible.

GitHub's own secret scanning with push protection is enabled on this repository
as a second line of defence. It catches provider-issued credentials this script
does not know about, but it knows nothing about *our* secrets — the
`digi-playerd` API token, the Nabu Casa webhook URL — so it is a backstop, not
the primary control.

### What counts as a secret here

- The `digi-playerd` API token (`/etc/digi-player/api-token`).
- The Nabu Casa webhook URL — the URL **is** the credential.
- Home Assistant OAuth client secrets and long-lived access tokens.
- SSH private keys.
- The real LAN addressing. Documentation examples use `192.168.1.x`, which is
  deliberately not the real network and is allow-listed.

## Release checklist

1. Work on a branch; open it for review.
2. **Get BJ's approval to merge.**
3. Bump `version` in `manifest.json` to match the intended tag.
4. Merge to `main`. The `pre-push` scan runs automatically.
5. **Get BJ's approval to release.**
6. Tag and publish the GitHub release.
7. Force HACS to re-read the repository so the update appears without waiting.
8. Verify on a real instance before telling anyone it is out.
