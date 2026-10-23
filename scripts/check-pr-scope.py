#!/usr/bin/env python3
"""Cheap task metadata/diff boundary for PRs to main. Does not fetch PR content with a token.

A task PR adds one note changes/<N>-<slug>.md for its own issue and never edits
CHANGELOG.md, so parallel PRs do not conflict. Only the release cut (VERSION changes,
`release_version.py cut`) edits CHANGELOG.md and deletes the notes. Note contents are
validated by `release_version.py check`.
"""
import json
import os
from pathlib import Path
import re
import subprocess

NOTE = re.compile(r'changes/(\d+)-[a-z0-9]+(?:-[a-z0-9]+)*\.md')
NOTES_README = 'changes/README.md'
SECURITY_REVIEW = re.compile(r'^Security-Review:[ \t]*\S', re.M)
# Paths that run code in CI or steer agents: the PR runs its own CI and gates (accepted risk).
REVIEWED_DIRS = ('.github/', 'scripts/', 'bin/', '.claude/', '.codex/')
REVIEWED_FILES = ('frontend/package.json', 'AGENTS.md', 'CLAUDE.md', 'RELEASES.md')
# What a release cut may change, besides deleting notes.
RELEASE_FILES = ('VERSION', 'frontend/package.json', 'pyproject.toml', 'CHANGELOG.md')
# Every form GitHub accepts: 'Closes #6', 'Closes: #6', 'Fixes owner/repo#6', 'Resolves <issue URL>'.
CLOSING = re.compile(r'(?i)\b(close[sd]?|fix(e[sd])?|resolve[sd]?)\b:?\s+(#\d+|[\w.-]+/[\w.-]+#\d+|https?://\S+/issues/\d+)')


def merge_base(base, head):
    """The PR's own changes start where the branch left main, not at the main tip."""
    return subprocess.check_output(['git', 'merge-base', base, head], text=True, timeout=30).strip()


def diff_status(base, head):
    out = subprocess.check_output(['git', 'diff', '--no-renames', '--name-status', '-z', base, head], text=True, timeout=30)
    fields = out.split('\0')[:-1]
    return list(zip(fields[0::2], fields[1::2]))


def pending_notes(sha):
    out = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', '-z', sha, 'changes/'], text=True, timeout=30)
    return [path for path in out.split('\0') if path and path != NOTES_README]


def blob(sha, path):
    result = subprocess.run(['git', 'show', f'{sha}:{path}'], capture_output=True, text=True, timeout=30)
    return result.stdout if result.returncode == 0 else None


def version(sha):
    return (blob(sha, 'VERSION') or '').strip()


def semver(value):
    match = re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', value)
    return tuple(map(int, match.groups())) if match else (-1,)


def check(event):
    pr = event['pull_request']
    body = pr.get('body') or ''
    branch = pr['head']['ref']
    match = re.fullmatch(r'(feature|fix|chore|docs|test|refactor)/(\d+)-[a-z0-9-]+', branch)
    if not match or not re.search(rf'\bRefs #{match[2]}\b', body):
        raise ValueError('Task branch must identify an issue (<type>/<N>-<slug>) and PR body must contain Refs #N')
    if CLOSING.search(body):
        raise ValueError('Use Refs #N, never a closing keyword: the issue closes after acceptance')
    issue = match[2]
    base, head = pr['base']['sha'], pr['head']['sha']
    if not all(re.fullmatch(r'[0-9a-f]{40}', sha) for sha in (base, head)):
        raise ValueError('Invalid commit SHA')
    tip, base = base, merge_base(base, head)
    subprocess.run(['git', 'diff', '--check', base, head], check=True, timeout=30)
    changes = diff_status(base, head)
    paths = [path for _, path in changes]
    if not paths:
        raise ValueError('Empty task')
    if any(Path(p).name.startswith('.env') and Path(p).name != '.env.example' for p in paths):
        raise ValueError('Environment files are outside PR scope')
    # A bare directory name is a symlink or submodule standing in for that directory.
    if any(p.startswith(REVIEWED_DIRS) or p in REVIEWED_FILES or f'{p}/' in REVIEWED_DIRS for p in paths) \
            and not SECURITY_REVIEW.search(body):
        raise ValueError(f'PR touching {", ".join(REVIEWED_DIRS + REVIEWED_FILES)} needs a "Security-Review: <summary>" line')
    notes = [(status, path) for status, path in changes if path.startswith('changes/') and path != NOTES_README]
    if version(base) != version(head):
        # Release cut: joins the notes into CHANGELOG.md and deletes them.
        if semver(version(head)) <= semver(version(base)):
            raise ValueError(f'Release PR must raise VERSION: {version(base)} -> {version(head)}')
        if tip != base:
            raise ValueError('Release PR must be up to date with main: update the branch right before merging')
        if extra := [p for status, p in changes if p not in RELEASE_FILES and (status, p) not in notes]:
            raise ValueError(f'Release PR only cuts the version; move these to a task PR: {", ".join(extra)}')
        if any(status != 'D' for status, _ in notes):
            raise ValueError('Release PR only deletes notes from changes/')
        if left := pending_notes(head):
            raise ValueError(f'Release PR must consume every note; left: {", ".join(left)}')
        return
    if 'CHANGELOG.md' in paths:
        raise ValueError(f'Task PRs do not edit CHANGELOG.md; add changes/{issue}-<slug>.md instead')
    own = [path for status, path in notes if status in ('A', 'M') and (m := NOTE.fullmatch(path)) and m[1] == issue]
    if len(own) != 1:
        raise ValueError(f'Task requires exactly one note changes/{issue}-<slug>.md')
    if foreign := [path for _, path in notes if path not in own]:
        raise ValueError(f'Task PR may only touch its own note, not: {", ".join(foreign)}')


if __name__ == '__main__':
    try:
        check(json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text()))
    except (ValueError, subprocess.SubprocessError) as error:
        raise SystemExit(f'FAIL  PR scope: {error}')
    print('PASS  PR scope')
