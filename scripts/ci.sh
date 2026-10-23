#!/usr/bin/env bash
# Kept for older docs and habits; the fast core lives in fast-check.sh.
set -euo pipefail
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/fast-check.sh" "$@"
