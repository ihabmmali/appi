import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugin.video.appi'


class LanguageRuntimeTests(unittest.TestCase):
    def test_preferences_retry_until_kodi_enumerates_streams_and_external_subtitle_wins(self):
        code = r"""
import sys, types
from pathlib import Path
plugin = Path(sys.argv[1])
sys.path.insert(0, str(plugin))
settings = {
    'language_choices_migrated': 'true',
    'preferred_audio_language_choice': 'en',
    'preferred_subtitle_language_choice': 'fr',
    'auto_saved_subtitles': 'true',
    'persist_subtitles': 'false',
}
state = {'session': {}, 'saved': '', 'builtins': []}
xbmc = types.ModuleType('xbmc')
xbmc.LOGWARNING = 2
xbmc.log = lambda *a, **k: None
xbmc.executebuiltin = lambda value: state['builtins'].append(value)
xbmc.convertLanguage = lambda value, fmt: {
    'eng':'en','english':'en','en':'en',
    'fre':'fr','fra':'fr','french':'fr','fr':'fr',
    'spa':'es','es':'es',
}.get(str(value).lower(), '')
xbmc.ISO_639_1 = 0
class BasePlayer:
    def __init__(self):
        self.audio_streams=[]; self.subtitle_streams=[]
        self.audio_selected=[]; self.subtitle_selected=[]
        self.external=[]; self.subtitle_visibility=[]
    def getAvailableAudioStreams(self): return list(self.audio_streams)
    def getAvailableSubtitleStreams(self): return list(self.subtitle_streams)
    def setAudioStream(self,index): self.audio_selected.append(index)
    def setSubtitleStream(self,index): self.subtitle_selected.append(index)
    def setSubtitles(self,path): self.external.append(path)
    def showSubtitles(self,value): self.subtitle_visibility.append(bool(value))
    def getPlayingFile(self): return 'https://provider.invalid/playing'
    def isPlayingVideo(self): return True
xbmc.Player=BasePlayer
sys.modules['xbmc']=xbmc
xa=types.ModuleType('xbmcaddon')
class Addon:
    def getSetting(self,key): return settings.get(key,'')
    def setSetting(self,key,value): settings[key]=value
xa.Addon=Addon
sys.modules['xbmcaddon']=xa
for name in ('buffered_hls','diagnostics','playback_history','metadata','refresh_state'):
    sys.modules['resources.lib.'+name]=types.ModuleType('resources.lib.'+name)
sys.modules['resources.lib.buffered_hls'].BufferedHlsManager=type('BufferedHlsManager',(),{})
sys.modules['resources.lib.diagnostics'].player_started=lambda player: None
sys.modules['resources.lib.diagnostics'].finish=lambda result: None
sys.modules['resources.lib.diagnostics'].event=lambda *a,**k: None
sys.modules['resources.lib.diagnostics'].enabled=lambda: False
sys.modules['resources.lib.playback_history'].finish_session=lambda: {}
sys.modules['resources.lib.metadata'].decode_focus=lambda value: None
sys.modules['resources.lib.metadata'].queue=lambda payload: None
sys.modules['resources.lib.metadata'].process_one=lambda: None
sys.modules['resources.lib.refresh_state'].load=lambda: {}
ui=types.ModuleType('resources.lib.buffered_ui')
ui.BufferOverlay=type('BufferOverlay',(),{'update':lambda *a,**k:None,'close':lambda *a,**k:None})
sys.modules['resources.lib.buffered_ui']=ui
ss=types.ModuleType('resources.lib.subtitle_store')
ss.load_session=lambda:dict(state['session'])
ss.last_saved_subtitle=lambda catalog,ref:state['saved']
ss.clear_session=lambda:None
ss.capture_temp_changes=lambda *a,**k:None
sys.modules['resources.lib.subtitle_store']=ss
from resources.lib import subtitle_service
p=subtitle_service.AppiPlayer()
p.onAVStarted()
assert p.audio_selected==[] and p.subtitle_selected==[]
p.audio_streams=['eng','spa']; p.subtitle_streams=['eng','fre']
p.apply_pending_languages()
assert p.audio_selected==[0],p.audio_selected
assert p.subtitle_selected==[1],p.subtitle_selected
state['session']={'subtitle_mode':'global','catalog':'tv','ref':'episode'}
state['saved']='/tmp/downloaded.srt'
p2=subtitle_service.AppiPlayer()
p2.onAVStarted()
assert p2.external==['/tmp/downloaded.srt'],p2.external
p2.subtitle_streams=['fre']
p2.apply_pending_languages()
assert p2.subtitle_selected==[],p2.subtitle_selected
settings['preferred_audio_language_choice']='none'
settings['preferred_subtitle_language_choice']='none'
state['session']={}; state['saved']=''
p3=subtitle_service.AppiPlayer()
p3.audio_streams=['eng']; p3.subtitle_streams=['fre']
p3.onAVStarted()
assert p3.audio_selected==[] and p3.subtitle_selected==[]
"""
        result = subprocess.run([sys.executable,'-c',code,str(PLUGIN)],
                                capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)


if __name__ == '__main__':
    unittest.main()
