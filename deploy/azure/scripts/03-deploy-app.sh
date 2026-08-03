#!/usr/bin/env bash
# Back-compat wrapper — prefer 04-deploy-app.sh
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
echo "NOTE: 03-deploy-app.sh is deprecated; forwarding to 04-deploy-app.sh" >&2
exec "$DIR/04-deploy-app.sh" "$@"
