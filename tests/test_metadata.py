import subprocess
import sys
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugin.video.appi'


class MetadataTests(unittest.TestCase):
    def test_queue_fetch_normalisation_and_bounded_cache(self):
        code = r'''
import json, os, sys, tempfile, types
from pathlib import Path
PLUGIN=Path(sys.argv[1]); sys.path.insert(0,str(PLUGIN))
profile=tempfile.mkdtemp(prefix='appi-meta-')
settings={'metadata_enabled':'true','metadata_cache_items':'100'}
xbmc=types.ModuleType('xbmc'); xbmc.LOGWARNING=2
xbmc.log=lambda *a,**k: None
xbmc.getCondVisibility=lambda q: q=='System.HasAddon(plugin.video.themoviedb.helper)'
class Player:
    def isPlayingVideo(self): return False
xbmc.Player=Player
def rpc(raw):
    request=json.loads(raw)
    assert request['method']=='Files.GetDirectory'
    directory=request['params']['directory']
    assert 'plugin.video.themoviedb.helper' in directory
    assert 'query=Example' in directory
    item={
      'title':'Pilot','plot':'A plot','thumbnail':'https://img/poster.jpg',
      'art':{'poster':'https://img/poster.jpg'},
      'rating':9.9,'director':['Director One'],
      'ratings':{'imdb':{'rating':7.6,'votes':12000}},
      'customproperties':{'IMDb_Rating':'7.8','IMDb_Votes':'12,345','IMDb_ID':'tt123'},
      'cast':[{'name':'Actor One','role':'Lead','thumbnail':'https://img/a.jpg'}],
      'uniqueid':{'tmdb':'55'}
    }
    return json.dumps({'jsonrpc':'2.0','id':1,'result':{'files':[item]}})
xbmc.executeJSONRPC=rpc; sys.modules['xbmc']=xbmc
xa=types.ModuleType('xbmcaddon')
class Addon:
    def getSetting(self,n): return settings.get(n,'')
    def getAddonInfo(self,n): return profile if n=='profile' else ''
xa.Addon=Addon; sys.modules['xbmcaddon']=xa
xv=types.ModuleType('xbmcvfs'); xv.translatePath=lambda p:p; xv.exists=os.path.exists; xv.mkdirs=lambda p:os.makedirs(p,exist_ok=True)
sys.modules['xbmcvfs']=xv
from resources.lib import metadata
payload={'media_type':'episode','title':'Example','year':2025,'imdb_id':'tt123','season':1,'episode':1}
assert metadata.queue(payload)
assert metadata.process_one()
data=metadata.get(payload)
assert data['plot']=='A plot'
assert data['poster']=='https://img/poster.jpg'
assert data['cast'][0]['name']=='Actor One'
assert data['directors']==['Director One']
assert data['episode_title']=='Pilot'
assert data['imdb_rating']==7.8 and data['imdb_votes']==12345
# The generic JSON-RPC rating is deliberately ignored; only IMDb_Rating is accepted.
assert data['imdb_rating']!=9.9
fallback=metadata._normalise_result({
    'ratings':{'IMDb':{'rating':8.2,'votes':456}},
    'director':'Director Two / Director Three',
},payload)
assert fallback['imdb_rating']==8.2 and fallback['imdb_votes']==456
assert fallback['directors']==['Director Two','Director Three']
movie={'media_type':'movie','title':'Another','year':2024,'imdb_id':'tt999'}
assert metadata.queue_many([movie, movie], priority=100) == 1
with metadata._connect() as connection:
    row=connection.execute('SELECT priority FROM queue WHERE cache_key=?',(metadata.cache_key(movie),)).fetchone()
    assert row == (100,)
with metadata._connect() as connection:
    connection.execute(
        'INSERT OR REPLACE INTO metadata(cache_key,fetched_at,data) VALUES(?,?,?)',
        (metadata.cache_key(movie),2,json.dumps({'plot':'Another plot'})),
    )
assert metadata.get_many([payload,movie])[metadata.cache_key(movie)]['plot']=='Another plot'
with metadata._connect() as connection:
    for index in range(105):
        connection.execute(
            'INSERT OR REPLACE INTO metadata(cache_key,fetched_at,data) VALUES(?,?,?)',
            ('extra-%03d'%index, index, '{}'),
        )
    metadata._prune(connection)
    assert connection.execute('SELECT COUNT(*) FROM metadata').fetchone()[0] == 100
metadata.clear_all()
assert metadata.status()['cached']==0
'''
        result = subprocess.run(
            [sys.executable, '-c', textwrap.dedent(code), str(PLUGIN)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
