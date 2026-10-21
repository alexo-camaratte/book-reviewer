import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parent.parent / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from publish_version import ApiError, publish  # noqa: E402

REPO = 'alexo-camaratte/book-reviewer'


class PublishTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.git('init', '-q')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'user.name', 'Fixture')
        (self.root / 'frontend').mkdir()
        (self.root / 'frontend/package.json').write_text(json.dumps({'version': '0.2.0'}) + '\n')
        (self.root / 'pyproject.toml').write_text('[project]\nname = "fixture"\nversion = "0.2.0"\n')
        (self.root / 'VERSION').write_text('0.2.0\n')
        (self.root / 'CHANGELOG.md').write_text('# Changelog\n\n## [Unreleased]\n\n## [0.2.0] - 2026-10-07\n\n- Baseline.\n')
        self.commit()
        self.sha = self.git('rev-parse', 'HEAD').strip()
        self.tag = None
        self.release = None
        self.writes = []
        self.event = 'push'
        self.conclusion = 'success'
        self.required = 'success'
        self.repo = REPO
        self.unknown = False

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.root, text=True, stderr=subprocess.DEVNULL)

    def commit(self):
        self.git('add', '.')
        self.git('commit', '-qm', 'fixture')

    def api(self, method, url, payload=None, missing=False):
        if method == 'POST':
            self.writes.append((url, payload))
            if url.endswith('/git/refs'):
                self.tag = payload['sha']
            elif url.endswith('/releases'):
                self.release = payload
            else:
                raise AssertionError(url)
            if self.unknown:
                raise ApiError('response lost after successful mutation')
            return payload
        if url.endswith('/actions/workflows/ci.yml'):
            return {'id': 7}
        if url.endswith('/actions/runs/42'):
            return {'workflow_id': 7, 'head_sha': self.sha, 'event': self.event, 'head_branch': 'main', 'status': 'completed',
                    'conclusion': self.conclusion, 'head_repository': {'full_name': self.repo}}
        if '/compare/' in url:
            return {'status': 'identical', 'merge_base_commit': {'sha': self.sha}}
        if url.endswith('/jobs?per_page=100'):
            return {'total_count': 1, 'jobs': [{'name': 'Required CI', 'conclusion': self.required}]}
        if '/git/ref/tags/' in url:
            return {'object': {'type': 'commit', 'sha': self.tag}} if self.tag else None
        if '/releases/tags/' in url:
            return self.release
        raise AssertionError(url)

    def run_publish(self):
        return publish(self.root, REPO, '42', self.api)

    def test_publication_workflow_security_mutations_are_rejected(self):
        spec = importlib.util.spec_from_file_location('guard', SCRIPTS / 'verify-release-workflow.py')
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        source = (SCRIPTS.parent / '.github/workflows/release.yml').read_bytes()
        guard.validate(source)
        for old, new in [(b"event == 'push'", b"event == 'pull_request'"), (b'persist-credentials: false', b'persist-credentials: true'),
                         (b'contents: write', b'contents: read'), (b'github.event.workflow_run.head_sha', b'github.ref'),
                         (b'actions: read', b'actions: write')]:
            self.assertIn(old, source)
            with self.assertRaises(ValueError):
                guard.validate(source.replace(old, new))

    def test_publish_and_idempotent_retry(self):
        self.assertEqual(self.run_publish(), 'PUBLISHED v0.2.0')
        self.assertTrue(self.release['prerelease'])
        self.assertEqual(self.release['name'], 'Revisor v0.2.0')
        self.assertEqual(self.tag, self.sha)
        self.assertEqual(self.run_publish(), 'ALREADY_PUBLISHED v0.2.0')
        self.assertEqual(len(self.writes), 2)

    def test_pr_fork_failed_or_missing_required_never_publishes(self):
        for field, value in [('event', 'pull_request'), ('repo', 'someone/fork'), ('conclusion', 'failure'), ('required', 'skipped')]:
            previous = getattr(self, field)
            setattr(self, field, value)
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.run_publish()
            self.assertEqual(self.writes, [])
            setattr(self, field, previous)

    def test_wrong_workflow_incomplete_ci_and_nonintegrated_commit_block(self):
        cases = [('run', 'workflow_id', 99), ('run', 'status', 'in_progress'), ('run', 'head_branch', 'feature'),
                 ('compare', 'status', 'diverged'), ('compare', 'merge_base_commit', {'sha': 'c' * 40}), ('jobs', 'total_count', 101)]
        for endpoint, key, value in cases:
            def altered(method, url, payload=None, missing=False):
                data = self.api(method, url, payload, missing)
                matches = (endpoint == 'run' and url.endswith('/actions/runs/42')) or (endpoint == 'compare' and '/compare/' in url) \
                    or (endpoint == 'jobs' and '/jobs?' in url)
                if matches:
                    data[key] = value
                return data
            with self.subTest(key=key), self.assertRaises(ValueError):
                publish(self.root, REPO, '42', altered)
            self.assertEqual(self.writes, [])

    def test_wrong_ci_sha_or_dirty_checkout_blocks(self):
        self.sha = 'a' * 40
        with self.assertRaises(ValueError):
            self.run_publish()
        self.sha = self.git('rev-parse', 'HEAD').strip()
        (self.root / 'untracked').write_text('work')
        with self.assertRaises(ValueError):
            self.run_publish()
        self.assertEqual(self.writes, [])

    def test_unknown_mutation_result_reconciles_without_resend(self):
        self.unknown = True
        self.assertEqual(self.run_publish(), 'PUBLISHED v0.2.0')
        self.assertEqual(len(self.writes), 2)

    def test_conflicting_tag_never_moves(self):
        self.tag = 'b' * 40
        with self.assertRaises(ValueError):
            self.run_publish()
        self.assertEqual(self.writes, [])

    def test_changed_existing_notes_are_not_overwritten(self):
        self.run_publish()
        self.release['body'] = 'changed'
        with self.assertRaises(ValueError):
            self.run_publish()
        self.assertEqual(len(self.writes), 2)

    def test_later_prose_only_merge_does_not_retag(self):
        self.run_publish()
        old = self.tag
        (self.root / 'README.md').write_text('docs')
        self.commit()
        self.sha = self.git('rev-parse', 'HEAD').strip()
        self.assertEqual(self.run_publish(), 'ALREADY_PUBLISHED v0.2.0')
        self.assertEqual(self.tag, old)
        self.assertEqual(len(self.writes), 2)

    def test_later_docs_run_can_publish_before_earlier_version_run(self):
        earlier = self.sha
        (self.root / 'README.md').write_text('docs')
        self.commit()
        self.sha = self.git('rev-parse', 'HEAD').strip()
        self.run_publish()
        later = self.tag
        self.git('checkout', '-q', earlier)
        self.sha = earlier
        self.assertEqual(self.run_publish(), 'ALREADY_PUBLISHED v0.2.0')
        self.assertEqual(self.tag, later)
        self.assertEqual(len(self.writes), 2)

    def test_same_version_with_new_code_never_retags(self):
        self.run_publish()
        (self.root / 'backend.py').write_text('x = 1\n')
        self.commit()
        self.sha = self.git('rev-parse', 'HEAD').strip()
        with self.assertRaises(ValueError):
            self.run_publish()
        self.assertEqual(len(self.writes), 2)


if __name__ == '__main__':
    unittest.main()
