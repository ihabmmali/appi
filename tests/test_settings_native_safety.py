"""Guard the native Kodi parser preconditions, not only XML well-formedness."""
import importlib.util
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugin.video.appi'


def unsafe_options(root):
    # Kodi CSettingString::Deserialize dereferences option->FirstChild()->Value().
    return [s.attrib['id'] for s in root.iter('setting')
            if any(o.text is None or not o.text.strip()
                   for o in s.findall('./constraints/options/option'))]


class NativeSettingsSafetyTests(unittest.TestCase):
    def test_released_0717_fixture_has_the_native_null_child_trigger(self):
        with zipfile.ZipFile(PLUGIN/'plugin.video.appi-0.7.17.zip') as z:
            settings=ET.fromstring(z.read('plugin.video.appi/resources/settings.xml'))
        self.assertEqual(unsafe_options(settings),[
            'preferred_audio_language_choice','preferred_subtitle_language_choice'])

    def test_source_and_shipped_settings_have_nonempty_options_and_valid_defaults(self):
        version=ET.parse(PLUGIN/'addon.xml').getroot().get('version')
        with zipfile.ZipFile(PLUGIN/('plugin.video.appi-'+version+'.zip')) as z:
            shipped=z.read('plugin.video.appi/resources/settings.xml')
        source=(PLUGIN/'resources/settings.xml').read_bytes()
        self.assertEqual(source,shipped)
        for data in (source,shipped):
            root=ET.fromstring(data)
            self.assertEqual(unsafe_options(root),[])
            for setting in root.iter('setting'):
                options=setting.findall('./constraints/options/option')
                if options:
                    self.assertIn(setting.findtext('default'),[o.text for o in options],setting.get('id'))

    def test_migration_handles_fresh_default_legacy_and_existing_empty_settings(self):
        spec=importlib.util.spec_from_file_location('native_safety_languages',PLUGIN/'resources/lib/languages.py')
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        for values,expected in [
            ({'preferred_audio_language_choice':'none','preferred_audio_language':'English'},'en'),
            ({'preferred_audio_language_choice':'none'},''),
            ({'language_choices_migrated':'true','preferred_audio_language_choice':'none','preferred_audio_language':'eng'},''),
            ({'language_choices_migrated':'true','preferred_audio_language_choice':'','preferred_audio_language':'eng'},''),
            ({'language_choices_migrated':'true','preferred_audio_language_choice':'ar'},'ar'),
        ]:
            with self.subTest(values=values):
                addon=SimpleNamespace(getSetting=lambda k:values.get(k,''),setSetting=lambda k,v:values.update({k:v}))
                m.migrate_preferences(addon)
                self.assertEqual(m.preference(addon,'audio'),expected)
                self.assertTrue(values['preferred_audio_language_choice'])
                self.assertEqual(m.normalize('none'),'')
                m.migrate_preferences(addon)
                self.assertEqual(m.preference(addon,'audio'),expected)
