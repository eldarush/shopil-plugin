import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugins/shopil-plugin'


class PackageTests(unittest.TestCase):
    def test_catalog_resolves_plugin_and_skills(self):
        catalog = json.loads((ROOT / '.agents/plugins/marketplace.json').read_text())
        entry = catalog['plugins'][0]
        plugin = ROOT / entry['source']['path']
        manifest = json.loads((plugin / '.codex-plugin/plugin.json').read_text())
        self.assertEqual(entry['name'], manifest['name'])
        self.assertRegex(manifest['version'], r'^\d+\.\d+\.\d+$')
        for name in ['jira-workflow', 'ponytail', 'shopil-project']:
            text = (plugin / f'skills/{name}/SKILL.md').read_text(encoding='utf-8')
            self.assertTrue(text.startswith('---\n'))
            self.assertIn(f'name: {name}\n', text)
            self.assertRegex(text, r'(?m)^description:')

    def test_course_originals_are_present_and_byte_exact(self):
        manifest = json.loads((PLUGIN / 'skills/shopil-project/references/materials-manifest.json').read_text(encoding='utf-8'))
        files = manifest['files']
        self.assertEqual(15, len(files))
        for item in files:
            path = PLUGIN / item['path']
            self.assertEqual(item['bytes'], path.stat().st_size, item['path'])
            self.assertEqual(item['sha256'], hashlib.sha256(path.read_bytes()).hexdigest(), item['path'])
            if item['text_path']:
                self.assertGreater((PLUGIN / item['text_path']).stat().st_size, 100)

    def test_complete_labs_contain_required_notebooks_and_starters(self):
        assets = PLUGIN / 'skills/shopil-project/assets/course'
        with zipfile.ZipFile(assets / 'etl-course-demo-main.zip') as archive:
            names = archive.namelist()
            for suffix in ['ETL_Course_Lab_HE.ipynb', 'exercises/starter/04_reviews_pipeline.py', 'data/raw/reviews.json', 'scripts/generate_data.py']:
                self.assertTrue(any(p.endswith('/' + suffix) for p in names), suffix)
            self.assertIsNone(archive.testzip())
        with zipfile.ZipFile(assets / 'streaming-course-demo-main.zip') as archive:
            for suffix in ['Streaming_Lab_HE.ipynb', 'src/streaming_lab/engine.py', 'src/streaming_lab/events.py']:
                self.assertTrue(any(p.endswith('/' + suffix) for p in archive.namelist()), suffix)
            self.assertIsNone(archive.testzip())

    def test_authored_markdown_links_resolve(self):
        for path in PLUGIN.rglob('*.md'):
            if 'extracted' in path.parts:
                continue
            for match in re.finditer(r'\]\((?:<([^>]+)>|([^\s)]+))\)', path.read_text(encoding='utf-8')):
                target = match[1] or match[2]
                if '://' in target or target.startswith('#'):
                    continue
                self.assertTrue((path.parent / target.split('#')[0]).exists(), f'{path}: {target}')

    def test_reproducible_archive_has_manifest_assets_and_no_caches(self):
        spec = importlib.util.spec_from_file_location('packager', ROOT / 'scripts/package_plugin.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            first = module.build(Path(directory) / 'a')
            second = module.build(Path(directory) / 'b')
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                self.assertIn('.codex-plugin/plugin.json', archive.namelist())
                self.assertNotIn('plugin.json', archive.namelist())
                self.assertIn('THIRD_PARTY_NOTICES.md', archive.namelist())
                self.assertTrue(any(p.endswith('etl-course-demo-main.zip') for p in archive.namelist()))
                self.assertFalse(any('__pycache__' in p or '.git/' in p for p in archive.namelist()))
                self.assertIsNone(archive.testzip())


if __name__ == '__main__':
    unittest.main()
