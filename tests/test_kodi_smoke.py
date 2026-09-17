import subprocess
import sys
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugin.video.appi'


class KodiControllerSmokeTests(unittest.TestCase):
    def test_indexed_browse_search_refresh_sort_and_playback_paths(self):
        code = r'''
import os, sys, tempfile, types
from pathlib import Path
from urllib.error import HTTPError
PLUGIN = Path(sys.argv[1])
sys.path.insert(0, str(PLUGIN))
sys.argv = ['plugin://plugin.video.appi', '1', '']
state = {'items': [], 'content': [], 'sort': [], 'ended': [], 'notifications': []}
settings = {
    'movie_sort':'0','tv_sort':'0',
    'persist_subtitles':'false','auto_saved_subtitles':'true',
    'manage_mp4_buffer':'false','hls_quality_mode':'1',
    'tv_m3u_base_url':'https://provider.invalid/tv',
    'request_timeout':'20'
}
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
xg=types.ModuleType('xbmcgui'); xg.NOTIFICATION_ERROR=1; xg.NOTIFICATION_INFO=0; xg.INPUT_ALPHANUM=0; xg.INPUT_NUMERIC=1
class Tag:
    def __getattr__(self,n): return lambda *a,**k: None
class ListItem:
    def __init__(self,label='',path='',offscreen=False): self.label=label; self.path=path; self.info={}; self.props={}; self.context=[]
    def setInfo(self,t,d): self.info.update(d)
    def setProperty(self,k,v): self.props[k]=v
    def getVideoInfoTag(self): return Tag()
    def setMimeType(self,v): self.mime=v
    def setContentLookup(self,v): self.lookup=v
    def setSubtitles(self,v): self.subs=v
    def addContextMenuItems(self,items,*a,**k): self.context.extend(items)
class Dialog:
    select_answers=[]; input_answers=[]
    def notification(self,*a,**k): state['notifications'].append(a)
    def ok(self,*a,**k): raise AssertionError('unexpected dialog: %r' % (a,))
    def input(self,*a,**k): return self.input_answers.pop(0) if self.input_answers else ''
    def select(self,*a,**k): return self.select_answers.pop(0) if self.select_answers else -1
class DialogProgress:
    def create(self,*a,**k): pass
    def update(self,*a,**k): pass
    def iscanceled(self): return False
    def close(self): pass
xg.ListItem=ListItem; xg.Dialog=Dialog; xg.DialogProgress=DialogProgress; sys.modules['xbmcgui']=xg
xp=types.ModuleType('xbmcplugin')
xp.SORT_METHOD_NONE=0; xp.SORT_METHOD_TITLE_IGNORE_THE=1; xp.SORT_METHOD_YEAR=2; xp.SORT_METHOD_EPISODE=3
xp.addDirectoryItems=lambda h,items,totalItems=0: state['items'].extend(items) or True
xp.setContent=lambda h,c: state['content'].append(c)
xp.addSortMethod=lambda h,m: state['sort'].append(m)
xp.endOfDirectory=lambda *a,**k: state['ended'].append(True) or True
xp.setResolvedUrl=lambda *a,**k: True
sys.modules['xbmcplugin']=xp
from resources.lib import app, playback_prefs

movies=[{'kind':'movie','display_title':'Movie %03d (2025)'%i,'title':'Movie %03d'%i,'year':2025,'tvg_id':'tt%03d'%i,'media_url':'https://x/m%d'%i} for i in range(30)]
shows=[{'show_key':'tt%03d\\x1fShow %03d\\x1f2025'%(i,i),'cache_name':'tv_show_%d'%i,'show_title':'Show %03d'%i,'group_title':'Show %03d (2025)'%i,'year':2025,'tvg_id':'tt%03d'%i,'seasons':[1],'episode_count':1} for i in range(30)]
eps=[{'kind':'episode','display_title':'Show 000 (2025) S01 E01','show_title':'Show 000','year':2025,'tvg_id':'tt000','season':1,'episode':1,'media_url':'https://x/e'}]
app._load_movies=lambda: movies; app._load_tv_shows=lambda: shows; app._load_show_episodes=lambda key: eps

app.show_root()
root_labels=[row[1].label for row in state['items']]
assert root_labels[:5] == [
    'Movies', 'TV Shows', 'Search', 'Recently Played Movies', 'Recently Played TV Shows'
], root_labels
assert not any(label.startswith('Search Movies') for label in [row[1].label for row in state['items']])
state['items'].clear()

app.show_movies()
assert [row[1].label for row in state['items']] == [
    'Browse A-Z', 'Browse by Year',
    'Recently Added (first 500 in provider order)',
    'All Movies (may load slowly)'
]
state['items'].clear()
app.show_browse_index('movies','alpha')
assert [row[1].label for row in state['items']] == ['M (30)']
state['items'].clear()

app.BROWSE_BUCKET_LIMIT=10
app.show_browse_items('movies','alpha','M')
assert len(state['items']) == 3
assert all(row[2] for row in state['items'])
assert not any('Next page' in row[1].label or 'Previous page' in row[1].label for row in state['items'])
state['items'].clear(); state['sort'].clear()
app.show_browse_items('movies','alpha','M','10')
assert len(state['items']) == 10
assert all(not row[2] for row in state['items'])
assert state['sort'] == [0,1,2], state['sort']
assert state['items'][0][1].context and 'configure_playback' in state['items'][0][1].context[0][1]
state['items'].clear()

app.show_tvshows()
assert len(state['items']) == 4
assert state['items'][0][1].label == 'Browse A-Z'
state['items'].clear()
Dialog.select_answers=[2]; Dialog.input_answers=['000']
app.search()
assert len(state['items']) == 2, [row[1].label for row in state['items']]
assert {row[1].label for row in state['items']} == {'Movie 000 (2025) [Movie]', 'Show 000 (2025) [TV Show]'}
assert not any('Next page' in row[1].label for row in state['items'])
state['items'].clear()

app.show_seasons(shows[0]['show_key']); assert len(state['items'])==1 and state['content'][-1]=='seasons'; state['items'].clear()
app.show_episodes(shows[0]['show_key'],'1'); assert len(state['items'])==1 and state['content'][-1]=='episodes'
assert 3 in state['sort']

li=ListItem(); app._configure_hls(li); assert li.props.get('inputstream')=='inputstream.adaptive'; assert li.props.get('inputstream.adaptive.stream_selection_type')=='ask-quality'
settings['hls_quality_mode']='2'; settings['hls_max_bitrate_kbps']='5000'; li2=ListItem(); app._configure_hls(li2); assert li2.props.get('inputstream.adaptive.chooser_bandwidth_max')=='5000000'
Dialog.select_answers=[2,3]
app.configure_playback({'target':'movie','catalog':'movies','ref':'m:tt000'})
pref=playback_prefs.get_target('movie',ref='m:tt000')
assert pref.get('hls_mode')==1
assert pref.get('subtitle_mode')=='search'
li3=ListItem(); app._configure_hls(li3, pref); assert li3.props.get('inputstream.adaptive.stream_selection_type')=='ask-quality'

page1="""#EXTM3U
#EXTINF:-1 tvg-id="tt101" tvg-type="tvshows" group-title="Alpha Show (2025)",Alpha Show S01 E01
https://x/tv/e1
"""
page2="""#EXTM3U
#EXTINF:-1 tvg-id="tt102" tvg-type="tvshows" group-title="Beta Show (2025)",Beta Show S01 E01
https://x/tv/e2
"""
requested=[]
def fake_fetch(url, timeout=20):
    requested.append(url)
    if url.endswith('/1'): return page1
    if url.endswith('/2'): return page2
    raise HTTPError(url, 404, 'end', {}, None)
app.fetch_text=fake_fetch
summaries=app.refresh_tv(show_notification=False)
assert summaries is not None and len(summaries)==2
assert requested == [
    'https://provider.invalid/tv/1',
    'https://provider.invalid/tv/2',
    'https://provider.invalid/tv/3'
]
'''
        result = subprocess.run(
            [sys.executable, '-c', textwrap.dedent(code), str(PLUGIN)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
