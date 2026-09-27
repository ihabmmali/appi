import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugin.video.appi'
sys.path.insert(0, str(PLUGIN))

from resources.lib import hls, languages, refresh_logic


class Release0713LogicTests(unittest.TestCase):
    def test_hls_master_parser_resolves_variants(self):
        text = """#EXTM3U
#EXT-X-STREAM-INF:BANDWIDTH=2500000,RESOLUTION=1280x720,CODECS="avc1.4d401f,mp4a.40.2"
low/playlist.m3u8
#EXT-X-STREAM-INF:AVERAGE-BANDWIDTH=6000000,RESOLUTION=1920x1080
https://cdn.example/high.m3u8
"""
        variants = hls.parse_master(text, 'https://provider.example/root/master.m3u8?token=secret')
        self.assertEqual(len(variants), 2)
        self.assertEqual(variants[0]['url'], 'https://provider.example/root/low/playlist.m3u8?token=secret')
        self.assertEqual(variants[0]['height'], 720)
        self.assertEqual(variants[1]['bandwidth'], 6000000)
        self.assertIn('1080p', hls.variant_label(variants[1]))

    def test_fast_refresh_overlap_merge(self):
        old = [{'media_url': 'u{}'.format(i)} for i in range(1, 21)]
        unchanged, evidence = refresh_logic.merge_leading(old, old[:8])
        self.assertEqual(unchanged, old)
        self.assertEqual(evidence['added'], 0)

        leading = [
            {'media_url': 'new-a'}, {'media_url': 'new-b'}, {'media_url': 'new-c'}
        ] + old[:10]
        merged, evidence = refresh_logic.merge_leading(old, leading)
        self.assertEqual([row['media_url'] for row in merged[:5]], ['new-a', 'new-b', 'new-c', 'u1', 'u2'])
        self.assertEqual(evidence['added'], 3)

        no_overlap, evidence = refresh_logic.merge_leading(old, [{'media_url': 'x{}'.format(i)} for i in range(10)])
        self.assertIsNone(no_overlap)
        self.assertEqual(evidence['reason'], 'no-overlap')

    def test_language_aliases_match(self):
        self.assertEqual(languages.normalize('English'), 'en')
        self.assertEqual(languages.normalize('eng'), 'en')
        self.assertEqual(languages.normalize('en-CA'), 'en')
        self.assertEqual(languages.match_index('English', ['spa', 'eng']), 1)
        self.assertEqual(languages.match_index('eng', ['French', 'English']), 1)
        self.assertIsNone(languages.match_index('', ['eng']))

    def test_search_history_is_bounded_deduplicated_and_corruption_safe(self):
        code = r'''
import json, os, sys, tempfile, types
from pathlib import Path
PLUGIN=Path(sys.argv[1]); sys.path.insert(0,str(PLUGIN))
profile=tempfile.mkdtemp(prefix='appi-search-profile-')
xa=types.ModuleType('xbmcaddon')
class Addon:
    def getAddonInfo(self,name): return profile if name=='profile' else ''
xa.Addon=Addon; sys.modules['xbmcaddon']=xa
xv=types.ModuleType('xbmcvfs')
xv.translatePath=lambda p:p
xv.exists=os.path.exists
xv.mkdirs=lambda p: os.makedirs(p,exist_ok=True)
sys.modules['xbmcvfs']=xv
from resources.lib import search_history
for index in range(25):
    search_history.add('term-{}'.format(index))
assert len(search_history.entries()) == 20
search_history.add('TERM-24')
assert search_history.entries()[0] == 'TERM-24'
assert len([x for x in search_history.entries() if x.casefold() == 'term-24']) == 1
search_history.delete('term-24')
assert all(x.casefold() != 'term-24' for x in search_history.entries())
search_history.clear()
assert search_history.entries() == []
with open(os.path.join(profile,'search_history.json'),'w',encoding='utf-8') as handle:
    handle.write('{broken')
assert search_history.entries() == []
'''
        result = subprocess.run(
            [sys.executable, '-c', textwrap.dedent(code), str(PLUGIN)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_refresh_state_serializes_and_resets_backoff_state(self):
        code = r'''
import os, sys, tempfile, types
from pathlib import Path
PLUGIN=Path(sys.argv[1]); sys.path.insert(0,str(PLUGIN))
profile=tempfile.mkdtemp(prefix='appi-refresh-profile-')
xa=types.ModuleType('xbmcaddon')
class Addon:
    def getAddonInfo(self,name): return profile if name=='profile' else ''
xa.Addon=Addon; sys.modules['xbmcaddon']=xa
xv=types.ModuleType('xbmcvfs')
xv.translatePath=lambda p:p
sys.modules['xbmcvfs']=xv
from resources.lib import refresh_state
assert refresh_state.acquire() is True
assert refresh_state.acquire() is False
refresh_state.release()
assert refresh_state.acquire() is True
refresh_state.release()
failed=refresh_state.record(False)
assert failed['failures'] == 1 and failed['last_attempt']
passed=refresh_state.record(True)
assert passed['failures'] == 0 and passed['last_success']
'''
        result = subprocess.run(
            [sys.executable, '-c', textwrap.dedent(code), str(PLUGIN)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class DiagnosticPrivacyTests(unittest.TestCase):
    def test_export_redacts_authenticated_url(self):
        code = r'''
import json, os, shutil, sys, tempfile, types, zipfile
from pathlib import Path
PLUGIN=Path(sys.argv[1]); sys.path.insert(0,str(PLUGIN))
profile=tempfile.mkdtemp(prefix='appi-diag-profile-')
out=tempfile.mkdtemp(prefix='appi-diag-out-')
settings={'diagnostics_enabled':'true'}
xbmc=types.ModuleType('xbmc')
xbmc.getInfoLabel=lambda name: '21.2 Omega' if name=='System.BuildVersion' else ''
xbmc.getCondVisibility=lambda name: name=='System.Platform.Android'
sys.modules['xbmc']=xbmc
xa=types.ModuleType('xbmcaddon')
class Addon:
    def getSetting(self,name): return settings.get(name,'')
    def getAddonInfo(self,name):
        if name=='profile': return profile
        if name=='version': return '0.7.14'
        if name=='id': return 'plugin.video.appi'
        return ''
xa.Addon=Addon; sys.modules['xbmcaddon']=xa
xv=types.ModuleType('xbmcvfs')
xv.translatePath=lambda p:p
xv.exists=os.path.exists
xv.mkdirs=lambda p: os.makedirs(p,exist_ok=True)
xv.copy=lambda src,dst: (shutil.copy2(src,dst) or True)
sys.modules['xbmcvfs']=xv
from resources.lib import diagnostics
url='https://user:pass@example.com/private/title/master.m3u8?token=TOPSECRET&sig=ABC123'
diagnostics.prepare_playback('movies','m:tt1',url,'hls','inputstream.adaptive',{'hls_mode':2})
diagnostics.event('test', note='safe')
diagnostics.finish('stopped')
target=diagnostics.export_latest(out)
with zipfile.ZipFile(target,'r') as archive:
    raw=archive.read('summary.json').decode('utf-8')
assert 'example.com' in raw
for forbidden in ('TOPSECRET','ABC123','user:pass','/private/title/master.m3u8'):
    assert forbidden not in raw, (forbidden, raw)
payload=json.loads(raw)
assert payload['availability']['per_segment_http_timing'] is False
assert payload['availability']['inputstream_buffer_level'] is False
'''
        result = subprocess.run(
            [sys.executable, '-c', textwrap.dedent(code), str(PLUGIN)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
