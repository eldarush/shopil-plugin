"""Select the pinned runtime even when the host's `python` points to an older one."""
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys

PLUGIN = Path(__file__).resolve().parents[1]
REQUIRED = runpy.run_path(str(PLUGIN / 'skills/jira-workflow/scripts/guard.py'))['PYTHON_VERSION']


def select_runtime():
    if sys.version_info[:3] == REQUIRED:
        return sys.executable
    candidates = [['py', '-3.14']] if os.name == 'nt' else []
    candidates += [['python3.14'], ['python3']]
    probe = 'import json,sys;print(json.dumps({"version":list(sys.version_info[:3]),"executable":sys.executable}))'
    for command in candidates:
        try:
            result = subprocess.run(command + ['-I', '-c', probe], capture_output=True, text=True, timeout=2)
            if result.returncode:
                continue
            info = json.loads(result.stdout)
            if not isinstance(info, dict):
                continue
            if tuple(info.get('version', [])) == REQUIRED and Path(info.get('executable', '')).is_file():
                return info['executable']
        except (OSError, subprocess.TimeoutExpired, ValueError, TypeError):
            continue
    raise RuntimeError('Python 3.14.10 is required. Install it, then use py -3.14 on Windows or expose python3.14 on PATH. No hook action was allowed.')


def main():
    try:
        executable = select_runtime()
    except RuntimeError as exc:
        print(f'ShopIL hook blocked: {exc}', file=sys.stderr)
        return 2
    script = PLUGIN / 'hooks/agent_hook.py'
    if sys.version_info[:3] == REQUIRED:
        runpy.run_path(str(script), run_name='__main__')
        return 0
    # Inherit stdin/stdout/stderr so hook events and exit-2 denials survive relaunch.
    try:
        return subprocess.call([executable, str(script)])
    except OSError as exc:
        print(f'ShopIL hook blocked: Python 3.14.10 could not start: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
