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
    def test_addons_xml_contains_both_addons(self):
        root = ET.parse(ROOT / 'addons.xml').getroot()
        ids = {addon.attrib['id'] for addon in root.findall('addon')}
        self.assertEqual(ids, {'plugin.video.appi', 'repository.appi'})

    def test_sha256_matches_addons_xml(self):
        data = (ROOT / 'addons.xml').read_bytes()
        expected = (ROOT / 'addons.xml.sha256').read_text(encoding='ascii').strip()
        self.assertEqual(hashlib.sha256(data).hexdigest(), expected)

    def test_packages_have_single_correct_top_level_directory(self):
        plugin_id, plugin_version = addon_identity(ROOT / 'plugin.video.appi')
        repo_id, repo_version = addon_identity(ROOT / 'repository.appi')
        packages = [
            (ROOT / plugin_id / f'{plugin_id}-{plugin_version}.zip', plugin_id),
            (ROOT / repo_id / f'{repo_id}-{repo_version}.zip', repo_id),
            (ROOT / f'{repo_id}-{repo_version}.zip', repo_id),
        ]
        for package, addon_id in packages:
            with self.subTest(package=package.name):
                with zipfile.ZipFile(package, 'r') as archive:
                    top = {name.split('/', 1)[0] for name in archive.namelist() if name}
                self.assertEqual(top, {addon_id})

    def test_package_sha256_sidecars_match(self):
        packages = []
        for directory in (ROOT / 'plugin.video.appi', ROOT / 'repository.appi'):
            addon_id, version = addon_identity(directory)
            packages.append(directory / f'{addon_id}-{version}.zip')
        for package in packages:
            with self.subTest(package=package.name):
                expected = package.with_name(package.name + '.sha256').read_text(encoding='ascii').strip()
                self.assertEqual(hashlib.sha256(package.read_bytes()).hexdigest(), expected)

    def test_repository_uses_current_dir_schema_and_sha256(self):
        manifest = ET.parse(ROOT / 'repository.appi' / 'addon.xml').getroot()
        extension = manifest.find("./extension[@point='xbmc.addon.repository']")
        self.assertIsNotNone(extension)
        directory = extension.find('dir')
        self.assertIsNotNone(directory)
        self.assertEqual(directory.findtext('hashes'), 'sha256')
        checksum = directory.find('checksum')
        self.assertEqual(checksum.attrib.get('verify'), 'sha256')

    def test_no_stale_versioned_packages_remain(self):
        for directory in (ROOT / 'plugin.video.appi', ROOT / 'repository.appi'):
            addon_id, version = addon_identity(directory)
            expected = {f'{addon_id}-{version}.zip', f'{addon_id}-{version}.zip.sha256'}
            actual = {p.name for p in directory.glob(f'{addon_id}-*.zip*')}
            self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
