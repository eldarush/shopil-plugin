import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'plugins/jira-workflow-guard/skills/jira-workflow/scripts/guard.py'
spec = importlib.util.spec_from_file_location('guard', SCRIPT)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
CONFIG = {'project_keys': ['SHOPIL'], 'main_branch': 'main'}


class PolicyTests(unittest.TestCase):
    def test_branches(self):
        self.assertEqual('SHOPIL-7', guard.branch_ticket('feature/SHOPIL-7-review-loader', CONFIG))
        for name in ['main', '', 'feature/OTHER-7-loader', 'feature/SHOPIL-0-loader', 'feature/SHOPIL-7', 'Feature/SHOPIL-7-loader', 'feature/SHOPIL-7-a/../../main']:
            with self.subTest(name=name), self.assertRaises(guard.Violation):
                guard.branch_ticket(name, CONFIG)

    def test_conventional_commits_and_exact_ticket(self):
        for message in ['feat(etl): add reviews [SHOPIL-7]', 'fix!: change contract\n\nRefs: SHOPIL-7', 'docs: update guide\n\nBREAKING CHANGE: new usage\nRefs: SHOPIL-7']:
            guard.conventional(message, 'SHOPIL-7')
        for message in ['', 'updates SHOPIL-7', 'feat: ', 'feat: loader [SHOPIL-70]', 'feat: loader [OTHER-7]', 'fix: loader\nRefs: SHOPIL-7', 'feat: loader [SHOPIL-7-extra]', 'feat: loader [SHOPIL-7x]', 'feat: loader [xSHOPIL-7]']:
            with self.subTest(message=message), self.assertRaises(guard.Violation):
                guard.conventional(message, 'SHOPIL-7')

    def test_secret_and_database_paths(self):
        for path in ['.env', 'chat/.env.local', 'etl/shop.duckdb', 'state.sqlite-wal', 'state.db-shm', 'keys/id_rsa', 'keys/client.pem', '.venv/x', 'a/credentials.json']:
            self.assertTrue(guard.forbidden(path), path)
        for path in ['.env.example', 'chat/.env.local.example', 'dbt/models/example.sql', 'docs/database.md', 'fixtures/orders.csv']:
            self.assertFalse(guard.forbidden(path), path)

    def test_push_cannot_target_main_from_another_branch(self):
        sha = 'a' * 40
        guard.pre_push(f'refs/heads/feature/SHOPIL-7-x {sha} refs/heads/feature/SHOPIL-7-x {sha}', CONFIG)
        for ref in ['refs/heads/main', 'refs/heads/feature/SHOPIL-8-x']:
            with self.assertRaises(guard.Violation):
                guard.pre_push(f'refs/heads/feature/SHOPIL-7-x {sha} {ref} {sha}', CONFIG)
        with self.assertRaises(guard.Violation):
            guard.pre_push(f'(delete) {"0" * 40} refs/heads/main {sha}', CONFIG)

    def test_invalid_config_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.json'
            for config in [{}, {'project_keys': [], 'main_branch': 'main'}, {'project_keys': ['.*'], 'main_branch': 'main'}, {**CONFIG, 'ignore_errors': True}]:
                path.write_text(json.dumps(config), encoding='utf-8')
                with self.assertRaises(guard.Violation):
                    guard.load_config(path)


class OwnershipTests(unittest.TestCase):
    def setUp(self):
        self.identity = {'accountId': 'account-a', 'displayName': 'Same Name'}
        self.issue = {'key': 'SHOPIL-7', 'fields': {'summary': 'Load reviews', 'assignee': {'accountId': 'account-a', 'displayName': 'Same Name'}, 'status': {'statusCategory': {'key': 'indeterminate'}}}}

    def test_own_task_allowed_for_each_installer(self):
        for account in ['account-a', 'account-b']:
            self.identity['accountId'] = account
            self.issue['fields']['assignee']['accountId'] = account
            guard.check_jira(self.issue, self.identity, 'SHOPIL-7', CONFIG)

    def test_same_name_different_id_is_not_owner(self):
        self.issue['fields']['assignee']['accountId'] = 'account-b'
        with self.assertRaisesRegex(guard.Violation, 'another account'):
            guard.check_jira(self.issue, self.identity, 'SHOPIL-7', CONFIG)

    def test_unassigned_or_missing_owner_is_read_only(self):
        for assignee in [None, {}, {'displayName': 'Same Name'}]:
            self.issue['fields']['assignee'] = assignee
            with self.assertRaises(guard.Violation):
                guard.check_jira(self.issue, self.identity, 'SHOPIL-7', CONFIG)

    def test_missing_identity_does_not_match_missing_assignee(self):
        self.issue['fields']['assignee'] = None
        for identity in [{}, {'accountId': None}, {'accountId': ''}, {'accountId': '   '}, {'displayName': 'Same Name'}]:
            with self.assertRaises(guard.Violation):
                guard.check_jira(self.issue, identity, 'SHOPIL-7', CONFIG)

    def test_reassignment_before_completion_is_blocked(self):
        guard.check_jira(self.issue, self.identity, 'SHOPIL-7', CONFIG)
        changed = copy.deepcopy(self.issue)
        changed['fields']['assignee']['accountId'] = 'account-b'
        with self.assertRaises(guard.Violation):
            guard.check_jira(changed, self.identity, 'SHOPIL-7', CONFIG, 'finish')

    def test_wrong_ticket_and_done_task_fail(self):
        with self.assertRaises(guard.Violation):
            guard.check_jira(self.issue, self.identity, 'SHOPIL-8', CONFIG)
        self.issue['fields']['status']['statusCategory']['key'] = 'done'
        with self.assertRaises(guard.Violation):
            guard.check_jira(self.issue, self.identity, 'SHOPIL-7', CONFIG)

    def test_todo_allowed_only_before_start(self):
        self.issue['fields']['status']['statusCategory']['key'] = 'new'
        guard.check_jira(self.issue, self.identity, 'SHOPIL-7', CONFIG, 'start')
        with self.assertRaises(guard.Violation):
            guard.check_jira(self.issue, self.identity, 'SHOPIL-7', CONFIG)


class GitIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='guard repo ')
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.env = {**os.environ, 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull}
        self.run_git('init', '-b', 'main')
        self.run_git('config', 'user.name', 'Test User')
        self.run_git('config', 'user.email', 'test@example.invalid')
        self.run_git('config', 'commit.gpgsign', 'false')
        (self.repo / '.workflow-guard.json').write_text(json.dumps(CONFIG), encoding='utf-8')
        self.run_git('add', '.')
        self.run_git('commit', '-m', 'chore: bootstrap [SHOPIL-7]')
        self.base = self.run_git('rev-parse', 'HEAD').stdout.strip()
        self.run_git('switch', '-c', 'feature/SHOPIL-7-loader')

    def run_git(self, *args, success=True):
        result = subprocess.run(['git', *args], cwd=self.repo, env=self.env, capture_output=True, text=True, encoding='utf-8')
        if success:
            self.assertEqual(0, result.returncode, result.stderr)
        return result

    def command(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=self.repo, env=self.env, capture_output=True, text=True)

    def commit_file(self, name='loader.py', message='feat: add loader [SHOPIL-7]'):
        (self.repo / name).write_text('example\n', encoding='utf-8')
        self.run_git('add', name)
        self.run_git('commit', '-m', message)

    def event(self):
        return {'pull_request': {'base': {'ref': 'main', 'sha': self.base}, 'head': {'ref': 'feature/SHOPIL-7-loader', 'sha': self.run_git('rev-parse', 'HEAD').stdout.strip()}, 'title': 'feat: load reviews [SHOPIL-7]', 'body': '## Summary\nRead reviews. https://example.atlassian.net/browse/SHOPIL-7\n\n## Validation\nRan the loader tests.'}}

    def test_real_hooks_block_bad_commit_and_allow_valid_commit(self):
        result = self.command('install-hooks')
        self.assertEqual(0, result.returncode, result.stderr)
        (self.repo / 'file.txt').write_text('content', encoding='utf-8')
        self.run_git('add', '.')
        bad = self.run_git('commit', '-m', 'bad message', success=False)
        self.assertNotEqual(0, bad.returncode)
        self.run_git('commit', '-m', 'feat: add file [SHOPIL-7]')

    def test_real_hook_blocks_secret_and_main_commit(self):
        self.assertEqual(0, self.command('install-hooks').returncode)
        (self.repo / '.env').write_text('FAKE_TOKEN=not-a-secret', encoding='utf-8')
        self.run_git('add', '.env')
        self.assertNotEqual(0, self.run_git('commit', '-m', 'feat: configure [SHOPIL-7]', success=False).returncode)
        self.run_git('rm', '--cached', '.env')
        self.run_git('switch', 'main')
        (self.repo / 'file.txt').write_text('x', encoding='utf-8')
        self.run_git('add', 'file.txt')
        self.assertNotEqual(0, self.run_git('commit', '-m', 'feat: configure [SHOPIL-7]', success=False).returncode)

    def test_existing_hooks_and_hook_manager_are_preserved(self):
        path = self.repo / '.git/hooks/pre-commit'
        path.write_text('# existing hook\n', encoding='utf-8')
        result = self.command('install-hooks')
        self.assertNotEqual(0, result.returncode)
        self.assertEqual('# existing hook\n', path.read_text(encoding='utf-8'))
        self.assertFalse((self.repo / '.git/hooks/commit-msg').exists())
        path.unlink()
        self.run_git('config', 'core.hooksPath', '.custom-hooks')
        self.assertNotEqual(0, self.command('install-hooks').returncode)

    def test_valid_pr_and_invalid_title(self):
        self.commit_file()
        event = self.event()
        self.assertEqual('SHOPIL-7', guard.check_pr(self.repo, event, CONFIG))
        event['pull_request']['title'] = 'feat: incorrect ticket [SHOPIL-70]'
        with self.assertRaises(guard.Violation):
            guard.check_pr(self.repo, event, CONFIG)

    def test_ci_rejects_bad_commit_even_when_title_is_valid(self):
        self.commit_file(message='bad commit')
        with self.assertRaises(guard.Violation):
            guard.check_pr(self.repo, self.event(), CONFIG)

    def test_ci_rejects_database_in_tree(self):
        self.commit_file(name='state.sqlite')
        with self.assertRaisesRegex(guard.Violation, 'Blocked'):
            guard.check_pr(self.repo, self.event(), CONFIG)

    def test_pr_metadata_cannot_inject_shell(self):
        self.commit_file()
        event = self.event()
        event['pull_request']['head']['ref'] = 'feature/SHOPIL-7-$(touch pwned)'
        with self.assertRaises(guard.Violation):
            guard.check_pr(self.repo, event, CONFIG)
        self.assertFalse((self.repo / 'pwned').exists())

    def test_cli_missing_config_is_nonzero(self):
        result = self.command('branch', '--config', 'missing.json')
        self.assertNotEqual(0, result.returncode)


if __name__ == '__main__':
    unittest.main()
