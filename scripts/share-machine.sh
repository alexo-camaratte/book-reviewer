# Sourced by fast-check.sh. Several project sessions share one machine, so a
# local run must not assume it owns every core. In CI the runner is ours alone.
#   TEST_WORKER_ARGS  node --test args: --test-concurrency=$SHARE_WORKERS locally, none in CI
#   heavy CMD...      run CMD under the machine-wide lock (one heavy step at a time)

SHARE_WORKERS=${SHARE_WORKERS:-2}
HEAVY_LOCK=${HEAVY_LOCK:-$HOME/.cache/gabriel-heavy.lock}
HEAVY_LOCK_WAIT=${HEAVY_LOCK_WAIT:-1800}

TEST_WORKER_ARGS=()
[[ -n "${CI:-}" ]] || TEST_WORKER_ARGS=("--test-concurrency=$SHARE_WORKERS")

# The frontend build goes through here. The lock fd is closed in the step (-o),
# so a daemon it leaves behind never keeps the lock.
heavy() {
  if [[ -n "${CI:-}" ]] || ! command -v flock >/dev/null 2>&1; then "$@"; return; fi
  mkdir -p -- "$(dirname -- "$HEAVY_LOCK")"
  local rc=0
  flock -n -o -E 75 "$HEAVY_LOCK" "$@" || rc=$?
  [[ $rc -eq 75 ]] || return "$rc"
  printf 'wait  another session holds %s; waiting up to %ss\n' "$HEAVY_LOCK" "$HEAVY_LOCK_WAIT" >&2
  rc=0
  flock -w "$HEAVY_LOCK_WAIT" -o -E 75 "$HEAVY_LOCK" "$@" || rc=$?
  [[ $rc -ne 75 ]] || printf 'FAIL  %s still held after %ss; rerun when the other session finishes\n' "$HEAVY_LOCK" "$HEAVY_LOCK_WAIT" >&2
  return "$rc"
}
