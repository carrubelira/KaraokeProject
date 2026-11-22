#!/usr/bin/env bash
# Starts the karaoke on this Linux machine: the server (with kp-audio) and a worker.
# Everything is in scripts/start.py; options: --no-worker, --no-audio, --fake, --port, --setup.
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
if ! command -v uv >/dev/null; then
  echo "uv is missing: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
  exit 1
fi
exec uv run --quiet --no-project --python 3.12 scripts/start.py "$@"
