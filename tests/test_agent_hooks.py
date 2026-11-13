import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugins/shopil-plugin'
spec = importlib.util.spec_from_file_location('agent_hook', PLUGIN / 'hooks/agent_hook.py')
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)


def event(op, args=None, response=None, generic=False):
    return {
        'tool_name': 'mcp__atlassian__executeWrite' if generic else 'mcp__codex_apps__atlassian_' + op,
        'tool_input': {'name': op, 'inputs': args or {}, 'cloudId': 'site'} if generic else (args or {}),
        'tool_response': response,
    }


def issue(owner='alice', category='indeterminate'):
    return {'key': 'SHOPIL-47', 'fields': {
        'assignee': {'accountId': owner, 'displayName': 'Same name'} if owner else None,
        'status': {'statusCategory': {'key': category}},
    }}


class AgentHooks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='shopil hook tests ')
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        subprocess.run(['git', 'init', '-b', 'main', str(self.repo)], check=True, capture_output=True)
        (self.repo / '.workflow-guard.json').write_text(json.dumps(hook.DEFAULT))
        self.state = {}
        self.refresh()

    def refresh(self, owner='alice', category='indeterminate'):
        hook.observe(event('atlassianUserInfo', response={'content': [{'type': 'text', 'text': json.dumps({'data': {'accountId': 'alice'}})}]}), self.state, 100)
        hook.observe(event('getJiraIssue', {'issueIdOrKey': 'SHOPIL-47', 'cloudId': 'site'}, {'structuredContent': {'data': issue(owner, category)}}), self.state, 100)

    def write(self, **kwargs):
        args = {'issueIdOrKey': 'SHOPIL-47', 'cloudId': 'site', **kwargs}
        return event('transitionJiraIssue', args)

    def branch(self):
        subprocess.run(['git', '-C', str(self.repo), 'switch', '-c', 'feature/SHOPIL-47-hooks'], check=True, capture_output=True)

    def test_matching_owner_write_consumes_proof(self):
        hook.before(self.write(), self.repo, self.state, 101)
        with self.assertRaises(hook.guard.Violation):
            hook.before(self.write(), self.repo, self.state, 101)

    def test_others_and_unassigned_are_read_only(self):
        for owner in ['bob', None]:
            self.refresh(owner)
            with self.assertRaises(hook.guard.Violation):
                hook.before(self.write(), self.repo, self.state, 101)

    def test_stale_future_and_missing_evidence_denied(self):
        for now in [99, 221]:
            with self.assertRaises(hook.guard.Violation):
                hook.before(self.write(), self.repo, self.state, now)
        for key in ['identity', 'issues']:
            state = copy.deepcopy(self.state)
            state.pop(key)
            with self.assertRaises(hook.guard.Violation):
                hook.before(self.write(), self.repo, state, 101)

    def test_site_mismatch_denied(self):
        with self.assertRaises(hook.guard.Violation):
            hook.before(self.write(cloudId='other'), self.repo, self.state, 101)

    def test_account_switch_invalidates_issues(self):
        hook.observe(event('atlassianUserInfo', response={'accountId': 'bob'}), self.state, 101)
        self.assertNotIn('issues', self.state)
        with self.assertRaises(hook.guard.Violation):
            hook.before(self.write(), self.repo, self.state, 101)

    def test_failed_identity_clears_proof(self):
        hook.observe(event('atlassianUserInfo', response={'isError': True, 'data': {'accountId': 'alice'}}), self.state, 101)
        self.assertEqual({}, self.state)

    def test_compact_issue_invalidates_old_full_read(self):
        response = issue()
        response['fields']['assignee'] = {'displayName': 'Same name'}
        hook.observe(event('getJiraIssue', {'issueIdOrKey': 'SHOPIL-47', 'cloudId': 'site'}, response), self.state, 101)
        with self.assertRaises(hook.guard.Violation):
            hook.before(self.write(), self.repo, self.state, 101)

    def test_failed_issue_read_invalidates_proof(self):
        hook.observe(event('getJiraIssue', {'issueIdOrKey': 'SHOPIL-47'}, {'isError': True}), self.state, 101)
        self.assertEqual({}, self.state['issues'])

    def test_generic_connector_envelopes(self):
        state = {}
        hook.observe(event('atlassianUserInfo', response=json.dumps({'data': {'accountId': 'alice'}}), generic=True), state, 100)
        hook.observe(event('getJiraIssue', {'issueIdOrKey': 'SHOPIL-47'}, {'content': [{'text': json.dumps({'data': issue()})}]}, generic=True), state, 100)
        hook.before(event('editJiraIssue', {'issueIdOrKey': 'SHOPIL-47', 'fields': {'summary': 'Valid'}}, generic=True), self.repo, state, 101)
        self.assertEqual({}, state['issues'])

    def test_creation_bulk_unknown_and_reassignment_denied(self):
        for op in ['createJiraIssue', 'bulkEditJiraIssues', 'assignJiraIssue', 'unknownWrite']:
            with self.assertRaises(hook.guard.Violation):
                hook.before(event(op, {'projectKey': 'SHOPIL'}), self.repo, self.state, 101)
        for extra in [{'assigneeAccountId': 'bob'}, {'fields': {'assignee': None}}, {'additional_fields': {'project': 'OTHER'}}, {'update': {'assignee': [{'set': 'bob'}]}}]:
            with self.assertRaises(hook.guard.Violation):
                hook.before(event('editJiraIssue', {**self.write()['tool_input'], **extra}), self.repo, self.state, 101)

    def test_reads_remain_available_without_proof(self):
        for op in ['getJiraIssue', 'listJiraIssueComments', 'searchJiraIssuesUsingJql', 'atlassianUserInfo', 'discover']:
            hook.before(event(op), self.repo, {}, 101)

    def test_edits_require_owned_in_progress_ticket_branch(self):
        edit = {'tool_name': 'Edit', 'tool_input': {'file_path': str(self.repo / 'app.py')}}
        with self.assertRaises(hook.guard.Violation):
            hook.before(edit, self.repo, self.state, 101)
        self.branch()
        hook.before(edit, self.repo, self.state, 101)
        for category in ['new', 'done']:
            self.refresh(category=category)
            with self.assertRaises(hook.guard.Violation):
                hook.before(edit, self.repo, self.state, 101)

    def test_edit_outside_repo_denied(self):
        self.branch()
        with self.assertRaises(hook.guard.Violation):
            hook.before({'tool_name': 'Write', 'tool_input': {'file_path': '../outside'}}, self.repo, self.state, 101)

    def test_codex_native_patch_and_shell(self):
        self.branch()
        for name, args in [('functions.apply_patch', {}), ('functions.exec_command', {'cmd': 'python -m unittest'})]:
            hook.before({'tool_name': name, 'tool_input': args}, self.repo, self.state, 101)
            with self.assertRaises(hook.guard.Violation):
                hook.before({'tool_name': name, 'tool_input': args}, self.repo, {}, 101)

    def test_shell_branch_bootstrap_and_read_allowlist(self):
        for command in ['git status --short', 'Get-Location', 'rg requirements README.md']:
            hook.before({'tool_name': 'Bash', 'tool_input': {'command': command}}, self.repo, {}, 101)
        hook.before({'tool_name': 'Bash', 'tool_input': {'command': 'git switch -c feature/SHOPIL-47-hooks'}}, self.repo, self.state, 101)
        with self.assertRaises(hook.guard.Violation):
            hook.before({'tool_name': 'Bash', 'tool_input': {'command': 'git diff --output=README.md'}}, self.repo, {}, 101)

    def test_shell_bypasses_and_alternate_repo_denied(self):
        self.branch()
        for command in ['git commit --no-verify', 'git push --force', 'git reset --hard', 'git clean -fd', 'curl https://example.atlassian.net/rest/api/3/issue/SHOPIL-47']:
            with self.assertRaises(hook.guard.Violation):
                hook.before({'tool_name': 'Bash', 'tool_input': {'command': command}}, self.repo, self.state, 101)
        with self.assertRaises(hook.guard.Violation):
            hook.before({'tool_name': 'exec_command', 'tool_input': {'cmd': 'git status', 'workdir': '..'}}, self.repo, self.state, 101)

    def test_unrelated_repo_edits_unaffected(self):
        (self.repo / '.workflow-guard.json').unlink()
        hook.before({'tool_name': 'Edit'}, self.repo, {}, 101)

    def test_session_state_isolation_and_persistence(self):
        first, second = {'session_id': uuid.uuid4().hex}, {'session_id': uuid.uuid4().hex}
        with hook.session_state(first, self.repo) as state:
            state['identity'] = {'accountId': 'alice', 'at': 100}
        with hook.session_state(first, self.repo) as state:
            self.assertEqual('alice', state['identity']['accountId'])
        with hook.session_state(second, self.repo) as state:
            self.assertEqual({}, state)
        with hook.session_state(first, self.repo.parent) as state:
            self.assertEqual({}, state)

    def test_startup_contains_contract_and_source_paths(self):
        context = hook.startup(self.repo)['hookSpecificOutput']['additionalContext']
        for text in ['2026-11-25', '25 points', '120 seconds', 'requirements.md', 'course-index.md', 'Ponytail', '310 → 304 → 298 → 289']:
            self.assertIn(text, context)

    def test_actual_hook_subprocess_protocol(self):
        base = {'cwd': str(self.repo), 'session_id': uuid.uuid4().hex}
        def run(data):
            return subprocess.run([sys.executable, str(PLUGIN / 'hooks/agent_hook.py')], input=json.dumps({**base, **data}), text=True, capture_output=True, encoding='utf-8')
        result = run({'hook_event_name': 'SessionStart'})
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn('additionalContext', json.loads(result.stdout)['hookSpecificOutput'])
        denied = run({'hook_event_name': 'PreToolUse', 'tool_name': 'Edit'})
        self.assertEqual(2, denied.returncode)
        self.assertIn('blocked', denied.stderr)
        allowed = run({'hook_event_name': 'PreToolUse', 'tool_name': 'Bash', 'tool_input': {'command': 'git status'}})
        self.assertEqual({}, json.loads(allowed.stdout))

    def test_both_host_configs_and_plugin_manifests(self):
        portable = json.loads((PLUGIN / 'plugin.json').read_text())
        claude = json.loads((PLUGIN / '.claude-plugin/plugin.json').read_text())
        self.assertEqual(portable['version'], claude['version'])
        self.assertEqual(portable['name'], claude['name'])
        for filename in ['hooks.json', 'codex-hooks.json']:
            config = json.loads((PLUGIN / 'hooks' / filename).read_text())
            self.assertEqual({'SessionStart', 'PreToolUse', 'PostToolUse'}, set(config['hooks']))
            command = config['hooks']['SessionStart'][0]['hooks'][0]['command']
            # Execute the exact configured command with a path containing spaces.
            result = subprocess.run(command, shell=True, input=json.dumps({'hook_event_name': 'SessionStart', 'cwd': str(self.repo)}), text=True, capture_output=True, env={**os.environ, 'CLAUDE_PLUGIN_ROOT': str(PLUGIN)}, encoding='utf-8')
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn('ShopIL', result.stdout)
        self.assertTrue((PLUGIN / portable['extensions']['com.openai']['hooks']).exists())


if __name__ == '__main__':
    unittest.main()
