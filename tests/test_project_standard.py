"""Project-standard contracts: fast-check entry point, machine sharing and CI wiring."""
from pathlib import Path
import subprocess
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

    def test_share_machine_contract(self):
        result = subprocess.run(['bash', str(SCRIPTS / 'test-share-machine.sh')], cwd=ROOT,
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('PASS  share-machine', result.stdout)


if __name__ == '__main__':
    unittest.main()
