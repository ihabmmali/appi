import subprocess
import sys
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugin.video.appi'


class KodiControllerSmokeTests(unittest.TestCase):
    def test_browse_and_hls_configuration_paths(self):
        code = r'''
import os, sys, tempfile, types
from pathlib import Path
PLUGIN = Path(sys.argv[1])
sys.path.insert(0, str(PLUGIN))
sys.argv = ['plugin://plugin.video.appi', '1', '']
state = {'items': [], 'content': [], 'sort': [], 'ended': []}
settings = {'movie_sort':'0','tv_sort':'0','persist_subtitles':'false','manage_mp4_buffer':'false','hls_quality_mode':'1'}
xbmc = types.ModuleType('xbmc'); xbmc.LOGERROR=1; xbmc.LOGWARNING=2; xbmc.LOGINFO=3
xbmc.log=lambda *a,**k: None; xbmc.executebuiltin=lambda *a,**k: None
xbmc.getCondVisibility=lambda q: True
xbmc.executeJSONRPC=lambda s:'{"jsonrpc":"2.0","id":1,"result":{"value":0}}'
xbmc.Player=type('Player',(),{}); xbmc.Monitor=type('Monitor',(),{})
sys.modules['xbmc']=xbmc
profile=tempfile.mkdtemp(prefix='appi-smoke-')
xa=types.ModuleType('xbmcaddon')
class Addon:
    def getSetting(self,n): return settings.get(n,'')
    def getAddonInfo(self,n): return profile if n=='profile' else ('plugin.video.appi' if n=='id' else '')
    def openSettings(self): pass
xa.Addon=Addon; sys.modules['xbmcaddon']=xa
xv=types.ModuleType('xbmcvfs'); xv.translatePath=lambda p: tempfile.gettempdir() if p=='special://temp/' else p; xv.exists=os.path.exists; xv.mkdirs=lambda p: os.makedirs(p,exist_ok=True)
sys.modules['xbmcvfs']=xv
xg=types.ModuleType('xbmcgui'); xg.NOTIFICATION_ERROR=1; xg.NOTIFICATION_INFO=0; xg.INPUT_ALPHANUM=0
class Tag:
    def __getattr__(self,n): return lambda *a,**k: None
class ListItem:
    def __init__(self,label='',path='',offscreen=False): self.label=label; self.path=path; self.info={}; self.props={}
    def setInfo(self,t,d): self.info.update(d)
    def setProperty(self,k,v): self.props[k]=v
    def getVideoInfoTag(self): return Tag()
    def setMimeType(self,v): self.mime=v
    def setContentLookup(self,v): self.lookup=v
    def setSubtitles(self,v): self.subs=v
class Dialog:
    def notification(self,*a,**k): pass
    def ok(self,*a,**k): raise AssertionError('unexpected dialog: %r' % (a,))
    def input(self,*a,**k): return ''
class DialogProgress:
    def create(self,*a,**k): pass
    def update(self,*a,**k): pass
    def iscanceled(self): return False
    def close(self): pass
xg.ListItem=ListItem; xg.Dialog=Dialog; xg.DialogProgress=DialogProgress; sys.modules['xbmcgui']=xg
xp=types.ModuleType('xbmcplugin'); xp.SORT_METHOD_TITLE_IGNORE_THE=1; xp.SORT_METHOD_YEAR=2; xp.SORT_METHOD_EPISODE=3
xp.addDirectoryItems=lambda h,items,totalItems=0: state['items'].extend(items) or True
xp.setContent=lambda h,c: state['content'].append(c)
xp.addSortMethod=lambda h,m: state['sort'].append(m)
xp.endOfDirectory=lambda *a,**k: state['ended'].append(True) or True
xp.setResolvedUrl=lambda *a,**k: True
sys.modules['xbmcplugin']=xp
from resources.lib import app
movies=[{'kind':'movie','display_title':'Beta (2020)','title':'Beta','year':2020,'tvg_id':'tt2','media_url':'https://x/2'},{'kind':'movie','display_title':'Alpha (2025)','title':'Alpha','year':2025,'tvg_id':'tt1','media_url':'https://x/1'}]
shows=[{'show_key':'ttx\\x1fShow\\x1f2025','cache_name':'tv_show_x','show_title':'Show','group_title':'Show (2025)','year':2025,'tvg_id':'ttx','seasons':[1],'episode_count':1}]
eps=[{'kind':'episode','display_title':'Show (2025) S01 E01','show_title':'Show','year':2025,'tvg_id':'ttx','season':1,'episode':1,'media_url':'https://x/e'}]
app._load_movies=lambda: movies; app._load_tv_shows=lambda: shows; app._load_show_episodes=lambda key: eps
app.show_movies(); assert len(state['items'])==2 and state['content'][-1]=='movies'; state['items'].clear()
app.show_tvshows(); assert len(state['items'])==1 and state['content'][-1]=='tvshows'; state['items'].clear()
app.show_seasons(shows[0]['show_key']); assert len(state['items'])==1 and state['content'][-1]=='seasons'; state['items'].clear()
app.show_episodes(shows[0]['show_key'],'1'); assert len(state['items'])==1 and state['content'][-1]=='episodes'
li=ListItem(); app._configure_hls(li); assert li.props.get('inputstream')=='inputstream.adaptive'; assert li.props.get('inputstream.adaptive.stream_selection_type')=='ask-quality'
settings['hls_quality_mode']='2'; settings['hls_max_bitrate_kbps']='5000'; li2=ListItem(); app._configure_hls(li2); assert li2.props.get('inputstream.adaptive.chooser_bandwidth_max')=='5000000'
'''
        result = subprocess.run(
            [sys.executable, '-c', textwrap.dedent(code), str(PLUGIN)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
