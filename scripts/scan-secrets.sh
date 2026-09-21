#!/usr/bin/env bash
#
# Scan for secrets before they reach a public repository.
#
# Usage:
#   scripts/scan-secrets.sh                 # scan the working tree
#   scripts/scan-secrets.sh <range>         # scan added lines in a commit range
#
# Exit 0 = clean, 1 = something looks like a secret, 2 = usage error.
#
# This runs from the pre-push hook on every push, not only on releases. A
# secret pushed to any branch of a public repo is published the moment it
# lands, and rewriting history does not un-publish it: the commit stays
# reachable through the GitHub API and through any fork or clone. If one does
# get out, rotate the credential -- do not just force-push over it.

set -uo pipefail

RANGE="${1:-}"

# Each rule is  name<TAB>regex. Written for grep -E.
read -r -d '' RULES <<'PATTERNS'
Nabu Casa instance URL	[a-z0-9]{20,}\.ui\.nabu\.casa
Nabu Casa MCP webhook	/api/webhook/mcp_[0-9a-f]{16,}
HA MCP OAuth client id	hamcp-[0-9a-f]{16,}
JSON Web Token	eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}
Private key block	BEGIN [A-Z ]*PRIVATE KEY
digi-playerd API token assignment	(api[_-]?token|API[_-]?TOKEN)[[:space:]]*[:=][[:space:]]*['\"]?[A-Za-z0-9_-]{16,}
Authorization header with literal	[Aa]uthorization:[[:space:]]*Bearer[[:space:]]+[A-Za-z0-9_.-]{16,}
Real LAN addressing	192\.168\.10\.[0-9]{1,3}
PATTERNS

# Documentation examples deliberately use 192.168.1.x, which is NOT the real
# network and is fine to publish. Anything matching this is not a finding.
ALLOW='192\.168\.1\.[0-9]{1,3}([^0-9]|$)'

if [ -n "$RANGE" ]; then
  # Added lines only: what this push would introduce.
  CONTENT="$(git diff --unified=0 "$RANGE" -- . 2>/dev/null \
             | grep -E '^\+' | grep -Ev '^\+\+\+')"
  SCOPE="added lines in $RANGE"
else
  CONTENT="$(git ls-files -z 2>/dev/null \
             | xargs -0 -I{} sh -c 'case "{}" in *.png|*.jpg|*.gif|*.pdf) ;; *) cat "{}" 2>/dev/null;; esac')"
  SCOPE="working tree"
fi

if [ -z "$CONTENT" ]; then
  echo "scan-secrets: nothing to scan ($SCOPE)"
  exit 0
fi

# The scanner must never print the secret it finds -- that would copy it into
# terminal scrollback and CI logs. Report the rule and a count only.
FOUND=0
while IFS=$'\t' read -r NAME REGEX; do
  [ -z "${NAME:-}" ] && continue
  HITS="$(printf '%s\n' "$CONTENT" | grep -E "$REGEX" | grep -Ev "$ALLOW" | wc -l | tr -d ' ')"
  if [ "$HITS" != "0" ]; then
    echo "  BLOCKED  $NAME -- $HITS line(s)"
    FOUND=$((FOUND + HITS))
  fi
done <<< "$RULES"

if [ "$FOUND" != "0" ]; then
  cat <<EOF

scan-secrets: $FOUND suspected secret(s) in the $SCOPE.

Nothing has been pushed. Find them with the rule name above, for example:
  git diff ${RANGE:-HEAD} | grep -nE '<the pattern>'

If a match is a false positive, add it to ALLOW in scripts/scan-secrets.sh
with a comment saying why it is safe. Do not pass --no-verify.
EOF
  exit 1
fi

echo "scan-secrets: clean ($SCOPE)"
exit 0
