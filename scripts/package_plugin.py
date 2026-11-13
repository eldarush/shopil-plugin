"""Build a portable plugin ZIP and checksum without Git data or machine-specific files."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugins/shopil-plugin'


def build(output=None):
    if '.'.join(map(str, sys.version_info[:3])) != (ROOT / '.python-version').read_text().strip():
        raise RuntimeError('Build the plugin with the Python version pinned in .python-version (3.14.10).')
    version = json.loads((PLUGIN / '.codex-plugin/plugin.json').read_text(encoding='utf-8'))['version']
    output = Path(output) if output else ROOT / 'dist'
    output.mkdir(parents=True, exist_ok=True)
    target = output / f'shopil-plugin-{version}.zip'
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(PLUGIN.rglob('*')):
            if path.is_file() and not any(p in {'__pycache__', '.git', '.venv'} for p in path.parts) and path.suffix != '.pyc':
                info = zipfile.ZipInfo(path.relative_to(PLUGIN).as_posix(), (2026, 11, 13, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                archive.writestr(info, path.read_bytes())
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix('.zip.sha256').write_text(f'{digest}  {target.name}\n', encoding='utf-8')
    return target


if __name__ == '__main__':
    print(build())
