#!/usr/bin/env python3
"""Publish a reviewed version only after successful CI of that exact main commit."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.request
from release_version import check, git, pending_notes, read_metadata, prose_only


class ApiError(Exception): pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs): return None


def api(method, endpoint, payload=None, missing=False):
    token = os.environ.get('GH_TOKEN')
    if not token: raise ApiError('missing token')
    request=urllib.request.Request('https://api.github.com/'+endpoint,
        data=json.dumps(payload).encode() if payload is not None else None, method=method,
        headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json',
                 'X-GitHub-Api-Version':'2022-11-28','Content-Type':'application/json','User-Agent':'book-reviewer-release'})
    try:
        with urllib.request.build_opener(NoRedirect()).open(request,timeout=20) as response:
            body=response.read(2*1024*1024+1)
            if len(body)>2*1024*1024:raise ApiError('oversized response')
            return json.loads(body)
    except urllib.error.HTTPError as error:
        if missing and error.code==404:return None
        raise ApiError('provider request failed') from None
    except (OSError,ValueError):raise ApiError('provider request failed') from None


def tag_commit(api_call, prefix, tag):
    ref=api_call('GET',prefix+'/git/ref/tags/'+tag,missing=True)
    if ref is None:return None
    obj=ref['object']
    # Annotated tags are supported but never rewritten. Bound indirection.
    for _ in range(4):
        if obj['type']=='commit' and re.fullmatch('[a-f0-9]{40}',obj['sha']):return obj['sha']
        if obj['type']!='tag' or not re.fullmatch('[a-f0-9]{40}',obj['sha']):break
        obj=api_call('GET',prefix+'/git/tags/'+obj['sha'])['object']
    raise ValueError('tag does not identify a commit')


def verify_release(release, tag, sha, notes, prerelease):
    if not isinstance(release,dict) or release.get('tag_name')!=tag or release.get('name')!='Revisor '+tag or release.get('draft') is not False or release.get('prerelease') is not prerelease:
        raise ValueError('existing release differs; never overwrite')
    body=release.get('body','')
    if not body.startswith(notes+'\n\n---\n') or f'Commit: `{sha}`\n' not in body:
        raise ValueError('existing release notes/identity differ')


def publish(root, repo, run_id, api_call=api):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo) or not re.fullmatch(r'[1-9][0-9]*',str(run_id)):raise ValueError('invalid target')
    prefix='repos/'+repo
    workflow=api_call('GET',prefix+'/actions/workflows/ci.yml')
    run=api_call('GET',prefix+'/actions/runs/'+str(run_id))
    sha=run.get('head_sha','')
    if (not re.fullmatch('[a-f0-9]{40}',sha) or run.get('workflow_id')!=workflow['id'] or run.get('event')!='push' or run.get('head_branch')!='main' or run.get('status')!='completed' or run.get('conclusion')!='success' or run.get('head_repository',{}).get('full_name')!=repo):
        raise ValueError('requires successful main push CI from this repository')
    if git(root,'rev-parse','HEAD').strip()!=sha or git(root,'status','--porcelain','--untracked-files=normal').strip():raise ValueError('checkout must be clean and match CI')
    comparison=api_call('GET',prefix+'/compare/'+sha+'...main')
    if comparison.get('status') not in ('ahead','identical') or comparison.get('merge_base_commit',{}).get('sha')!=sha:raise ValueError('commit is not integrated in main')
    jobs=api_call('GET',prefix+'/actions/runs/'+str(run_id)+'/jobs?per_page=100')
    required=[j for j in jobs.get('jobs',[]) if j.get('name')=='Required CI']
    if jobs.get('total_count',101)>100 or len(required)!=1 or required[0].get('conclusion')!='success':raise ValueError('missing successful Required CI')
    version=check(root,None,'HEAD');_,sections,_=read_metadata(root,'HEAD')
    notes=sections[version][1];tag='v'+version;prerelease=version.startswith('0.')
    # Task merges leave notes in changes/ for the next release cut: nothing to publish, and
    # never a tag on a commit that carries unreleased work (even if the release run was missed).
    if pending_notes(root,'HEAD'):return 'NOT_A_RELEASE '+tag
    target=tag_commit(api_call,prefix,tag)
    existing=api_call('GET',prefix+'/releases/tags/'+tag,missing=True)
    if target and target!=sha:
        related = any(subprocess.run(['git','merge-base','--is-ancestor',a,b],cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode == 0 for a,b in ((target,sha),(sha,target)))
        if not related: raise ValueError('tag conflict')
        old,old_sections,_=read_metadata(root,target)
        paths=git(root,'diff','--name-only','--no-renames',target,sha).splitlines()
        if old!=version or old_sections[version]!=sections[version] or any(not prose_only(p) for p in paths):raise ValueError('tag conflict')
        verify_release(existing,tag,target,notes,prerelease)
        return 'ALREADY_PUBLISHED '+tag
    if existing:
        if target!=sha:raise ValueError('release without matching tag')
        verify_release(existing,tag,sha,notes,prerelease)
        return 'ALREADY_PUBLISHED '+tag
    if target is None:
        try:api_call('POST',prefix+'/git/refs',{'ref':'refs/tags/'+tag,'sha':sha})
        except ApiError:
            # Unknown mutation result: reconcile before any retry; never resend here.
            if tag_commit(api_call,prefix,tag)!=sha:raise
    if tag_commit(api_call,prefix,tag)!=sha:raise ValueError('tag conflict')
    body=notes+'\n\n---\n'+f'Commit: `{sha}`\nCI: https://github.com/{repo}/actions/runs/{run_id}\n\n'+ 'Release de código-fonte; não instala nem atualiza cópias locais do aplicativo.\n'
    payload={'tag_name':tag,'target_commitish':sha,'name':'Revisor '+tag,'body':body,'draft':False,'prerelease':prerelease,'make_latest':'false' if prerelease else 'legacy'}
    try:api_call('POST',prefix+'/releases',payload)
    except ApiError:
        if api_call('GET',prefix+'/releases/tags/'+tag,missing=True) is None:raise
    verify_release(api_call('GET',prefix+'/releases/tags/'+tag),tag,sha,notes,prerelease)
    if tag_commit(api_call,prefix,tag)!=sha:raise ValueError('tag changed during publication')
    return 'PUBLISHED '+tag


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repository',required=True);p.add_argument('--ci-run',required=True)
    args=p.parse_args()
    try:print(publish(Path(__file__).resolve().parent.parent,args.repository,args.ci_run))
    except (ApiError,ValueError,OSError,KeyError,TypeError,subprocess.SubprocessError):p.exit(1,'FAIL: release publication stopped; reconcile CI, tag and release before retry.\n')

if __name__=='__main__':main()
