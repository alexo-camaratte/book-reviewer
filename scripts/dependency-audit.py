#!/usr/bin/env python3
"""Dependency audit of the frontend (pnpm) and the backend (pip-audit), with a verdict per
source that tells a vulnerability apart from an audit source outage.

  python3 scripts/dependency-audit.py [--soft-unavailable] [--level moderate]

Frontend: `pnpm --dir frontend audit --json --prod`. pnpm 10 with --json exits 1 on any
advisory and ignores --audit-level, so the verdict comes from metadata.vulnerabilities,
summing the levels at or above --level. Missing or non-numeric counts fail closed.
Backend: pip-audit over the [project].dependencies of pyproject.toml. pip-audit reports
no severity, so any backend finding is unrated and fails at every level.

Exit 0: clean. Exit 1: vulnerability found or unexpected failure (fail closed).
Exit 3: an audit source timed out or answered 5xx/network error and nothing failed;
with --soft-unavailable that outage is a warning and exits 0.
Writes audit=ok|vulnerable|unavailable|failed to $GITHUB_OUTPUT when set.
"""
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parent.parent
LEVELS = ('info', 'low', 'moderate', 'high', 'critical')
UNAVAILABLE = re.compile(
    r'responded with 5\d\d|ETIMEDOUT|ESOCKETTIMEDOUT|ECONNRESET|ECONNREFUSED|EAI_AGAIN|ENOTFOUND'
    r'|ERR_SOCKET_TIMEOUT|UND_ERR_CONNECT_TIMEOUT|UND_ERR_HEADERS_TIMEOUT|socket hang up'
    r'|ConnectionError|ConnectTimeout|ReadTimeout|Max retries exceeded|Temporary failure in name resolution'
    r'|HTTPError: 5\d\d|Service Unavailable')
# Fail closed: a vulnerability or a broken audit blocks; an outage alone only warns.
SEVERITY = ('ok', 'unavailable', 'failed', 'vulnerable')


def run(command, timeout):
    proc = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            start_new_session=True)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        return None, '', f'no answer within {timeout}s'
    return proc.returncode, out, err


def classify_pnpm(code, out, err, level):
    """(state, detail). Counts by level; only levels at or above `level` decide."""
    if code is None:
        return 'unavailable', err
    try:
        report = json.loads(out)
    except ValueError:
        report = None
    if isinstance(report, dict) and 'metadata' in report and 'error' not in report:
        if code not in (0, 1):
            return 'failed', f'exit {code}'
        found = report['metadata'].get('vulnerabilities') if isinstance(report['metadata'], dict) else None
        counts = {name: found.get(name) for name in LEVELS} if isinstance(found, dict) else {}
        if not all(type(counts.get(name)) is int and counts[name] >= 0 for name in LEVELS):
            return 'failed', 'metadata.vulnerabilities missing or not numeric'
        detail = ', '.join(f'{name} {counts[name]}' for name in reversed(LEVELS))
        blocking = sum(counts[name] for name in LEVELS[LEVELS.index(level):])
        return ('vulnerable' if blocking else 'ok'), detail
    return ('unavailable' if UNAVAILABLE.search(out + err) else 'failed'), (err.strip() or out.strip())[-500:]


def classify_pip(code, out, err):
    """(state, detail). pip-audit has no severity: every finding counts."""
    if code is None:
        return 'unavailable', err
    try:
        report = json.loads(out)
    except ValueError:
        report = None
    deps = report.get('dependencies') if isinstance(report, dict) else None
    if isinstance(deps, list) and all(isinstance(d, dict) and isinstance(d.get('vulns', []), list) for d in deps):
        found = sorted({(d.get('name'), v.get('id')) for d in deps for v in d.get('vulns', []) if isinstance(v, dict)})
        if code == 0 and not found:
            return 'ok', f'{len(deps)} dependencies, 0 vulnerabilities'
        if code == 1 and found:
            return 'vulnerable', 'unrated: ' + ', '.join(f'{name} {vuln}' for name, vuln in found)
        return 'failed', f'exit {code} with {len(found)} findings'
    return ('unavailable' if UNAVAILABLE.search(out + err) else 'failed'), (err.strip() or out.strip())[-500:]


def backend_requirements():
    return tomllib.loads((ROOT / 'pyproject.toml').read_text())['project'].get('dependencies', [])


def audit(level, timeout, runner=run):
    results = {'frontend': classify_pnpm(*runner(['pnpm', '--dir', 'frontend', 'audit', '--json', '--prod'], timeout), level)}
    with tempfile.NamedTemporaryFile('w', suffix='.txt') as requirements:
        requirements.write(''.join(f'{line}\n' for line in backend_requirements()))
        requirements.flush()
        command = [sys.executable, '-m', 'pip_audit', '--format', 'json', '--progress-spinner', 'off', '-r', requirements.name]
        results['backend'] = classify_pip(*runner(command, timeout))
    return results


def main(argv, runner=run):
    soft = '--soft-unavailable' in argv
    level = argv[argv.index('--level') + 1] if '--level' in argv[:-1] else 'moderate'
    if level not in LEVELS:
        print(f'FAIL  unknown --level {level}', file=sys.stderr)
        return 1
    results = audit(level, int(os.environ.get('AUDIT_TIMEOUT', '120')), runner)
    state = max((s for s, _ in results.values()), key=SEVERITY.index)
    for source, (verdict, detail) in results.items():
        print(f'{source:9} {verdict:11} {detail}')
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as handle:
            handle.write(f'audit={state}\n')
    if state == 'ok':
        print(f'PASS  dependency audit (frontend --prod at or above {level}; backend any finding)')
        return 0
    if state == 'unavailable':
        print('WARN  audit source unavailable; rerun when it answers', file=sys.stderr)
        if soft:
            print('::warning title=audit indisponível::audit source unavailable; no vulnerability verdict for this run')
            return 0
        return 3
    print(f'FAIL  dependency audit: {state}', file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
