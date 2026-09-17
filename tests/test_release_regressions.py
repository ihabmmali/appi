import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugin.video.appi'
SETTINGS = PLUGIN / 'resources' / 'settings.xml'
STRINGS = PLUGIN / 'resources' / 'language' / 'resource.language.en_gb' / 'strings.po'


class SettingsLocalizationTests(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
