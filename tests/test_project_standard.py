"""Project-standard contracts: fast-check entry point, machine sharing and CI wiring."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / 'scripts'


def matches(rule, command):
    """Claude Code Bash rule semantics: a trailing ':*' means ' *' (or the bare command), '*' matches anything."""
    if not (rule.startswith('Bash(') and rule.endswith(')')):
        return False
    pattern = rule[5:-1]
    if pattern.endswith(':*'):
        if command == pattern[:-2]:
            return True
        pattern = pattern[:-2] + ' *'
    return re.fullmatch('.*'.join(map(re.escape, pattern.split('*'))), command, re.S) is not None


def decide(perms, command):
    for verdict in ('deny', 'ask', 'allow'):
        if any(matches(rule, command) for rule in perms[verdict]):
            return verdict
    return 'prompt'


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
        self.assertNotIn('enabledPlugins', settings, 'skill installation stays in the personal environment')
        self.assertNotIn('extraKnownMarketplaces', settings)
        perms = settings['permissions']
        self.assertFalse(set(perms['allow']) & set(perms['ask']) or set(perms['allow']) & set(perms['deny'])
                         or set(perms['ask']) & set(perms['deny']), 'a rule lives in one list only')
        # Real commands, decided with the documented semantics, not by string presence.
        cases = {
            'allow': ['./scripts/fast-check.sh', 'python3 -m unittest discover -s tests', 'gh pr view 14 --repo o/r',
                      'git fetch --prune origin',
                      'git worktree add -b chore/6-x .claude/worktrees/chore-6 origin/main',
                      'git worktree remove .claude/worktrees/chore-6', 'pnpm --dir frontend build'],
            'ask': ['gh pr merge 14 --repo o/r --squash', 'gh pr create --body-file body.md', 'gh issue comment 6 --body-file x.md',
                    'rm notes.txt', 'git branch -D chore/6-x', './scripts/jail.sh ./scripts/test.sh',
                    './scripts/jail.sh git -C /workspace status', 'python3 scripts/release_version.py cut --bump patch',
                    ],
            'deny': ['git push -u origin chore/x:main', 'git push origin chore/x +HEAD:y', 'git push -u origin chore/x:refs/tags/v9',
                     'git push --force origin chore/x', 'git push -u origin chore/x --force-with-lease', 'git push origin chore/x main',
                     'git push origin --delete chore/x', 'git push origin chore/x --tags',
                     'git -C wt push --force origin chore/x', 'git -C wt push -u origin chore/x:main', 'git -C wt reset --hard',
                     'git -C wt clean -fdx', 'git clean -fdx', 'git stash', 'git diff --output=out.txt', 'git diff --no-index /dev/null x',
                     'git fetch --upload-pack=evil .', 'git add -f .', 'git -C wt add --force .', 'bandit -r backend -o out.json',
                     'gh pr merge 14 --squash --admin', 'rm -rf build', 'git worktree remove --force .claude/worktrees/x',
                     'git -C wt worktree remove -f x', './scripts/jail.sh rm -rf /workspace/.books', 'cat .env',
                     'gh issue comment 6 --body-file /home/u/repo/.env', 'gh pr create --body-file=.books/a/b.json',
                     'sudo true', 'gh secret list',
                     'git -c core.fsmonitor=evil status',
                     'git worktree add -b x .claude/worktrees/../../x origin/main', 'git worktree remove .claude/worktrees/../../x',
                     'git worktree add -b x -f .claude/worktrees/x origin/main'],
        }
        for expected, commands in cases.items():
            for command in commands:
                with self.subTest(command=command):
                    self.assertEqual(decide(perms, command), expected)
        # Anything else falls back to the default prompt, e.g. a push of main or a branch -d.
        # Pushes always ask (AGENTS.md: push only with specific authorization), including refspecs to other branches.
        for command in ('git push origin main', 'git switch -c x', 'git branch -d x', 'gh api repos/o/r',
                        'git push -u origin chore/6-x', 'git push origin chore/6-x:other', 'git -C wt push -u origin chore/6-x',
                        'git add changes/6-fix-thing.md', 'python3 -m unittest discover -s /tmp/x',
                        'git -C wt -c remote.origin.receivepack=evil push origin chore/6-x'):
            with self.subTest(command=command):
                self.assertIn(decide(perms, command), ('prompt', 'deny'))
        self.assertEqual(decide(perms, 'git add changes/6-fix-thing.md'), 'prompt', 'a slug with -f is not a force flag')

    def test_share_machine_contract(self):
        result = subprocess.run(['bash', str(SCRIPTS / 'test-share-machine.sh')], cwd=ROOT,
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('PASS  share-machine', result.stdout)


if __name__ == '__main__':
    unittest.main()
