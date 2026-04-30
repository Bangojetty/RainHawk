#!/usr/bin/env bash
cd "$(dirname "$0")"
exec .venv/Scripts/python.exe -m frontend.server "$@"
