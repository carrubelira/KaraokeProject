# Starts the karaoke on this Windows machine: the server (with kp-audio, its sound) and a worker.
# Everything is in scripts/start.py; options: --no-worker, --no-audio, --fake, --port, --setup.
Set-Location (Split-Path -Parent $PSScriptRoot)
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host 'uv is missing: winget install astral-sh.uv'
    exit 1
}
# Not 'Stop': Windows PowerShell would take uv's notes on stderr for errors.
$ErrorActionPreference = 'Continue'
& uv run --quiet --no-project --python 3.12 scripts/start.py @args
exit $LASTEXITCODE
