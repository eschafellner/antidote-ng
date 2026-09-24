#!/usr/bin/env bash
# Kompatibler Einstiegspunkt; die Deployment-Logik liegt im Projektstamm.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec bash "$SCRIPT_DIR/deploy.sh" "$@"
