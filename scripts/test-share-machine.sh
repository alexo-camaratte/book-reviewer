#!/usr/bin/env bash
# Regression cases for share-machine.sh: capped local test workers and the
# machine-wide lock that queues heavy steps across project sessions.
set -Eeuo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
LIB="$ROOT_DIR/scripts/share-machine.sh"
WORK=$(mktemp -d)
trap 'rm -rf -- "$WORK"' EXIT
fail() { printf 'FAIL  %s\n' "$1" >&2; exit 1; }

LOCK="$WORK/cache/heavy.lock"
lib() { # [VAR=value...] -- command...; runs command with the library sourced, outside CI
  local vars=()
  while [[ $1 != -- ]]; do vars+=("$1"); shift; done
  shift
  env -u CI HOME="$WORK/home" HEAVY_LOCK="$LOCK" "${vars[@]}" bash -c '. "$1"; shift; "$@"' _ "$LIB" "$@"
}
workers() { lib "$@" -- eval 'printf "%s" "${TEST_WORKER_ARGS[*]}"'; }

# Local runs cap the test workers; CI keeps every core.
[[ $(workers) == '--test-concurrency=2' ]] || fail "local default must cap workers, got '$(workers)'"
[[ $(workers SHARE_WORKERS=3) == '--test-concurrency=3' ]] || fail 'SHARE_WORKERS must set the cap'
[[ -z $(workers CI=true) ]] || fail 'CI must not cap workers'

# Two heavy steps from different sessions never overlap; the second one waits and says so.
busy=(sh -c 'mkdir "$1" || exit 9; sleep 1; rmdir "$1"' _ "$WORK/busy")
lib -- heavy "${busy[@]}" >"$WORK/h1.log" 2>&1 & pid1=$!
lib -- heavy "${busy[@]}" >"$WORK/h2.log" 2>&1 & pid2=$!
wait "$pid1" || fail "first heavy step: $(cat "$WORK/h1.log")"
wait "$pid2" || fail "second heavy step: $(cat "$WORK/h2.log")"
grep -q 'wait' "$WORK/h1.log" "$WORK/h2.log" || fail 'the queued session must say it is waiting'

# The wait is bounded: a lock held too long fails clearly and the step never runs.
flock "$LOCK" sleep 3 & holder=$!
until ! flock -n "$LOCK" true; do sleep 0.1; done
if out=$(lib HEAVY_LOCK_WAIT=1 -- heavy touch "$WORK/ran" 2>&1); then fail 'a held lock must time out'; fi
[[ "$out" == *'still held'* ]] || fail "unexpected timeout output: $out"
[[ ! -e "$WORK/ran" ]] || fail 'the step must not run without the lock'

# CI runners are not shared: no lock there.
lib CI=true HEAVY_LOCK_WAIT=1 -- heavy true || fail 'CI must not wait for the machine lock'
wait "$holder"

# The step's own exit code comes back unchanged.
rc=0; lib -- heavy sh -c 'exit 3' || rc=$?
[[ $rc -eq 3 ]] || fail "heavy must return the step's exit code, got $rc"

# A daemon left behind by a heavy step does not keep the lock.
lib -- heavy sh -c 'sleep 3 >/dev/null 2>&1 &' || fail 'heavy step with a background child'
out=$(lib HEAVY_LOCK_WAIT=1 -- heavy true 2>&1) || fail "lock leaked to a child process: $out"

printf 'PASS  share-machine\n'
