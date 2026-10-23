"""PR scope gate: task PRs add exactly one changes/<N>-<slug>.md; only a VERSION bump edits CHANGELOG.md."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parent.parent / 'scripts' / 'check-pr-scope.py'
LOG = '# Changelog\n\n## [Unreleased]\n\n## [0.1.4] - 2026-10-15\n\n- X.\n'
RELEASE_BODY = 'Refs #20\nSecurity-Review: version bump only'


class CheckPrScopeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'user.name', 'Fixture')

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.dir), *args], check=True, capture_output=True, text=True).stdout.strip()

    def commit(self, files=None, deleted=(), message='c'):
        for name, text in (files or {}).items():
            (self.dir / name).parent.mkdir(parents=True, exist_ok=True)
            (self.dir / name).write_text(text)
        for name in deleted:
            (self.dir / name).unlink()
        self.git('add', '-A')
        self.git('commit', '-qm', message)
        return self.git('rev-parse', 'HEAD')

    def scope(self, files=None, deleted=(), branch='fix/12-audit-level', body=None, notes=(), main_after=None):
        self.commit({'VERSION': '0.1.4\n', 'CHANGELOG.md': LOG, 'changes/README.md': '# Notas\n',
                     **{f'changes/{n}': '- Old.\n' for n in notes}}, message='base')
        self.git('checkout', '-qb', branch)
        head = self.commit(files, deleted, 'task')
        self.git('checkout', '-q', 'main')
        if main_after:
            self.commit(main_after, message='parallel')
        event = self.dir / '.git' / 'event.json'
        issue = branch.split('/')[1].split('-')[0]
        event.write_text(json.dumps({'pull_request': {
            'head': {'ref': branch, 'sha': head}, 'base': {'sha': self.git('rev-parse', 'main')},
            'body': f'Refs #{issue}' if body is None else body}}))
        return subprocess.run([sys.executable, str(SCRIPT)], cwd=self.dir, capture_output=True, text=True,
                              env={'GITHUB_EVENT_PATH': str(event), 'PATH': '/usr/bin:/bin'}, timeout=30)

    def assertRefused(self, result, text=''):
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(text, result.stderr)

    def test_task_with_its_own_note_passes(self):
        result = self.scope({'backend/a.py': 'a\n', 'changes/12-audit-level.md': '- A.\n'})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('PASS', result.stdout)

    def test_editing_its_own_note_passes(self):
        result = self.scope({'changes/12-audit-level.md': '- B.\n', 'changes/README.md': '# Notas 2\n'},
                            notes=['12-audit-level.md'])
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_task_without_note_is_refused(self):
        self.assertRefused(self.scope({'backend/a.py': 'a\n'}), 'changes/12-')

    def test_exactly_one_own_note(self):
        for files, deleted, notes in (
                ({'changes/13-other.md': '- A.\n'}, (), ()),
                ({'changes/12-a.md': '- A.\n', 'changes/12-b.md': '- B.\n'}, (), ()),
                ({'changes/12-a.md': '- A.\n', 'changes/7-old.md': '- C.\n'}, (), ['7-old.md']),
                ({'changes/12-a.md': '- A.\n'}, ['changes/7-old.md'], ['7-old.md']),
                ({'changes/12_Audit.md': '- A.\n'}, (), ())):
            with self.subTest(files=files, deleted=deleted):
                self.setUp()
                self.assertRefused(self.scope(files, deleted, notes=notes))

    def test_task_touching_changelog_is_refused(self):
        result = self.scope({'changes/12-a.md': '- A.\n', 'CHANGELOG.md': LOG + '\n- Nova.\n'})
        self.assertRefused(result, 'CHANGELOG.md')

    def test_branch_must_name_an_issue(self):
        for branch in ('release/20-v0-2-0', 'claude/20-x', 'chore/project-standard'):
            with self.subTest(branch=branch):
                self.setUp()
                self.assertRefused(self.scope({'changes/20-a.md': '- A.\n'}, branch=branch, body='Refs #20'), 'Refs #N')

    def test_version_bump_is_the_release_and_consumes_every_note(self):
        bump = {'VERSION': '0.1.5\n', 'CHANGELOG.md': LOG.replace('## [0.1.4]', '## [0.1.5] - 2026-10-22\n\n- Y.\n\n## [0.1.4]')}
        notes = ['7-a.md', '9-b.md']
        ok = self.scope(bump, ['changes/7-a.md', 'changes/9-b.md'], branch='chore/20-release', notes=notes, body=RELEASE_BODY)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.setUp()
        self.assertRefused(self.scope(bump, ['changes/7-a.md'], branch='chore/20-release', notes=notes, body=RELEASE_BODY), '9-b')
        self.setUp()
        self.assertRefused(self.scope({**bump, 'changes/20-x.md': '- X.\n'}, branch='chore/20-release', body=RELEASE_BODY))

    def test_release_must_raise_the_version(self):
        for version in ('0.1.3', '0.1.4-rc.1', 'x'):
            with self.subTest(version=version):
                self.setUp()
                result = self.scope({'VERSION': version + '\n', 'backend/a.py': 'a\n'}, branch='chore/20-release', body=RELEASE_BODY)
                self.assertRefused(result, 'VERSION')

    def test_sensitive_paths_require_a_security_review_line(self):
        for path in ('.github/workflows/ci.yml', 'scripts/fast-check.sh', 'frontend/package.json', '.claude/settings.json',
                     'AGENTS.md', 'CLAUDE.md', 'RELEASES.md', 'bin', '.claude'):
            with self.subTest(path=path):
                self.setUp()
                files = {path: 'x\n', 'changes/12-a.md': '- A.\n'}
                self.assertRefused(self.scope(files), 'Security-Review:')
                for body in ('Refs #12\nSecurity-Review:', 'Refs #12\nSecurity-Review:   ', 'Refs #12 Security-Review: x'):
                    self.setUp()
                    self.assertRefused(self.scope(files, body=body), 'Security-Review:')
                self.setUp()
                ok = self.scope(files, body='Refs #12\n\nSecurity-Review: no new token, gate or permission\n')
                self.assertEqual(ok.returncode, 0, ok.stderr)

    def test_lockfile_and_nested_docs_need_no_security_review_line(self):
        for path in ('frontend/pnpm-lock.yaml', 'docs/AGENTS.md', 'frontend/src/scripts/x.ts'):
            with self.subTest(path=path):
                self.setUp()
                result = self.scope({path: 'x\n', 'changes/12-a.md': '- A.\n'})
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_release_bump_also_needs_the_security_review_line(self):
        bump = {'VERSION': '0.1.5\n', 'frontend/package.json': '{"version": "0.1.5"}\n'}
        self.assertRefused(self.scope(bump, branch='chore/20-release'), 'Security-Review:')

    def test_parallel_note_merged_into_main_is_not_this_prs_change(self):
        result = self.scope({'changes/12-a.md': '- A.\n'}, main_after={'changes/600-b.md': '- B.\n'})
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_every_closing_keyword_form_is_refused(self):
        for body in ('Refs #12\nCloses: #12', 'Refs #12\nFixes alexo-camaratte/book-reviewer#12',
                     'Refs #12\nResolves https://github.com/alexo-camaratte/book-reviewer/issues/12', 'Refs #12\nclose #3'):
            with self.subTest(body=body):
                self.setUp()
                self.assertRefused(self.scope({'changes/12-a.md': '- A.\n'}, body=body), 'closing keyword')

    def test_release_pr_must_be_up_to_date_with_main(self):
        # A note merged into main after the release branched would stay pending on main.
        bump = {'VERSION': '0.1.5\n', 'CHANGELOG.md': LOG.replace('## [0.1.4]', '## [0.1.5] - 2026-10-22\n\n- Y.\n\n## [0.1.4]')}
        result = self.scope(bump, ['changes/7-a.md'], branch='chore/20-release', notes=['7-a.md'], body=RELEASE_BODY,
                            main_after={'changes/11-late.md': '- Late.\n'})
        self.assertRefused(result, 'up to date')

    def test_release_pr_carries_only_release_files(self):
        bump = {'VERSION': '0.1.5\n', 'CHANGELOG.md': LOG.replace('## [0.1.4]', '## [0.1.5] - 2026-10-22\n\n- Y.\n\n## [0.1.4]')}
        result = self.scope({**bump, 'backend/a.py': 'a\n'}, ['changes/7-a.md'], branch='chore/20-release', notes=['7-a.md'],
                            body=RELEASE_BODY)
        self.assertRefused(result, 'backend/a.py')

    def test_refs_closing_keyword_and_env_files(self):
        self.assertRefused(self.scope({'changes/12-a.md': '- A.\n'}, body='Refs #13'))
        self.setUp()
        self.assertRefused(self.scope({'changes/12-a.md': '- A.\n'}, body='Refs #12\nCloses #12'))
        self.setUp()
        self.assertRefused(self.scope({'changes/12-a.md': '- A.\n', '.env.local': 'X=1\n'}))


if __name__ == '__main__':
    unittest.main()
