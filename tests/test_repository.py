import hashlib
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def addon_identity(directory):
    root = ET.parse(directory / 'addon.xml').getroot()
    return root.attrib['id'], root.attrib['version']


class RepositoryTests(unittest.TestCase):
    def test_current_plugin_package_matches_source_tree(self):
        addon_id, version = addon_identity(ROOT / 'plugin.video.appi')
        directory = ROOT / addon_id
        package = directory / f'{addon_id}-{version}.zip'
        expected = {}
        for path in directory.rglob('*'):
            if not path.is_file():
                continue
            if '__pycache__' in path.parts or path.suffix in {'.pyc', '.pyo', '.zip'}:
                continue
            if path.name.endswith('.zip.sha256') or path.name == '.DS_Store':
                continue
            expected[f'{addon_id}/{path.relative_to(directory).as_posix()}'] = path.read_bytes()
        with zipfile.ZipFile(package, 'r') as archive:
            packaged = {
                name: archive.read(name)
                for name in archive.namelist()
                if name and not name.endswith('/')
            }
        self.assertEqual(set(packaged), set(expected))
        for name, value in expected.items():
            self.assertEqual(packaged[name], value, name)

    def test_addons_xml_contains_both_addons(self):
        root = ET.parse(ROOT / 'addons.xml').getroot()
        self.assertEqual({a.attrib['id'] for a in root.findall('addon')}, {'plugin.video.appi', 'repository.appi'})

    def test_sha256_matches_addons_xml(self):
        data = (ROOT / 'addons.xml').read_bytes()
        expected = (ROOT / 'addons.xml.sha256').read_text(encoding='ascii').strip()
        self.assertEqual(hashlib.sha256(data).hexdigest(), expected)

    def test_packages_and_root_bootstraps(self):
        plugin_id, plugin_version = addon_identity(ROOT / 'plugin.video.appi')
        repo_id, repo_version = addon_identity(ROOT / 'repository.appi')
        packages = [
            (ROOT / plugin_id / f'{plugin_id}-{plugin_version}.zip', plugin_id),
            (ROOT / repo_id / f'{repo_id}-{repo_version}.zip', repo_id),
            (ROOT / f'{plugin_id}-{plugin_version}.zip', plugin_id),
        ]
        for package, addon_id in packages:
            with self.subTest(package=package.name), zipfile.ZipFile(package, 'r') as archive:
                self.assertIsNone(archive.testzip())
                names = archive.namelist()
                top = {name.split('/', 1)[0] for name in names if name}
                self.assertEqual(top, {addon_id})
                self.assertIn(addon_id + '/', names)
                self.assertIn(addon_id + '/addon.xml', names)

    def test_package_sha256_sidecars_match(self):
        for directory in (ROOT / 'plugin.video.appi', ROOT / 'repository.appi'):
            addon_id, version = addon_identity(directory)
            package = directory / f'{addon_id}-{version}.zip'
            expected = package.with_name(package.name + '.sha256').read_text(encoding='ascii').strip()
            self.assertEqual(hashlib.sha256(package.read_bytes()).hexdigest(), expected)

    def test_pages_lists_only_direct_plugin(self):
        plugin_id, plugin_version = addon_identity(ROOT / 'plugin.video.appi')
        html = (ROOT / 'index.html').read_text(encoding='utf-8')
        plugin_name = f'{plugin_id}-{plugin_version}.zip'
        self.assertIn(f'href="{plugin_name}">{plugin_name}</a>', html)
        self.assertIn(
            'href="plugin.video.appi-0.6.3.zip">plugin.video.appi-0.6.3.zip</a>',
            html,
        )
        self.assertIn(
            'href="plugin.video.appi-0.7.0.zip">plugin.video.appi-0.7.0.zip</a>',
            html,
        )
        self.assertNotIn('repository.appi-', html)
        self.assertFalse(any(ROOT.glob('repository.appi-*.zip')))

    def test_repository_schema_sha256(self):
        manifest = ET.parse(ROOT / 'repository.appi' / 'addon.xml').getroot()
        directory = manifest.find("./extension[@point='xbmc.addon.repository']/dir")
        self.assertIsNotNone(directory)
        self.assertEqual(directory.findtext('hashes'), 'sha256')
        self.assertEqual(directory.find('checksum').attrib.get('verify'), 'sha256')


if __name__ == '__main__':
    unittest.main()
