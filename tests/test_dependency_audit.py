"""Dependency audit verdicts: vulnerability per level vs. audit source outage, fail closed."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parent.parent / 'scripts' / 'dependency-audit.py'
spec = importlib.util.spec_from_file_location('dependency_audit', SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def pnpm(**counts):
    levels = {name: 0 for name in mod.LEVELS} | counts
    return json.dumps({'advisories': {}, 'metadata': {'vulnerabilities': levels}})


def pip(*vulns):
    return json.dumps({'dependencies': [{'name': 'pkg', 'version': '1.0', 'vulns': [{'id': v} for v in vulns]}], 'fixes': []})


class DependencyAuditTest(unittest.TestCase):
    def test_pnpm_verdict_comes_from_counts_at_or_above_the_level(self):
        self.assertEqual(mod.classify_pnpm(0, pnpm(), '', 'moderate')[0], 'ok')
        # pnpm 10 exits 1 on any advisory: below the level is still clean.
        self.assertEqual(mod.classify_pnpm(1, pnpm(low=3, info=1), '', 'moderate')[0], 'ok')
        for level in ('moderate', 'high', 'critical'):
            with self.subTest(level=level):
                self.assertEqual(mod.classify_pnpm(1, pnpm(**{level: 1}), '', 'moderate')[0], 'vulnerable')
        state, detail = mod.classify_pnpm(1, pnpm(high=2, low=1), '', 'moderate')
        self.assertEqual(state, 'vulnerable')
        self.assertEqual(detail, 'critical 0, high 2, moderate 0, low 1, info 0')

    def test_pnpm_fails_closed_on_broken_reports(self):
        for code, out in [(2, pnpm()), (1, json.dumps({'metadata': {}})), (1, json.dumps({'metadata': {'vulnerabilities': {'high': '1'}}})),
                          (1, json.dumps({'metadata': {'vulnerabilities': {}}, 'error': {'code': 'X'}})), (1, 'not json')]:
            with self.subTest(code=code, out=out):
                self.assertEqual(mod.classify_pnpm(code, out, '', 'moderate')[0], 'failed')

    def test_outages_are_unavailable_not_clean(self):
        self.assertEqual(mod.classify_pnpm(None, '', 'no answer within 1s', 'moderate')[0], 'unavailable')
        self.assertEqual(mod.classify_pnpm(1, '', 'request to registry responded with 503', 'moderate')[0], 'unavailable')
        self.assertEqual(mod.classify_pnpm(1, '', 'ETIMEDOUT', 'moderate')[0], 'unavailable')
        self.assertEqual(mod.classify_pip(None, '', 'no answer within 1s')[0], 'unavailable')
        self.assertEqual(mod.classify_pip(1, '', 'requests.exceptions.ConnectionError: Max retries exceeded')[0], 'unavailable')

    def test_pip_any_finding_fails_and_broken_reports_fail_closed(self):
        self.assertEqual(mod.classify_pip(0, json.dumps({'dependencies': [], 'fixes': []}), '')[0], 'ok')
        state, detail = mod.classify_pip(1, pip('PYSEC-1', 'PYSEC-1', 'GHSA-2'), '')
        self.assertEqual(state, 'vulnerable')
        self.assertEqual(detail, 'unrated: pkg GHSA-2, pkg PYSEC-1')
        for code, out in [(1, pip()), (0, pip('PYSEC-1')), (2, pip()), (1, 'Traceback'), (0, json.dumps({'dependencies': 'x'}))]:
            with self.subTest(code=code, out=out):
                self.assertEqual(mod.classify_pip(code, out, '')[0], 'failed')

    def test_skipped_backend_dependency_is_not_clean(self):
        skipped = json.dumps({'dependencies': [{'name': 'x', 'skip_reason': 'not on PyPI'}], 'fixes': []})
        self.assertEqual(mod.classify_pip(0, skipped, '')[0], 'failed')

    def test_only_the_final_error_decides_an_outage(self):
        # A retry warning followed by an unrelated crash is a broken audit, not an outage.
        err = 'WARNING: Retrying after NewConnectionError ECONNRESET\nTraceback (most recent call last):\nRuntimeError: build failed\n'
        self.assertEqual(mod.classify_pip(1, '', err)[0], 'failed')
        self.assertEqual(mod.classify_pnpm(1, '', err, 'moderate')[0], 'failed')
        self.assertEqual(mod.classify_pip(1, '', 'Traceback\nrequests.exceptions.ConnectionError: Max retries exceeded\n')[0], 'unavailable')

    def test_backend_audit_is_strict(self):
        commands = []
        def runner(command, timeout):
            commands.append(command)
            return 0, pnpm() if command[0] == 'pnpm' else json.dumps({'dependencies': [], 'fixes': []}), ''
        with contextlib.redirect_stdout(io.StringIO()):
            mod.main([], runner)
        self.assertIn('--strict', commands[1])

    def run_main(self, frontend, backend, *args):
        def runner(command, timeout):
            return frontend if command[0] == 'pnpm' else backend
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = mod.main(list(args), runner)
        return code, out.getvalue() + err.getvalue()

    def test_overall_verdict_and_exit_codes(self):
        clean_pip = (0, json.dumps({'dependencies': [], 'fixes': []}), '')
        outage = (None, '', 'no answer within 1s')
        code, text = self.run_main((0, pnpm(), ''), clean_pip)
        self.assertEqual(code, 0)
        self.assertIn('frontend  ok', text)
        self.assertIn('backend   ok', text)
        self.assertEqual(self.run_main((1, pnpm(high=1), ''), clean_pip)[0], 1)
        self.assertEqual(self.run_main((0, pnpm(), ''), (1, pip('PYSEC-1'), ''))[0], 1)
        self.assertEqual(self.run_main(outage, clean_pip)[0], 3)
        self.assertEqual(self.run_main(outage, clean_pip, '--soft-unavailable')[0], 0)
        # An outage never hides a real finding or a broken audit in the other source.
        self.assertEqual(self.run_main(outage, (1, pip('PYSEC-1'), ''), '--soft-unavailable')[0], 1)
        self.assertEqual(self.run_main(outage, (2, 'Traceback', ''), '--soft-unavailable')[0], 1)
        self.assertEqual(self.run_main((1, pnpm(low=1), ''), clean_pip, '--level', 'low')[0], 1)
        for args in (('--level', 'bogus'), ('--level',), ('--level=bogus',), ('--soft',)):
            with self.subTest(args=args):
                self.assertEqual(self.run_main((0, pnpm(), ''), clean_pip, *args)[0], 1)
        self.assertEqual(self.run_main((1, pnpm(moderate=1), ''), clean_pip, '--level', 'high')[0], 0)
        self.assertEqual(self.run_main((1, pnpm(moderate=1), ''), clean_pip, '--level=high')[0], 0)
        self.assertEqual(self.run_main((1, pnpm(high=1), ''), clean_pip, '--level=high')[0], 1)

    def test_ci_runs_the_audit(self):
        workflow = (SCRIPT.parent.parent / '.github/workflows/ci.yml').read_text()
        self.assertIn('python3 scripts/dependency-audit.py --soft-unavailable', workflow)
        self.assertIn('pip-audit', workflow)


if __name__ == '__main__':
    unittest.main()
