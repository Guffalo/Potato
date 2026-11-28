#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
echo ""
echo "  =========================================="
echo "    POTATO - LAN Media Hub & TV Transmitter"
echo "    Created by Guffalo (GPL-3.0-or-later)"
echo "  =========================================="
echo ""
if command -v python3 >/dev/null 2>&1; then
  exec python3 potato.py --open "$@"
else
  echo "[!] Python 3 is required. Install python3 and run ./start_potato.sh again."
  exit 1
fi
