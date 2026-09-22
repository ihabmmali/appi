import subprocess
import sys
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugin.video.appi'


class SubtitleServiceSmokeTests(unittest.TestCase):
    def test_saved_off_and_search_modes(self):
        code = r'''
import os, sys, tempfile, types
from pathlib import Path
PLUGIN=Path(sys.argv[1]); sys.path.insert(0,str(PLUGIN))
profile=tempfile.mkdtemp(prefix='appi-sub-'); temp=tempfile.mkdtemp(prefix='appi-temp-')
settings={'persist_subtitles':'true','auto_saved_subtitles':'true'}
state={'builtins':[], 'set':[], 'show':[]}
xbmc=types.ModuleType('xbmc'); xbmc.LOGWARNING=2
class Player:
    def __init__(self): pass
    def setSubtitles(self,p): state['set'].append(p)
    def showSubtitles(self,v): state['show'].append(v)
    def isPlayingVideo(self): return False
xbmc.Player=Player
xbmc.executebuiltin=lambda v: state['builtins'].append(v)
xbmc.log=lambda *a,**k: None
xbmc.Monitor=type('Monitor',(),{})
sys.modules['xbmc']=xbmc
xg=types.ModuleType('xbmcgui')
class Dialog:
    def yesno(self,*a,**k): return False
xg.Dialog=Dialog; sys.modules['xbmcgui']=xg
xa=types.ModuleType('xbmcaddon')
class Addon:
    def getSetting(self,n): return settings.get(n,'')
    def getAddonInfo(self,n): return profile if n=='profile' else ''
xa.Addon=Addon; sys.modules['xbmcaddon']=xa
xv=types.ModuleType('xbmcvfs'); xv.translatePath=lambda p: temp if p=='special://temp/' else p; xv.exists=os.path.exists; xv.mkdirs=lambda p: os.makedirs(p,exist_ok=True)
sys.modules['xbmcvfs']=xv
from resources.lib import subtitle_store, subtitle_service
from resources.lib import playback_history
# Create one persistent subtitle through the store index directly using the public capture path.
subtitle_store.prepare_session('movies','m:tt1')
source=os.path.join(temp,'one.srt')
open(source,'w').write('1\\n00:00:00,000 --> 00:00:01,000\\nHello\\n')
subtitle_store.capture_temp_changes(); subtitle_store.capture_temp_changes()
subtitle_store.clear_session()
player=subtitle_service.AppiPlayer()
subtitle_store.prepare_session('movies','m:tt1', subtitle_mode='saved')
player.onAVStarted(); assert state['set'], state
subtitle_store.clear_session(); state['set'].clear(); state['show'].clear()
subtitle_store.prepare_session('movies','m:tt1', subtitle_mode='off')
player.onAVStarted(); assert not state['set'], state
subtitle_store.clear_session()
subtitle_store.prepare_session('movies','m:tt1', subtitle_mode='search')
player.onAVStarted(); assert state['builtins']==['ActivateWindow(subtitlesearch)'], state
player.onAVStarted(); assert len(state['builtins'])==1, state
subtitle_store.clear_all()
assert subtitle_store.saved_subtitles('movies','m:tt1') == []
assert subtitle_store.load_session() is None
settings['auto_next_episode']='true'
episode={'kind':'episode','display_title':'Series S01 E01','show_title':'Series','season':1,'episode':1,'tvg_id':'tt9000001'}
show_key='tt9000001\\x1fSeries\\x1f2042'
playback_history.start_session('tv','e:tt9000001:1:1',episode,show_key)
player.onPlayBackEnded()
assert any(value.startswith('PlayMedia(plugin://plugin.video.appi/?action=play_next') for value in state['builtins']), state
assert 'completed=1' in state['builtins'][-1], state
'''
        result = subprocess.run(
            [sys.executable, '-c', textwrap.dedent(code), str(PLUGIN)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
