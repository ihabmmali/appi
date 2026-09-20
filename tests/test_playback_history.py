import subprocess
import sys
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugin.video.appi'


class PlaybackHistoryTests(unittest.TestCase):
    def test_recent_lists_and_resume_progress(self):
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
from resources.lib import playback_history
movie={'kind':'movie','display_title':'Movie (2025)','title':'Movie','year':2025,'tvg_id':'tt1'}
ep1={'kind':'episode','display_title':'Show S01 E01','show_title':'Show','year':2025,'tvg_id':'tt2','season':1,'episode':1}
ep2={'kind':'episode','display_title':'Show S01 E02','show_title':'Show','year':2025,'tvg_id':'tt2','season':1,'episode':2}
playback_history.start_session('movies','m:tt1',movie)
playback_history.update_progress(321,1200)
assert playback_history.resume_point('movies','m:tt1')==(321.0,1200.0)
assert playback_history.reset_resume('movies','m:tt1') is True
assert playback_history.resume_point('movies','m:tt1') is None
assert playback_history.recent_movies()[0]['title']=='Movie'
playback_history.finish_session(False)
show_key='tt2\\x1fShow\\x1f2025'
playback_history.start_session('tv','e:tt2:1:1',ep1,show_key)
playback_history.update_progress(600,1800)
playback_history.finish_session(False)
playback_history.start_session('tv','e:tt2:1:2',ep2,show_key)
playback_history.update_progress(50,1800)
recent=playback_history.recent_shows()
assert len(recent)==1 and recent[0]['ref']=='e:tt2:1:2'
playback_history.finish_session(True)
assert playback_history.get_entry('tv','e:tt2:1:2')['completed'] is True
assert playback_history.is_watched(show_key,'e:tt2:1:2') is True
assert playback_history.set_watched(show_key,'e:tt2:1:2',ep2,False) is True
assert playback_history.is_watched(show_key,'e:tt2:1:2') is False
assert playback_history.set_watched(show_key,'e:tt2:1:2',ep2,True) is True
assert playback_history.resume_point('tv','e:tt2:1:2') is None
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
