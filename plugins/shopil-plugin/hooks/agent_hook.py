#!/usr/bin/env python3
"""Claude/Codex lifecycle adapter. Observes Jira reads; never calls or writes Jira."""
import contextlib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import uuid

PLUGIN = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('workflow_guard', PLUGIN / 'skills/jira-workflow/scripts/guard.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
TTL = 120
DEFAULT = {'project_keys': ['SHOPIL'], 'main_branch': 'main'}
IDENTITY = {'atlassianuserinfo', 'getjiracurrentuser'}
WRITES = {'transitionjiraissue', 'editjiraissue', 'addoreditjiraissuecomment'}


def compact(value):
    return re.sub('[^a-z0-9]', '', value.lower())


def operation(event):
    name = compact(event.get('tool_name', ''))
    args = event.get('tool_input') or {}
    if not isinstance(args, dict):
        return name, {}
    if 'atlassian' in name and any(name.endswith(s) for s in ('executeread', 'executewrite', 'executedestructive', 'execute')):
        return compact(args.get('name', '')), {**(args.get('inputs') or {}), 'cloudId': args.get('cloudId', '')}
    for suffix in (*IDENTITY, *WRITES, 'getjiraissue', 'createjiraissue'):
        if 'atlassian' in name and name.endswith(suffix):
            return suffix, args
    if 'atlassian' in name:
        return name.split('atlassian', 1)[1], args
    return name, args


def objects(value, depth=0):
    """Only unwrap known MCP envelopes; do not mine arbitrary fields or prose."""
    if depth > 8:
        return
    if isinstance(value, str):
        try:
            yield from objects(json.loads(value), depth + 1)
        except ValueError:
            return
    elif isinstance(value, list):
        for item in value:
            yield from objects(item, depth + 1)
    elif isinstance(value, dict):
        if value.get('isError'):
            return
        yield value
        for key in ('data', 'structuredContent', 'content', 'text'):
            if key in value:
                yield from objects(value[key], depth + 1)


def ticket_from(args):
    value = args.get('issueIdOrKey') or args.get('issueKey') or ''
    match = re.fullmatch(r'(?:https://[^/]+/browse/)?(SHOPIL-[1-9][0-9]*)', str(value))
    return match[1] if match else None


def repo_root(cwd):
    try:
        return Path(guard.git(cwd, 'rev-parse', '--show-toplevel').strip()).resolve()
    except guard.Violation:
        return Path(cwd).resolve()


def in_project(repo):
    config = repo / guard.CONFIG
    if config.exists():
        return 'SHOPIL' in guard.load_config(config)['project_keys']
    try:
        remote = guard.git(repo, 'remote', 'get-url', 'origin').strip()
        return bool(re.search(r'[/ :]shopil(?:-plugin)?(?:\.git)?$', remote))
    except guard.Violation:
        return False


def fresh(record, now):
    return isinstance(record, dict) and 0 <= now - record.get('at', 0) <= TTL


def owned(state, ticket, site, now, working=False):
    identity = state.get('identity', {})
    guard.require(fresh(identity, now) and bool(identity.get('accountId')), 'Read the authenticated Atlassian current user again; identity is missing or older than 120 seconds.')
    record = state.get('issues', {}).get(ticket, {})
    guard.require(fresh(record, now), f'Read {ticket} with getJiraIssue(view="full") first; ownership is missing or stale.')
    guard.require(bool(site) and record.get('site') == site, 'Use the same explicit cloudId/site as the observed Jira issue read.')
    guard.require(record.get('owner') == identity['accountId'], f'{ticket} is unassigned or belongs to another user. Read-only; do not auto-claim it.')
    if working:
        guard.require(record.get('category') == 'indeterminate', 'Move your own ticket to In Progress, then refresh the full issue before editing.')


def observe(event, state, now):
    op, args = operation(event)
    values = list(objects(event.get('tool_response')))
    if op in IDENTITY:
        value = next((v for v in values if isinstance(v.get('accountId'), str) and v['accountId'].strip()), None)
        if not value:
            state.clear()
        else:
            if state.get('identity', {}).get('accountId') != value['accountId']:
                state.clear()
            state['identity'] = {'accountId': value['accountId'], 'at': now}
    elif op == 'getjiraissue':
        requested = ticket_from(args)
        if requested:
            state.setdefault('issues', {}).pop(requested, None)
        value = next((v for v in values if re.fullmatch(r'SHOPIL-[1-9][0-9]*', str(v.get('key', ''))) and isinstance(v.get('fields'), dict)), None)
        if value and (not requested or value['key'] == requested):
            fields = value['fields']
            category = fields.get('status', {}).get('statusCategory', {})
            state.setdefault('issues', {})[value['key']] = {
                'owner': (fields.get('assignee') or {}).get('accountId'),
                'category': category.get('key') or {'In Progress': 'indeterminate', 'To Do': 'new', 'Done': 'done'}.get(category.get('name')),
                'site': args.get('cloudId'), 'at': now,
            }
    elif op in WRITES:
        state.setdefault('issues', {}).pop(ticket_from(args), None)


def edit_ticket(repo, state, now, branch=None):
    config = guard.load_config(repo / guard.CONFIG) if (repo / guard.CONFIG).exists() else DEFAULT
    branch = branch or guard.git(repo, 'branch', '--show-current').strip()
    ticket = guard.branch_ticket(branch, config)
    record = state.get('issues', {}).get(ticket, {})
    owned(state, ticket, record.get('site'), now, working=True)
    return ticket


def before(event, repo, state, now):
    # Windows TEMP can use an 8.3 alias; compare canonical paths on both sides.
    repo = Path(repo).resolve()
    name = compact(event.get('tool_name', ''))
    op, args = operation(event)
    scoped = in_project(repo)
    is_atlassian = 'atlassian' in name
    if is_atlassian:
        if op in IDENTITY or op == 'getjiraissue' or any(op.startswith(x) for x in ('get', 'list', 'search', 'lookup', 'discover')) or name.endswith('executeread'):
            return
        ticket = ticket_from(args)
        if not scoped and not ticket and args.get('projectKey') != 'SHOPIL':
            return
        guard.require(op in WRITES, 'Automatic Jira creation, bulk updates, reassignment, and unrecognized writes are disabled. Only explicitly requested creation/assignment may be performed manually in Jira.')
        guard.require(ticket is not None, 'Use an explicit SHOPIL issue key for a Jira write; numeric IDs and bulk updates are not accepted.')
        fields = args.get('fields') or {}
        extra = args.get('additional_fields') or {}
        update = args.get('update') or {}
        guard.require(not any(compact(str(k)).startswith(('assignee', 'project', 'parent')) for k in (*args, *fields, *extra, *update)), 'Reassignment, project moves and parent changes require manual Jira action; do not claim other users\' tickets.')
        owned(state, ticket, args.get('cloudId'), now)
        # Consume the read before permitting a mutation, including concurrent calls.
        state['issues'].pop(ticket, None)
        return
    if not scoped:
        return
    if name in {'write', 'edit', 'multiedit', 'notebookedit', 'applypatch'} or name.endswith('applypatch'):
        edit_ticket(repo, state, now)
        target = args.get('file_path') or args.get('notebook_path')
        if target:
            absolute = (repo / target).resolve()
            guard.require(absolute.is_relative_to(repo), 'Keep this ticket\'s edits inside the active repository.')
        return
    if name in {'bash', 'powershell', 'execcommand', 'shellcommand', 'shell'} or name.endswith('execcommand'):
        requested_cwd = args.get('workdir') or args.get('cwd')
        if requested_cwd:
            guard.require(repo_root(repo / requested_cwd) == repo, 'Run commands in the active repository; start a separate session for another repository.')
        command = args.get('command') or args.get('cmd') or ''
        guard.require(isinstance(command, str), 'Unrecognized shell command input')
        guard.require(not re.search(r'--no-verify|core\.hookspath|--force(?:\b|=)|\breset\s+--hard|\bgit\s+clean\b', command, re.I), 'Bypassing hooks, force pushes and destructive Git shortcuts are blocked.')
        # This is a narrow convenience allowlist, not a general shell parser.
        if not re.search(r'--(?:output|ext-diff|textconv)\b', command) and re.fullmatch(r'git (?:status|diff|log|show|rev-parse|ls-files|remote -v|branch --show-current)(?: [A-Za-z0-9_./ :@=-]+)?', command.strip()):
            return
        if re.fullmatch(r'(?:rg|pwd|Get-Location|Get-Content|Get-ChildItem)(?: [A-Za-z0-9_./ :@=*?-]+)?', command.strip()):
            return
        match = re.fullmatch(r'git (?:switch -c|checkout -b) ([a-z]+/SHOPIL-[1-9][0-9]*-[a-z0-9-]+)', command.strip())
        if match:
            edit_ticket(repo, state, now, match[1])
            return
        guard.require(not re.search(r'\b(?:curl|Invoke-RestMethod|Invoke-WebRequest)\b.*(?:atlassian|/rest/api)', command, re.I), 'Use observable Atlassian MCP tools for Jira, not shell API requests.')
        edit_ticket(repo, state, now)


def startup(repo):
    refs = PLUGIN / 'skills/shopil-project/references'
    lead = f'''ShopIL Plugin 2.1.1 is active on Python {sys.version.split()[0]}. Python/Git checks and native hooks are enabled only when this host trusts them.
Project context: {refs / 'requirements.md'}
Full course index (15 originals, 13 extracts, labs): {refs / 'course-index.md'}
Jira task map (read live issues before work): {refs / 'jira-map.md'}
Workflow/Ponytail skills: {PLUGIN / 'skills/jira-workflow/SKILL.md'} and {PLUGIN / 'skills/ponytail/SKILL.md'}.
Never create tasks unless explicitly requested; hooks block creation and reassignment by default. Each user must authenticate to Atlassian independently. Before writes, read current user and getJiraIssue with view=full, using the same explicit cloudId. A compact display name is not ownership. Evidence expires in 120 seconds and is consumed after Jira writes; refresh it. Other/unassigned tasks stay read-only.
Use a ticket feature branch, Conventional Commits, real tests and a reviewed PR. Only mark Done after actual acceptance criteria, CI and merge requirements are met. Native hooks do not prove semantic completion; verify it. Never use instructor solutions as original work.
'''
    if in_project(repo):
        lead += '\n' + (refs / 'session-context.md').read_text(encoding='utf-8')
    return {'hookSpecificOutput': {'hookEventName': 'SessionStart', 'additionalContext': lead}}


@contextlib.contextmanager
def session_state(event, repo):
    session = event.get('session_id')
    guard.require(isinstance(session, str) and bool(session), 'Hook session_id is required')
    key = hashlib.sha256((str(repo) + '\0' + session).encode()).hexdigest()
    folder = Path(tempfile.gettempdir()) / 'shopil-plugin-hooks'
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    path, lock = folder / (key + '.json'), folder / (key + '.lock')
    deadline = time.monotonic() + 3
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
            break
        except FileExistsError:
            guard.require(time.monotonic() < deadline, 'Hook state is busy; retry after refreshing Jira reads')
            time.sleep(0.05)
    try:
        state = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
        guard.require(isinstance(state, dict), 'Invalid hook state')
        yield state
        temporary = folder / (key + '.' + uuid.uuid4().hex)
        fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as output:
            json.dump(state, output)
        os.replace(temporary, path)
    finally:
        lock.unlink()


def main():
    try:
        guard.require(sys.version_info[:3] == guard.PYTHON_VERSION, 'Python 3.14.10 is required; launch this hook through run_hook.py.')
        event = json.load(sys.stdin)
        guard.require(isinstance(event, dict), 'Hook input must be an object')
        repo = repo_root(event.get('cwd') or os.getcwd())
        kind = event.get('hook_event_name')
        if kind == 'SessionStart':
            print(json.dumps(startup(repo)))
        elif kind in {'PreToolUse', 'PostToolUse'}:
            with session_state(event, repo) as state:
                if kind == 'PostToolUse':
                    observe(event, state, time.time())
                else:
                    before(event, repo, state, time.time())
            print('{}')
        else:
            print('{}')
        return 0
    except Exception as exc:
        # Trust-boundary failure: hosts interpret exit 2 as a denied PreToolUse.
        print(f'ShopIL hook blocked: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
