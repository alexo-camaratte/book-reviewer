#!/usr/bin/env bash
# The fast core an agent must pass before every push, and the PR check (`Required CI`):
# compile, Python tests (workflow contracts included), frontend tests, lint and build,
# without credentials or remote services.
set -Eeuo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

# Other project sessions share this machine: capped test workers locally, and
# the build queues on one machine-wide lock.
. "$ROOT_DIR/scripts/share-machine.sh"

step() { printf '\n==> %s\n' "$1"; }
step compile; python3 -m compileall -q backend tests
step 'python tests'; ./scripts/test.sh
step 'frontend tests'; node --test "${TEST_WORKER_ARGS[@]}" frontend/src/lib/*.test.ts
step lint; pnpm --dir frontend lint
step build; heavy pnpm --dir frontend build
printf '\nPASS  fast core\n'
