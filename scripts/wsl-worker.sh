#!/usr/bin/env bash
# The worker inside WSL, for a server on Windows: scripts/start.ps1 runs it when the GPU stack
# lives in WSL (native Windows is not supported by the engine, see NOTICE.md).
#
#   scripts/wsl-worker.sh PORT [ENROLMENT_TOKEN]
#
# WSL reaches Windows through its gateway, whose address changes with every boot: the worker's
# server address is set to it each time. The first time it is enrolled with the token given. It
# stops when the launcher does (its end of our stdin closes).
set -euo pipefail
cd "$(dirname "$0")/.."
PORT="$1"
TOKEN="${2:-}"
export PATH="$HOME/.local/bin:$PATH"
# yt-dlp needs node for YouTube; with nvm it is only on the PATH of a login shell.
if [ -s "$HOME/.nvm/nvm.sh" ]; then
  # shellcheck source=/dev/null
  . "$HOME/.nvm/nvm.sh" >/dev/null
fi

GATEWAY="$(ip route show default | awk '{print $3}')"
SERVER="http://$GATEWAY:$PORT"
CONFIG="${XDG_DATA_HOME:-$HOME/.local/share}/karaoke-worker/worker.json"

if [ ! -f "$CONFIG" ]; then
  if [ -z "$TOKEN" ]; then
    echo "not enrolled and no enrolment token" >&2
    exit 1
  fi
  .venv/bin/karaoke-worker enroll "$SERVER" "$TOKEN" --name "$(hostname)-wsl"
else
  .venv/bin/python - "$CONFIG" "$SERVER" <<'PY'
import json, sys
path, server = sys.argv[1], sys.argv[2]
with open(path, encoding="utf-8") as f:
    data = json.load(f)
data["server"] = server
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
PY
fi

echo "worker in WSL, server at $SERVER"
.venv/bin/karaoke-worker run &
worker=$!
stop() {
  kill -INT "$worker" 2>/dev/null || true
  wait "$worker" 2>/dev/null || true
}
trap stop EXIT
# Blocks until the launcher on Windows goes away (or the worker ends on its own).
cat >/dev/null &
watcher=$!
wait -n "$worker" "$watcher" || true
