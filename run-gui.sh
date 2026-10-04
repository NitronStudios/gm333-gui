#!/usr/bin/env bash
#
# Quick launcher to run GM333 GUI directly without installing
#

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$DIR:$PYTHONPATH"
exec python3 -m gm333gui "$@"
