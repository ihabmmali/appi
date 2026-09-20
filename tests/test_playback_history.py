import subprocess
import sys
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugin.video.appi'


class PlaybackHistoryTests(unittest.TestCase):
    def test_recent_identity_only_and_legacy_status_reset(self):
        code = r'''
import os, sys, tempfile, types
from pathlib import Path
PLUGIN=Path(sys.argv[1]); sys.path.insert(0,str(PLUGIN))
profile=tempfile.mkdtemp(prefix='appi-history-')
xa=types.ModuleType('xbmcaddon')
class Addon:
    def getAddonInfo(self,n): return profile if n=='profile' else ''
xa.Addon=Addon; sys.modules['xbmcaddon']=xa
xv=types.ModuleType('xbmcvfs'); xv.translatePath=lambda p:p; xv.exists=os.path.exists; xv.mkdirs=lambda p:os.makedirs(p,exist_ok=True)
sys.modules['xbmcvfs']=xv
from resources.lib import cache, playback_history
movie={'kind':'movie','display_title':'Movie (2025)','title':'Movie','year':2025,'tvg_id':'tt1'}
ep1={'kind':'episode','display_title':'Show S01 E01','show_title':'Show','year':2025,'tvg_id':'tt2','season':1,'episode':1}
ep2={'kind':'episode','display_title':'Show S01 E02','show_title':'Show','year':2025,'tvg_id':'tt2','season':1,'episode':2}
cache.save_object('playback_history', {'movies': {'legacy': {'position': 321}}})
cache.save_object('watched_episodes', {'legacy-show': {'legacy': {}}})
playback_history.start_session('movies','m:tt1',movie)
assert playback_history.recent_movies()[0]['title']=='Movie'
assert cache.load_object('playback_history') is None
assert cache.load_object('watched_episodes') is None
entry=playback_history.get_entry('movies','m:tt1')
assert 'position' not in entry and 'total' not in entry and 'completed' not in entry
playback_history.finish_session()
show_key='tt2\x1fShow\x1f2025'
playback_history.start_session('tv','e:tt2:1:1',ep1,show_key)
playback_history.finish_session()
playback_history.start_session('tv','e:tt2:1:2',ep2,show_key)
recent=playback_history.recent_shows()
assert len(recent)==1 and recent[0]['ref']=='e:tt2:1:2'
playback_history.finish_session()
assert 'completed' not in playback_history.get_entry('tv','e:tt2:1:2')
assert playback_history.remove('movies','m:tt1') is True
assert playback_history.recent_movies()==[]
assert playback_history.remove_show(show_key) is True
assert playback_history.recent_shows()==[]
'''
        result = subprocess.run(
            [sys.executable, '-c', textwrap.dedent(code), str(PLUGIN)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
