#!/usr/bin/env python3
"""Version/changelog contract. Local preparation only; never tags, publishes or deploys."""
import argparse
from datetime import date, datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import tomllib

VERSION = r'(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)'
HEADER = re.compile(r'^## \[(Unreleased|' + VERSION + r')\](?: - (\d{4}-\d{2}-\d{2}))?$', re.M)
FILES = ('VERSION', 'frontend/package.json', 'pyproject.toml', 'CHANGELOG.md')
INITIAL = '0.2.0'
PYPROJECT_VERSION = re.compile(r'^version = "[^"\n]*"$', re.M)
# Task PRs add one note changes/<N>-<slug>.md and never edit CHANGELOG.md; only the
# release cut changes VERSION, joins the notes into CHANGELOG.md and deletes them.
NOTES_DIR = 'changes'
NOTES_README = 'changes/README.md'
NOTE = re.compile(r'changes/(\d+)-[a-z0-9]+(?:-[a-z0-9]+)*\.md')
CATEGORIES = ('Adicionado', 'Alterado', 'Corrigido', 'Removido', 'Segurança')


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root, text=True, stderr=subprocess.DEVNULL)


def resolve(root, ref):
    return git(root, 'rev-parse', '--verify', '--end-of-options', ref + '^{commit}').strip()


def parse_version(value):
    if not re.fullmatch(VERSION, value):
        raise ValueError('version must be MAJOR.MINOR.PATCH without leading zeroes')
    return tuple(map(int, value.split('.')))


def next_version(value, bump):
    major, minor, patch = parse_version(value)
    if bump == 'patch': return f'{major}.{minor}.{patch + 1}'
    if bump == 'minor': return f'{major}.{minor + 1}.0'
    if bump == 'major': return f'{major + 1}.0.0'
    raise ValueError('unknown bump')


def parse_changelog(text):
    headers = list(HEADER.finditer(text))
    if not headers or headers[0][1] != 'Unreleased' or len(headers) != len(re.findall(r'^## ', text, re.M)):
        raise ValueError('changelog headings are invalid')
    sections = {}
    last = None
    for i, match in enumerate(headers):
        version, day = match[1], match[2]
        if version in sections: raise ValueError('duplicate changelog version')
        if version == 'Unreleased':
            if day: raise ValueError('Unreleased must not be dated')
        else:
            if not day or date.fromisoformat(day).isoformat() != day: raise ValueError('invalid release date')
            order = parse_version(version)
            if last is not None and order >= last: raise ValueError('versions must descend')
            last = order
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        body = text[match.end():end].strip()
        if version != 'Unreleased' and not re.search(r'^- \S', body, re.M): raise ValueError('release notes are empty')
        sections[version] = (day, body)
    return sections


def read_metadata(root, revision=None):
    if revision:
        revision = resolve(root, revision)
        values = {p: git(root, 'show', f'{revision}:{p}') for p in FILES}
    else:
        if any((root / p).is_symlink() or (root / p).resolve() != root / p for p in FILES):
            raise ValueError('metadata paths must be canonical')
        values = {p: (root / p).read_text() for p in FILES}
    version = values['VERSION'].strip()
    parse_version(version)
    if json.loads(values['frontend/package.json']).get('version') != version: raise ValueError('package version differs from VERSION')
    if tomllib.loads(values['pyproject.toml']).get('project', {}).get('version') != version: raise ValueError('pyproject version differs from VERSION')
    if len(PYPROJECT_VERSION.findall(values['pyproject.toml'])) != 1: raise ValueError('pyproject must declare one version line')
    notes = parse_changelog(values['CHANGELOG.md'])
    if list(notes)[1:2] != [version]: raise ValueError('latest changelog entry must match VERSION')
    return version, notes, values


def pending_notes(root, revision=None):
    """Note paths waiting for the next release, sorted by issue number."""
    if revision:
        out = git(root, 'ls-tree', '-r', '-z', resolve(root, revision), NOTES_DIR + '/')
        entries = [line.split('\t', 1) for line in out.split('\0') if line]
        if any(meta.split()[0] not in ('100644', '100755') for meta, _ in entries):
            raise ValueError('notes must be regular files')
        paths = [path for _, path in entries]
    else:
        folder = root / NOTES_DIR
        if folder.is_symlink() or (folder.exists() and folder.resolve() != folder): raise ValueError('changes/ must be a regular file tree')
        paths = [f'{NOTES_DIR}/{p.relative_to(folder).as_posix()}' for p in folder.rglob('*') if p.is_symlink() or not p.is_dir()] if folder.is_dir() else []
        if any((root / p).is_symlink() for p in paths): raise ValueError('notes must be regular files')
    paths = [p for p in paths if p != NOTES_README]
    for path in paths:
        if not NOTE.fullmatch(path): raise ValueError('invalid note name: '+path)
    return sorted(paths, key=lambda p: (int(NOTE.fullmatch(p)[1]), p))


def read_note(root, path, revision=None):
    if revision: return git(root, 'show', f'{resolve(root, revision)}:{path}')
    if (root / path).is_symlink(): raise ValueError('note must be a regular file')
    return (root / path).read_text()


def parse_note(text):
    """[(category or None, item block)] in file order. Accepts '- item', indented
    continuation right after an item, blank lines and '### <category>'."""
    entries, category, item = [], None, None
    for line in text.splitlines():
        if line.startswith('- ') and line[2:].strip():
            item = [line.rstrip()]
            entries.append((category, item))
        elif line[:1] in (' ', '\t') and line.strip():
            if item is None: raise ValueError('continuation without item')
            item.append(line.rstrip())
        elif not line.strip():
            item = None
        elif line.startswith('### ') and line[4:].strip() in CATEGORIES:
            category, item = line[4:].strip(), None
        else:
            raise ValueError('invalid note line')
    if not entries: raise ValueError('empty note')
    return [(c, '\n'.join(lines)) for c, lines in entries]


def join_notes(texts):
    """Release body: uncategorized items first, then categories in fixed order."""
    grouped = {}
    for text in texts:
        for category, item in parse_note(text):
            grouped.setdefault(category, []).append(item)
    blocks = ['\n'.join(grouped[None])] if None in grouped else []
    blocks += [f'### {c}\n\n' + '\n'.join(grouped[c]) for c in CATEGORIES if c in grouped]
    return '\n\n'.join(blocks)


def prose_only(path):
    # Deliberately narrow: runtime runbooks and agent/security instructions are contracts.
    return path == 'README.md'


def check(root, base=None, head=None):
    version, notes, values = read_metadata(root, head)
    if notes['Unreleased'][1]: raise ValueError('Unreleased stays empty; notes live in changes/')
    pending = pending_notes(root, head)
    for path in pending: parse_note(read_note(root, path, head))
    if not base: return version
    base = resolve(root, base)
    if head: head = resolve(root, head)
    paths = git(root, 'diff', '--name-only', '--no-renames', base, *([head] if head else [])).splitlines()
    has_base = subprocess.run(['git','cat-file','-e',f'{base}:VERSION'],cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode == 0
    if not has_base:
        if version != INITIAL or list(notes) != ['Unreleased',INITIAL]: raise ValueError('initial baseline must be only '+INITIAL)
        return version
    old, history, old_values = read_metadata(root, base)
    for item in list(history)[1:]:
        if notes.get(item) != history[item]: raise ValueError('historical release notes must not be rewritten')
    changed_notes = [p for p in paths if NOTE.fullmatch(p)]
    if version == old:
        # Task: a note in changes/, CHANGELOG.md untouched, no note consumed.
        if values['CHANGELOG.md'] != old_values['CHANGELOG.md']: raise ValueError('task PRs do not edit CHANGELOG.md')
        if any(p not in pending for p in changed_notes): raise ValueError('only the release cut deletes notes')
        if any(not prose_only(p) for p in paths) and not changed_notes:
            raise ValueError('behavior/tooling/config changes require a note in changes/')
    elif version not in {next_version(old, bump) for bump in ('patch','minor','major')}:
        raise ValueError('version must be one patch/minor/major increment from base')
    elif list(notes)[2:] != list(history)[1:]:
        raise ValueError('one candidate release per PR; preserve existing history')
    elif pending:
        raise ValueError('release cut must consume every note in changes/')
    return version


def cut(root, bump):
    version, notes, values = read_metadata(root)
    if notes['Unreleased'][1]: raise ValueError('Unreleased stays empty; notes live in changes/')
    pending = pending_notes(root)
    if not pending: raise ValueError('no notes in changes/ to release')
    body = join_notes(read_note(root, path) for path in pending)
    new = next_version(version, bump)
    text = values['CHANGELOG.md']
    start = HEADER.search(text).start()
    current = list(HEADER.finditer(text))[1].start()
    day = datetime.now(timezone.utc).date().isoformat()
    updated = text[:start] + f'## [Unreleased]\n\n## [{new}] - {day}\n\n{body}\n\n' + text[current:]
    package = json.loads(values['frontend/package.json']); package['version'] = new
    pyproject = PYPROJECT_VERSION.sub(f'version = "{new}"', values['pyproject.toml'], count=1)
    changes = {'VERSION':new+'\n','frontend/package.json':json.dumps(package,ensure_ascii=False,indent=2)+'\n','pyproject.toml':pyproject,'CHANGELOG.md':updated}
    try:
        for name, data in changes.items(): (root/name).write_text(data)
    except OSError:
        for name, data in values.items(): (root/name).write_text(data)
        raise
    for path in pending: (root/path).unlink()
    return new


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action',required=True)
    validate = commands.add_parser('check');validate.add_argument('--base');validate.add_argument('--head')
    prepare = commands.add_parser('cut');prepare.add_argument('--bump',choices=('patch','minor','major'),required=True)
    commands.add_parser('notes')
    args=parser.parse_args();root=Path(__file__).resolve().parent.parent
    try:
        if args.action=='cut':
            # This project keeps only main; cut prepares files and never commits or publishes.
            print('PREPARED_NOT_PUBLISHED\t'+cut(root,args.bump))
        elif args.action=='notes':
            version,notes,_=read_metadata(root);print(notes[version][1])
        else: print('PASS\tversion\t'+check(root,args.base or None,args.head or None))
    except (ValueError,OSError,subprocess.SubprocessError,KeyError,IndexError):
        parser.exit(1,'FAIL: version/changelog contract; see RELEASES.md\n')

if __name__=='__main__':main()
