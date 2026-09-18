import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugin.video.appi'
SETTINGS = PLUGIN / 'resources' / 'settings.xml'
STRINGS = PLUGIN / 'resources' / 'language' / 'resource.language.en_gb' / 'strings.po'


class SettingsLocalizationTests(unittest.TestCase):
    def test_stable_browser_and_download_batch_features_are_packaged(self):
        addon = ET.parse(PLUGIN / 'addon.xml').getroot()
        self.assertEqual(addon.attrib.get('version'), '0.7.2')
        helper = addon.find("./requires/import[@addon='plugin.video.themoviedb.helper']")
        self.assertIsNotNone(helper)
        self.assertNotEqual(helper.attrib.get('optional'), 'true')
        self.assertEqual(helper.attrib.get('version'), '0.0.0')
        self.assertFalse((PLUGIN / 'resources' / 'lib' / 'browser.py').exists())
        self.assertFalse((PLUGIN / 'resources' / 'skins').exists())
        self.assertTrue((PLUGIN / 'resources' / 'lib' / 'downloads.py').is_file())
        app = (PLUGIN / 'resources' / 'lib' / 'app.py').read_text(encoding='utf-8')
        self.assertIn("'download_ref'", app)
        self.assertIn("'fetch_metadata_batch'", app)
        metadata = (PLUGIN / 'resources' / 'lib' / 'metadata.py').read_text(encoding='utf-8')
        self.assertIn('def show_payload', metadata)
        self.assertIn("'episode_title', 'plot', 'imdb_rating', 'imdb_votes'", metadata)

    def test_po_has_one_entry_per_blank_line_block(self):
        text = STRINGS.read_text(encoding='utf-8')
        blocks = re.split(r'\n\s*\n', text.strip())
        for block in blocks[1:]:
            self.assertLessEqual(
                block.count('msgctxt "#'), 1,
                msg='PO localization entries must be separated by a blank line',
            )

    def test_every_settings_localization_id_exists(self):
        tree = ET.parse(SETTINGS)
        used = set()
        for element in tree.getroot().iter():
            for attr in ('label', 'help'):
                value = element.attrib.get(attr, '')
                if value.isdigit():
                    used.add(value)
            if element.tag == 'heading' and (element.text or '').strip().isdigit():
                used.add((element.text or '').strip())
        for option in tree.getroot().iter('option'):
            value = option.attrib.get('label', '')
            if value.isdigit():
                used.add(value)

        text = STRINGS.read_text(encoding='utf-8')
        defined = set(re.findall(r'msgctxt "#(\d+)"', text))
        self.assertTrue(used)
        self.assertEqual(used - defined, set(), msg='settings.xml references undefined localized strings')

    def test_all_visible_settings_have_labels(self):
        root = ET.parse(SETTINGS).getroot()
        for setting in root.iter('setting'):
            self.assertTrue(setting.attrib.get('label', '').isdigit(), setting.attrib.get('id'))

    def test_maintenance_actions_cover_refresh_and_clear_scopes(self):
        root = ET.parse(SETTINGS).getroot()
        actions = {
            setting.attrib['id']: (setting.findtext('data') or '')
            for setting in root.iter('setting')
            if setting.attrib.get('type') == 'action'
        }
        self.assertEqual(
            set(actions),
            {
                'refresh_movie_list', 'refresh_tv_list', 'refresh_all_lists',
                'clear_movie_cache', 'clear_tv_cache', 'clear_catalog_caches',
                'clear_saved_subtitles', 'clear_recent_media',
                'metadata_status', 'clear_metadata_cache',
                'download_status', 'retry_downloads',
            },
        )
        for scope in ('movies', 'tv', 'catalogs', 'subtitles', 'recent', 'metadata'):
            self.assertTrue(any('scope={}'.format(scope) in value for value in actions.values()))


if __name__ == '__main__':
    unittest.main()
