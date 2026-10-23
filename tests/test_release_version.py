import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
import release_version as mod  # noqa: E402

PYPROJECT = '[project]\nname = "fixture"\nversion = "{v}"\n'


class VersionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.git('init', '-q')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'user.name', 'Fixture')
        (self.root / 'frontend').mkdir()
        self.write_version('0.2.0')
        (self.root / 'CHANGELOG.md').write_text('# Changelog\n\n## [Unreleased]\n\n## [0.2.0] - 2026-10-07\n\n### Adicionado\n\n- Baseline.\n')
        self.commit()
        self.base = self.git('rev-parse', 'HEAD').strip()

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.root, text=True, stderr=subprocess.DEVNULL)

    def commit(self):
        self.git('add', '.')
        self.git('commit', '-qm', 'fixture')

    def write_version(self, version, package=None, pyproject=None):
        (self.root / 'VERSION').write_text(version + '\n')
        (self.root / 'frontend/package.json').write_text(json.dumps({'name': 'f', 'version': package or version}) + '\n')
        (self.root / 'pyproject.toml').write_text(PYPROJECT.format(v=pyproject or version))

    def add_note(self, name='1-fix.md', text='### Corrigido\n- Corrige comportamento.\n'):
        (self.root / 'changes').mkdir(exist_ok=True)
        (self.root / 'changes' / name).write_text(text)

    def test_cut_updates_every_source_and_validates(self):
        self.add_note()
        (self.root / 'backend.py').write_text('x = 1\n')
        self.assertEqual(mod.cut(self.root, 'patch'), '0.2.1')
        self.commit()
        self.assertEqual(mod.check(self.root, self.base, 'HEAD'), '0.2.1')
        self.assertEqual(json.loads((self.root / 'frontend/package.json').read_text())['version'], '0.2.1')
        self.assertIn('version = "0.2.1"', (self.root / 'pyproject.toml').read_text())

    def test_cut_is_allowed_on_main(self):
        self.git('branch', '-M', 'main')
        self.add_note()
        self.assertEqual(mod.cut(self.root, 'minor'), '0.3.0')

    def test_code_without_note_is_rejected(self):
        (self.root / 'backend.py').write_text('x = 1\n')
        self.commit()
        with self.assertRaises(ValueError):
            mod.check(self.root, self.base, 'HEAD')

    def test_task_with_note_needs_no_version(self):
        (self.root / 'backend.py').write_text('x = 1\n')
        self.add_note('3-task.md')
        self.commit()
        self.assertEqual(mod.check(self.root, self.base, 'HEAD'), '0.2.0')
        self.assertEqual(mod.pending_notes(self.root, 'HEAD'), ['changes/3-task.md'])

    def test_task_cannot_edit_changelog_or_delete_notes(self):
        self.add_note('3-task.md')
        p = self.root / 'CHANGELOG.md'
        p.write_text(p.read_text().replace('- Baseline.', '- Baseline.\n- Extra.'))
        self.commit()
        with self.assertRaises(ValueError):
            mod.check(self.root, self.base, 'HEAD')
        self.setUp()
        self.add_note('3-task.md')
        self.commit()
        task = self.git('rev-parse', 'HEAD').strip()
        (self.root / 'changes/3-task.md').unlink()
        (self.root / 'backend.py').write_text('x = 1\n')
        self.add_note('4-other.md')
        self.commit()
        with self.assertRaises(ValueError):
            mod.check(self.root, task, 'HEAD')

    def test_invalid_notes_are_rejected(self):
        for name, text in [('1_Fix.md', '- A.\n'), ('fix.md', '- A.\n'), ('1-fix.txt', '- A.\n'),
                           ('1-fix.md', ''), ('1-fix.md', 'Texto solto.\n'), ('1-fix.md', '### Outro\n- A.\n'),
                           ('1-fix.md', '  continuação sem item\n'), ('1-fix.md', '## [9.9.9] - 2026-01-01\n- A.\n')]:
            with self.subTest(name=name, text=text):
                self.setUp()
                (self.root / 'backend.py').write_text('x = 1\n')
                self.add_note(name, text)
                self.add_note('2-valid.md', '- Válida.\n')
                self.commit()
                with self.assertRaisesRegex(ValueError, 'invalid note|empty note|continuation'):
                    mod.check(self.root, self.base, 'HEAD')

    def test_symlinked_notes_are_rejected(self):
        (self.root / 'changes').mkdir()
        (self.root / 'changes/12-x.md').symlink_to('- A.')
        (self.root / 'backend.py').write_text('x = 1\n')
        self.commit()
        with self.assertRaisesRegex(ValueError, 'regular file'):
            mod.check(self.root, self.base, 'HEAD')
        with self.assertRaisesRegex(ValueError, 'regular file'):
            mod.pending_notes(self.root)

    def test_cut_groups_notes_by_category_in_issue_order_and_deletes_them(self):
        self.add_note('10-b.md', '### Corrigido\n- Dez.\n  Continua.\n')
        self.add_note('9-a.md', '- Sem categoria.\n\n### Corrigido\n- Nove.\n\n### Adicionado\n- Novo.\n')
        (self.root / 'changes/README.md').write_text('# Notas\n')
        self.commit()
        task = self.git('rev-parse', 'HEAD').strip()
        self.assertEqual(mod.cut(self.root, 'minor'), '0.3.0')
        self.assertEqual(sorted(p.name for p in (self.root / 'changes').iterdir()), ['README.md'])
        section = mod.read_metadata(self.root)[1]['0.3.0'][1]
        self.assertEqual(section, '- Sem categoria.\n\n### Adicionado\n\n- Novo.\n\n### Corrigido\n\n- Nove.\n- Dez.\n  Continua.')
        self.commit()
        self.assertEqual(mod.check(self.root, task, 'HEAD'), '0.3.0')

    def test_release_must_consume_every_note(self):
        self.add_note('3-task.md')
        self.commit()
        task = self.git('rev-parse', 'HEAD').strip()
        self.add_note('4-late.md')
        mod.cut(self.root, 'patch')
        self.add_note('4-late.md')
        self.commit()
        with self.assertRaises(ValueError):
            mod.check(self.root, task, 'HEAD')

    def test_readme_only_needs_no_release(self):
        (self.root / 'README.md').write_text('clarification')
        self.commit()
        self.assertEqual(mod.check(self.root, self.base, 'HEAD'), '0.2.0')

    def test_contracts_and_design_require_note(self):
        for name in ['AGENTS.md', 'RUNBOOK.md', 'design/tokens.json']:
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('changed contract')
            self.commit()
            with self.subTest(name=name), self.assertRaises(ValueError):
                mod.check(self.root, self.base, 'HEAD')

    def test_empty_cut_does_not_modify_metadata(self):
        with self.assertRaises(ValueError):
            mod.cut(self.root, 'patch')
        self.assertEqual((self.root / 'VERSION').read_text(), '0.2.0\n')

    def test_historical_notes_are_immutable(self):
        self.add_note()
        mod.cut(self.root, 'minor')
        p = self.root / 'CHANGELOG.md'
        p.write_text(p.read_text().replace('Baseline.', 'Rewritten.'))
        self.commit()
        with self.assertRaises(ValueError):
            mod.check(self.root, self.base, 'HEAD')

    def test_mirror_mismatch_fails(self):
        for package, pyproject in [('9.0.0', None), (None, '9.0.0')]:
            self.write_version('0.2.0', package, pyproject)
            self.commit()
            with self.subTest(package=package, pyproject=pyproject), self.assertRaises(ValueError):
                mod.check(self.root, None, 'HEAD')

    def test_downgrade_or_skipped_increment_is_rejected(self):
        self.add_note()
        mod.cut(self.root, 'minor')
        for version in ['0.1.9', '0.9.0']:
            self.write_version(version)
            p = self.root / 'CHANGELOG.md'
            p.write_text(re.sub(r'## \[0\.[0-9]+\.[0-9]+\] -', '## [' + version + '] -', p.read_text(), count=1))
            self.commit()
            with self.subTest(version=version), self.assertRaises(ValueError):
                mod.check(self.root, self.base, 'HEAD')

    def test_invalid_and_duplicate_versions_rejected(self):
        for version in ['01.0.0', '1.0', 'v1.0.0', '1.0.0;bad']:
            with self.assertRaises(ValueError):
                mod.parse_version(version)
        p = self.root / 'CHANGELOG.md'
        p.write_text(p.read_text() + '\n## [0.2.0] - 2026-10-07\n\n- Duplicate.\n')
        self.commit()
        with self.assertRaises(ValueError):
            mod.check(self.root, None, 'HEAD')

    def test_first_versioned_commit_must_be_initial_baseline(self):
        repo = Path(self.tmp.name) / 'fresh'
        repo.mkdir()
        run = lambda *a: subprocess.check_output(['git', *a], cwd=repo, text=True, stderr=subprocess.DEVNULL)
        run('init', '-q')
        run('config', 'user.email', 'fixture@example.invalid')
        run('config', 'user.name', 'Fixture')
        (repo / 'README.md').write_text('before versioning')
        run('add', '.')
        run('commit', '-qm', 'old')
        old = run('rev-parse', 'HEAD').strip()
        (repo / 'frontend').mkdir()
        for version, ok in [('0.2.0', True), ('0.3.0', False)]:
            (repo / 'VERSION').write_text(version + '\n')
            (repo / 'frontend/package.json').write_text(json.dumps({'version': version}))
            (repo / 'pyproject.toml').write_text(PYPROJECT.format(v=version))
            (repo / 'CHANGELOG.md').write_text(f'# Changelog\n\n## [Unreleased]\n\n## [{version}] - 2026-10-07\n\n- Baseline.\n')
            run('add', '.')
            run('commit', '-qm', 'versioned')
            with self.subTest(version=version):
                if ok:
                    self.assertEqual(mod.check(repo, old, 'HEAD'), version)
                else:
                    with self.assertRaises(ValueError):
                        mod.check(repo, old, 'HEAD')


if __name__ == '__main__':
    unittest.main()
