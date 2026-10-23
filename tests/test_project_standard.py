"""Project-standard contracts: fast-check entry point, machine sharing and CI wiring."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / 'scripts'


class FastCheckTest(unittest.TestCase):
    def test_fast_check_is_the_ci_entry_point(self):
        fast = SCRIPTS / 'fast-check.sh'
        self.assertTrue(fast.is_file(), 'scripts/fast-check.sh is the fast core')
        self.assertTrue(fast.stat().st_mode & 0o111, 'fast-check.sh must be executable')
        workflow = (ROOT / '.github/workflows/ci.yml').read_text()
        self.assertIn('./scripts/fast-check.sh', workflow)
        self.assertIn('fast-check.sh', (SCRIPTS / 'ci.sh').read_text(), 'ci.sh stays as an alias')

    def test_fast_check_shares_the_machine(self):
        text = (SCRIPTS / 'fast-check.sh').read_text()
        self.assertIn('scripts/share-machine.sh', text)
        self.assertIn('heavy pnpm --dir frontend build', text, 'the build queues on the machine lock')
        self.assertIn('TEST_WORKER_ARGS', text, 'frontend tests use the local worker cap')

    def test_ci_runs_once_per_pull_request(self):
        workflow = (ROOT / '.github/workflows/ci.yml').read_text()
        trigger = workflow.split('\non:', 1)[1].split('\njobs:', 1)[0]
        # A branch with an open PR gets only the pull_request run; push runs only on main,
        # where Publish version needs it.
        self.assertIn('\n  push:\n    branches: [main]\n', trigger)
        self.assertIn('\n  pull_request:\n', trigger)
        self.assertNotIn('[push, pull_request]', workflow)
        self.assertIn('cancel-in-progress: ${{ github.event_name == \'pull_request\' }}', workflow)
        # Outside a PR the group must be unique per commit: a shared main group would let a
        # third merge cancel the pending run of the second, and its release would never publish.
        self.assertIn('group: ci-${{ github.event.pull_request.number || github.sha }}', workflow)

    def test_pr_scope_gate_runs_on_every_pr_event(self):
        workflow = (ROOT / '.github/workflows/ci.yml').read_text()
        # Editing the body (Refs #N, Security-Review:) must re-run the gate.
        self.assertIn('types: [opened, synchronize, reopened, edited]', workflow)
        self.assertIn("if: github.event_name == 'pull_request'\n        run: python3 scripts/check-pr-scope.py", workflow)
        self.assertTrue((ROOT / 'changes/README.md').is_file())

    def test_worktrees_live_in_an_ignored_folder(self):
        # Only the committed .gitignore counts: a personal excludesFile or .git/info/exclude must not make this pass.
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(['git', 'init', '-q', '--template=', tmp], check=True, timeout=30)
            shutil.copy(ROOT / '.gitignore', Path(tmp) / '.gitignore')
            ignored = lambda path: subprocess.run(['git', '-c', 'core.excludesFile=/dev/null', 'check-ignore', '-q', '--no-index', path],
                                                  cwd=tmp, timeout=30).returncode == 0
            self.assertTrue(ignored('.claude/worktrees/fix-12/README.md'), '.claude/worktrees/ must be ignored')
            self.assertFalse(ignored('.claude/settings.json'), 'shared agent settings stay tracked')
        self.assertIn('.claude/worktrees/<tipo>-<N>', (ROOT / 'AGENTS.md').read_text())

    def test_claude_settings_contract(self):
        settings = json.loads((ROOT / '.claude/settings.json').read_text())
        self.assertEqual(settings['attribution']['commit'], '')
        self.assertEqual(settings['attribution']['pr'], '')
        self.assertIs(settings['includeCoAuthoredBy'], False)
        perms = settings['permissions']
        allow, ask, deny = set(perms['allow']), set(perms['ask']), set(perms['deny'])
        self.assertFalse(allow & ask or allow & deny or ask & deny, 'a rule lives in one list only')
        for rule in ('Bash(./scripts/fast-check.sh:*)', 'Bash(gh pr create:*)', 'Bash(gh pr merge:*)',
                     'Bash(git push origin chore/:*)', 'Bash(git worktree remove:*)'):
            self.assertIn(rule, allow)
        for rule in ('Bash(rm:*)', 'Bash(git branch -D:*)', 'Bash(python3 scripts/release_version.py cut:*)',
                     'Bash(gh pr merge * --merge*)'):
            self.assertIn(rule, ask)
        for rule in ('Bash(git push --force:*)', 'Bash(git push * --force*)', 'Bash(git push origin main:*)',
                     'Bash(git reset --hard:*)', 'Bash(rm -rf:*)', 'Bash(gh pr merge * --admin*)',
                     'Bash(git worktree remove * --f*)', 'Read(./**/.env*)', 'Edit(./.books/**)', 'Write(./.books/**)'):
            self.assertIn(rule, deny)
        # Broad pushes would bypass the narrow task-branch allows.
        self.assertFalse({'Bash(git push:*)', 'Bash(git:*)', 'Bash(gh:*)'} & allow)

    def test_share_machine_contract(self):
        result = subprocess.run(['bash', str(SCRIPTS / 'test-share-machine.sh')], cwd=ROOT,
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('PASS  share-machine', result.stdout)


if __name__ == '__main__':
    unittest.main()
