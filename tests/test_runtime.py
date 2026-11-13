import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

PLUGIN = Path(__file__).resolve().parents[1] / 'plugins/shopil-plugin'
spec = importlib.util.spec_from_file_location('run_hook', PLUGIN / 'hooks/run_hook.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)
guard_spec = importlib.util.spec_from_file_location('runtime_guard', PLUGIN / 'skills/jira-workflow/scripts/guard.py')
guard = importlib.util.module_from_spec(guard_spec)
guard_spec.loader.exec_module(guard)


class RuntimeTests(unittest.TestCase):
    def test_pinned_runtime_uses_current_interpreter_without_probing(self):
        with patch.object(runtime.sys, 'version_info', (3, 14, 10)), patch.object(runtime.subprocess, 'run') as probe:
            self.assertEqual(sys.executable, runtime.select_runtime())
            probe.assert_not_called()

    def test_old_default_selects_verified_installed_runtime(self):
        response = subprocess.CompletedProcess([], 0, json.dumps({'version': [3, 14, 10], 'executable': sys.executable}))
        with patch.object(runtime.sys, 'version_info', (3, 14, 6)), patch.object(runtime.subprocess, 'run', return_value=response) as probe:
            self.assertEqual(sys.executable, runtime.select_runtime())
            self.assertIn('-I', probe.call_args.args[0])

    def test_wrong_patch_release_is_rejected(self):
        for version in [[3, 14, 9], [3, 14, 6], [3, 15, 2], [3, 16, 0]]:
            response = subprocess.CompletedProcess([], 0, json.dumps({'version': version, 'executable': sys.executable}))
            with patch.object(runtime.sys, 'version_info', (3, 14, 6)), patch.object(runtime.subprocess, 'run', return_value=response):
                with self.assertRaisesRegex(RuntimeError, '3.14.10'):
                    runtime.select_runtime()

    def test_unavailable_or_malformed_runtime_fails_closed(self):
        for result in [subprocess.CompletedProcess([], 1, ''), subprocess.CompletedProcess([], 0, 'not json'), subprocess.CompletedProcess([], 0, '[]')]:
            with patch.object(runtime.sys, 'version_info', (3, 14, 6)), patch.object(runtime.subprocess, 'run', return_value=result):
                with self.assertRaises(RuntimeError):
                    runtime.select_runtime()
        with patch.object(runtime.sys, 'version_info', (3, 14, 6)), patch.object(runtime.subprocess, 'run', side_effect=FileNotFoundError):
            with self.assertRaises(RuntimeError):
                runtime.select_runtime()

    def test_missing_runtime_returns_hook_denial(self):
        with patch.object(runtime, 'select_runtime', side_effect=RuntimeError('missing')), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(2, runtime.main())

    def test_relaunch_preserves_denial_exit_code(self):
        with patch.object(runtime.sys, 'version_info', (3, 14, 6)), patch.object(runtime, 'select_runtime', return_value=sys.executable), patch.object(runtime.subprocess, 'call', return_value=2) as child:
            self.assertEqual(2, runtime.main())
            self.assertEqual([sys.executable, str(PLUGIN / 'hooks/agent_hook.py')], child.call_args.args[0])
            self.assertEqual({}, child.call_args.kwargs)  # inherited protocol streams

    def test_standalone_checker_rejects_wrong_runtime(self):
        with patch.object(guard.sys, 'version_info', (3, 14, 6)), contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(1, guard.main(['branch']))
            self.assertIn('Python 3.14.10 is required', error.getvalue())

    def test_runtime_disappearing_after_probe_blocks_hook(self):
        with patch.object(runtime.sys, 'version_info', (3, 14, 6)), patch.object(runtime, 'select_runtime', return_value=sys.executable), patch.object(runtime.subprocess, 'call', side_effect=FileNotFoundError), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(2, runtime.main())

    def test_real_launcher_protocol_reports_actual_runtime(self):
        event = {'hook_event_name': 'SessionStart', 'cwd': str(PLUGIN)}
        result = subprocess.run([sys.executable, str(PLUGIN / 'hooks/run_hook.py')], input=json.dumps(event), capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        context = json.loads(result.stdout)['hookSpecificOutput']['additionalContext']
        self.assertIn('Python 3.14.10', context)


if __name__ == '__main__':
    unittest.main()
