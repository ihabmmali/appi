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
import json, os, sys, tempfile, types
from pathlib import Path
from urllib.error import HTTPError
PLUGIN = Path(sys.argv[1])
sys.path.insert(0, str(PLUGIN))
sys.argv = ['plugin://plugin.video.appi', '1', '']
state = {'items': [], 'content': [], 'sort': [], 'ended': [], 'notifications': [], 'selects': [], 'resolved': [], 'builtins': [], 'events': []}
native_status = {}
settings = {
    'movie_sort':'0','tv_sort':'0',
    'persist_subtitles':'false','auto_saved_subtitles':'true',
    'manage_mp4_buffer':'false','hls_quality_mode':'1',
    'auto_next_episode':'false',
    'tv_m3u_base_url':'https://provider.invalid/tv',
    'request_timeout':'20'
}
xbmc = types.ModuleType('xbmc'); xbmc.LOGERROR=1; xbmc.LOGWARNING=2; xbmc.LOGINFO=3
xbmc.log=lambda *a,**k: None
def execute_builtin(value,*a,**k):
    state['builtins'].append(value); state['events'].append(('builtin',value))
xbmc.executebuiltin=execute_builtin
xbmc.getCondVisibility=lambda q: True
def execute_jsonrpc(raw):
    request=json.loads(raw)
    if request.get('method')=='Files.GetFileDetails':
        value=native_status.get(request['params']['file'], {'playcount':0,'resume':{'position':0,'total':0}})
        return json.dumps({'jsonrpc':'2.0','id':request.get('id'),'result':{'filedetails':value}})
    if request.get('method')=='Files.SetFileDetails':
        native_status[request['params']['file']]={'playcount':request['params']['playcount'],'resume':{'position':0,'total':0}}
        return json.dumps({'jsonrpc':'2.0','id':request.get('id'),'result':'OK'})
    return '{"jsonrpc":"2.0","id":1,"result":{"value":0}}'
xbmc.executeJSONRPC=execute_jsonrpc
xbmc.Player=type('Player',(),{}); xbmc.Monitor=type('Monitor',(),{})
xbmc.Actor=lambda name,role='',order=0,thumbnail='': {'name':name,'role':role}
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
    def __init__(self,owner): self.owner=owner
    def setPlot(self,value): self.owner.tagdata['plot']=value
    def setRating(self,*value): self.owner.tagdata['rating']=value
    def setCast(self,value): self.owner.tagdata['cast']=value
    def setTitle(self,value): self.owner.tagdata['tag_title']=value
    def __getattr__(self,n): return lambda *a,**k: None
class ListItem:
    def __init__(self,label='',path='',offscreen=False): self.label=label; self.path=path; self.info={}; self.props={}; self.context=[]; self.art={}; self.tagdata={}
    def setInfo(self,t,d): self.info.update(d)
    def setProperty(self,k,v): self.props[k]=v
    def getVideoInfoTag(self): return Tag(self)
    def setArt(self,value): self.art.update(value)
    def setMimeType(self,v): self.mime=v
    def setContentLookup(self,v): self.lookup=v
    def setSubtitles(self,v): self.subs=v
    def addContextMenuItems(self,items,*a,**k): self.context.extend(items)
class Dialog:
    select_answers=[]; input_answers=[]
    def notification(self,*a,**k): state['notifications'].append(a)
    def ok(self,*a,**k): raise AssertionError('unexpected dialog: %r' % (a,))
    def input(self,*a,**k): return self.input_answers.pop(0) if self.input_answers else ''
    def select(self,*a,**k):
        state['selects'].append((a,k))
        return self.select_answers.pop(0) if self.select_answers else -1
    def yesno(self,*a,**k): return True
class DialogProgress:
    def create(self,*a,**k): pass
    def update(self,*a,**k): pass
    def iscanceled(self): return False
    def close(self): pass
xg.ListItem=ListItem; xg.Dialog=Dialog; xg.DialogProgress=DialogProgress; sys.modules['xbmcgui']=xg
xp=types.ModuleType('xbmcplugin')
xp.SORT_METHOD_NONE=0; xp.SORT_METHOD_UNSORTED=0; xp.SORT_METHOD_DATEADDED=4
xp.SORT_METHOD_TITLE_IGNORE_THE=1; xp.SORT_METHOD_YEAR=2; xp.SORT_METHOD_EPISODE=3
xp.addDirectoryItems=lambda h,items,totalItems=0: state['items'].extend(items) or True
xp.setContent=lambda h,c: state['content'].append(c)
xp.addSortMethod=lambda h,m,*args: state['sort'].append(m)
def end_directory(*a,**k):
    state['ended'].append((a,k)); state['events'].append(('end',k)); return True
xp.endOfDirectory=end_directory
xp.setResolvedUrl=lambda *a,**k: state['resolved'].append((a,k)) or True
sys.modules['xbmcplugin']=xp
from resources.lib import app, favorites, metadata, playback_history, playback_prefs

movies=[{'kind':'movie','display_title':'Movie %03d (2025)'%i,'title':'Movie %03d'%i,'year':2025,'tvg_id':'tt%03d'%i,'media_url':'https://x/m%d'%i} for i in range(30)]
shows=[{'show_key':'tt%03d\\x1fShow %03d\\x1f2025'%(i,i),'cache_name':'tv_show_%d'%i,'show_title':'Show %03d'%i,'group_title':'Show %03d (2025)'%i,'year':2025,'tvg_id':'tt%03d'%i,'seasons':[1],'episode_count':1} for i in range(30)]
eps=[{'kind':'episode','display_title':'Show 000 (2025) S01 E01','show_title':'Show 000','year':2025,'tvg_id':'tt000','season':1,'episode':1,'media_url':'https://x/e'}]
app._load_movies=lambda: movies; app._load_tv_shows=lambda: shows; app._load_show_episodes=lambda key: eps

lookup=metadata.lookup_payload(movies[0])
enriched={'plot':'Cached plot','poster':'https://img/poster.jpg','cast':[{'name':'Actor','role':'Lead'}],'imdb_rating':7.7,'imdb_votes':99}
with metadata._connect() as connection:
    connection.execute('INSERT INTO metadata(cache_key,fetched_at,data) VALUES(?,?,?)',(metadata.cache_key(lookup),1,json.dumps(enriched)))

app.show_root()
root_labels=[row[1].label for row in state['items']]
assert root_labels[:5] == [
    'Movies', 'TV Shows', 'Search', 'Recently Played Movies', 'Recently Played TV Shows'
], root_labels
assert root_labels == root_labels[:5] + [
    'Favorite Movies', 'Favorite TV Shows', 'Settings'
], root_labels
assert not any(label.startswith('Refresh ') for label in root_labels), root_labels
assert not any(label.startswith('Search Movies') for label in [row[1].label for row in state['items']])
root_context={row[1].label:[entry[0] for entry in row[1].context] for row in state['items']}
assert 'Fetch metadata for everything in this folder' in root_context['Movies']
assert 'Fetch metadata for everything in this folder' in root_context['TV Shows']
assert 'Fetch metadata for all Recently Played Movies' in root_context['Recently Played Movies']
assert 'Fetch metadata for all Recently Played TV Shows' in root_context['Recently Played TV Shows']
assert state['ended'], 'root directory did not finish'
assert state['ended'][-1][1].get('cacheToDisc') is False, state['ended'][-1]
state['items'].clear()

app.show_movies()
assert [row[1].label for row in state['items']] == [
    'Browse A-Z', 'Browse by Year',
    'Recently Added (first 500 in provider order)',
    'All Movies (may load slowly)'
]
state['items'].clear()
app.show_browse_all('movies')
assert [row[1].label for row in state['items'][:3]] == [
    'Movie 000 (2025)', 'Movie 001 (2025)', 'Movie 002 (2025)'
]
assert state['items'][0][1].info['title'] == 'Movie 000 (2025)'
assert state['items'][0][1].art['poster'] == 'https://img/poster.jpg'
assert state['items'][0][1].tagdata['plot'] == 'IMDb: 7.7/10\nCast: Actor\n\nCached plot'
assert state['items'][0][1].tagdata['rating'] == (7.7, 99, 'imdb', True)
assert 'dateadded' not in state['items'][0][1].info
assert any('Add to Appi Favorites' == row[0] for row in state['items'][0][1].context)
assert state['items'][0][1].context[0][0] == 'Add to Appi Favorites'
assert not any('in Appi' in row[0] or row[0].startswith('Resume from saved') or row[0]=='Play from beginning' for row in state['items'][0][1].context)
state['items'].clear(); state['sort'].clear()
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
assert state['items'][0][1].context[0][0] == 'Add to Appi Favorites'
assert any('configure_playback' in row[1] for row in state['items'][0][1].context)
state['items'].clear()

app.show_tvshows()
assert len(state['items']) == 4
assert state['items'][0][1].label == 'Browse A-Z'
state['items'].clear(); state['events'].clear()
Dialog.select_answers=[0]; Dialog.input_answers=['000']
app.search()
assert state['selects'][-1][0][1] == ['Movies and TV Shows', 'Movies', 'TV Shows']
assert len(state['items']) == 2, [row[1].label for row in state['items']]
assert {row[1].label for row in state['items']} == {'Movie 000 (2025) [Movie]', 'Show 000 (2025) [TV Show]'}
assert all(row[1].context[0][0] == 'Add to Appi Favorites' for row in state['items'])
assert not any('Next page' in row[1].label for row in state['items'])
assert not any(value.startswith('Container.Update(') for value in state['builtins'])
state['items'].clear()

# The routed form uses the same synchronous, proven search path and must not
# depend on an asynchronous Container.Update handoff.
app._run_action({'action':'search','scope':'movies','query':'movie 029'})
assert [row[1].label for row in state['items']] == ['Movie 029 (2025)']
state['items'].clear()

app.show_seasons(shows[0]['show_key']); assert len(state['items'])==1 and state['content'][-1]=='seasons'
assert state['items'][0][1].context[0][0]=='Mark season as watched'
state['items'].clear()
app.show_episodes(shows[0]['show_key'],'1'); assert len(state['items'])==1 and state['content'][-1]=='episodes'
assert 3 in state['sort']
app.set_season_watched({'show_key':shows[0]['show_key'],'season':'1'})
assert native_status[app._play_ref_url('tv',app.item_ref(eps[0]),shows[0]['show_key'])]['playcount']==1

li=ListItem(); app._configure_hls(li); assert li.props.get('inputstream')=='inputstream.adaptive'; assert li.props.get('inputstream.adaptive.stream_selection_type')=='ask-quality'
settings['hls_quality_mode']='2'; settings['hls_max_bitrate_kbps']='5000'; li2=ListItem(); app._configure_hls(li2); assert li2.props.get('inputstream.adaptive.chooser_bandwidth_max')=='5000000'
Dialog.select_answers=[2,3]
app.configure_playback({'target':'movie','catalog':'movies','ref':'m:tt000'})
pref=playback_prefs.get_target('movie',ref='m:tt000')
assert pref.get('hls_mode')==1
assert pref.get('subtitle_mode')=='search'
li3=ListItem(); app._configure_hls(li3, pref); assert li3.props.get('inputstream.adaptive.stream_selection_type')=='ask-quality'

favorites.set_favorite('movie','m:tt000',movies[0],True)
state['items'].clear(); app.show_favorite_movies()
assert [row[1].label for row in state['items']] == ['Movie 000 (2025)']
assert any('Remove from Appi Favorites' == row[0] for row in state['items'][0][1].context)

playback_history.start_session('movies','m:tt000',movies[0])
playback_history.finish_session()
app._probe_kind=lambda *a,**k: {'kind':'mp4'}
recent_before=playback_history.recent_movies()
app.play_ref({'catalog':'movies','ref':'m:tt000','kodi_action':'check_exists'})
assert playback_history.recent_movies()==recent_before
app.play_ref({'catalog':'movies','ref':'m:tt000'})
resolved=state['resolved'][-1][0][2]
assert 'StartOffset' not in resolved.props
assert not state['selects'] or state['selects'][-1][0][0] != 'Resume playback'
assert 'position' not in playback_history.get_entry('movies','m:tt000')

progression=[dict(eps[0], episode=n, display_title='Show 000 S01 E%02d'%n, media_url='https://x/e%d'%n) for n in (1,2,3)]
app._load_show_episodes=lambda key: progression
show_key=shows[0]['show_key']
def native_path(item): return app._play_ref_url('tv',app.item_ref(item),show_key)
native_status[native_path(progression[0])]={'playcount':1,'resume':{'position':0,'total':1800}}
assert app._next_episode_for_show(show_key,'e:tt000:1:1')['episode']==2
native_status[native_path(progression[1])]={'playcount':1,'resume':{'position':0,'total':1800}}
assert app._next_episode_for_show(show_key,'e:tt000:1:1')['episode']==3
native_status[native_path(progression[1])]={'playcount':0,'resume':{'position':400,'total':1800}}
assert app._next_episode_for_show(show_key,'e:tt000:1:1')['episode']==2
assert app._next_episode_for_show(show_key,'e:tt000:1:1',after_completed=True)['episode']==2

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
