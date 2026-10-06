#!/usr/bin/env sh
# LMW launcher for macOS/Linux. Usage: ./lmw.sh run "request" -w ./my-site
DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHONPATH="$DIR${PYTHONPATH:+:$PYTHONPATH}" exec python3 -m lmw "$@"
