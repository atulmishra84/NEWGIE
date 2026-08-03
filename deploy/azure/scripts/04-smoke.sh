#!/usr/bin/env bash
# Back-compat wrapper — prefer 05-smoke.sh
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
echo "NOTE: 04-smoke.sh is deprecated; forwarding to 05-smoke.sh" >&2
exec "$DIR/05-smoke.sh" "$@"
