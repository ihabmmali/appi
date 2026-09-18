import subprocess
import sys
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugin.video.appi'


class DownloadTests(unittest.TestCase):
    def test_queue_paths_hls_packaging_and_nfo(self):
        code = r'''
import os, sys, tempfile, threading, types
from pathlib import Path
PLUGIN=Path(sys.argv[1]); sys.path.insert(0,str(PLUGIN))
profile=tempfile.mkdtemp(prefix='appi-download-')
settings={'download_folder':os.path.join(profile,'offline'),'hls_max_bitrate_kbps':'8000'}
xbmc=types.ModuleType('xbmc'); xbmc.LOGWARNING=2; xbmc.LOGERROR=1
xbmc.log=lambda *a,**k: None; xbmc.executeJSONRPC=lambda value:'{}'
sys.modules['xbmc']=xbmc
xa=types.ModuleType('xbmcaddon')
class Addon:
    def getSetting(self,n): return settings.get(n,'')
    def getAddonInfo(self,n): return profile if n=='profile' else ''
xa.Addon=Addon; sys.modules['xbmcaddon']=xa
xg=types.ModuleType('xbmcgui'); xg.NOTIFICATION_ERROR=1
class Dialog:
    def notification(self,*a,**k): pass
xg.Dialog=Dialog; sys.modules['xbmcgui']=xg
xv=types.ModuleType('xbmcvfs'); xv.translatePath=lambda p:p; xv.exists=os.path.exists; xv.mkdirs=lambda p:os.makedirs(p,exist_ok=True)
sys.modules['xbmcvfs']=xv
from resources.lib import downloads
movie={'kind':'movie','title':'A/B: Movie','display_title':'A/B: Movie (2025)','year':2025,'tvg_id':'tt1','media_url':'https://x/movie'}
assert downloads.queue_item('movies',movie)
assert not downloads.queue_item('movies',movie)
assert downloads.status()['queued']==1
job={'download_id':'movies|m:tt1','catalog':'movies','show_key':'','item':movie}
base=downloads._base_destination(job,{})
assert 'A_B_ Movie (2025)' in base, base
playlist="""#EXTM3U
#EXT-X-TARGETDURATION:4
#EXTINF:4,
one.ts
#EXTINF:4,
two.ts
#EXT-X-ENDLIST
"""
init, segments=downloads._parse_hls('https://x/path/list.m3u8',playlist)
assert init is None and [value[0] for value in segments]==['https://x/path/one.ts','https://x/path/two.ts']
def fake_resource(url, byte_range, path, stop_event, playing_callback=lambda:False):
    with open(path,'wb') as handle: handle.write(b'one' if url.endswith('one.ts') else b'two')
downloads._download_resource=fake_resource
target=downloads._download_hls('https://x/path/list.m3u8',playlist,base,'movies|m:tt1',threading.Event())
assert target.endswith('.ts') and open(target,'rb').read()==b'onetwo'
downloads._write_nfo(target,job,{'plot':'Plot','imdb_rating':8.1,'imdb_votes':10,'imdb_id':'tt1','cast':[{'name':'Actor','role':'Lead'}],'directors':['Director']})
assert os.path.exists(os.path.splitext(target)[0]+'.nfo')
nfo=open(os.path.splitext(target)[0]+'.nfo',encoding='utf-8').read()
assert '<director>Director</director>' in nfo
episode={'kind':'episode','show_title':'Example Show','display_title':'Example Show S01 E02','year':2025,'tvg_id':'tt2','season':1,'episode':2,'media_url':'https://x/episode'}
episode_job={'download_id':'tv|e:tt2:1:2','catalog':'tv','show_key':'show','item':episode}
episode_base=downloads._base_destination(episode_job,{})
downloads._write_nfo(episode_base+'.mp4',episode_job,{})
assert os.path.exists(os.path.join(os.path.dirname(os.path.dirname(episode_base)), 'tvshow.nfo'))
class Response:
    status=200
    headers={'Content-Length':'6'}
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def getcode(self): return self.status
    def read(self,size): return b'abcdef'
downloads.urlopen=lambda *a,**k:Response()
paused=os.path.join(profile,'paused.mp4')
try:
    downloads._download_direct('https://x/direct',paused,'pause',threading.Event(),lambda:True)
    raise AssertionError('active download should yield to playback')
except downloads.PlaybackStarted:
    pass
assert os.path.exists(paused+'.part') and not os.path.exists(paused)
try:
    downloads._parse_hls('https://x/list.m3u8','#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI="key"\n#EXTINF:1,\na.ts\n#EXT-X-ENDLIST')
    raise AssertionError('encrypted HLS should be rejected')
except RuntimeError as exc:
    assert 'Encrypted HLS' in str(exc)
master="""#EXTM3U
#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="audio",NAME="English",DEFAULT=YES,AUTOSELECT=YES,URI="audio.m3u8"
#EXT-X-STREAM-INF:BANDWIDTH=1000000,CODECS="avc1.4d401f,mp4a.40.2",AUDIO="audio"
video.m3u8
"""
video="""#EXTM3U
#EXT-X-TARGETDURATION:4
#EXTINF:4,
video-1.m4s
#EXT-X-ENDLIST
"""
audio="""#EXTM3U
#EXT-X-TARGETDURATION:4
#EXTINF:4,
audio-1.m4s
#EXT-X-ENDLIST
"""
downloads.fetch_text=lambda url,timeout=30: {
    'https://x/video.m3u8':video,
    'https://x/audio.m3u8':audio,
}[url]
bundle_base=os.path.join(settings['download_folder'],'separate-audio')
bundle=downloads._download_hls(
    'https://x/master.m3u8',master,bundle_base,'separate',threading.Event()
)
assert bundle.endswith('.strm') and os.path.exists(bundle)
local_master=open(bundle,encoding='utf-8').read().strip()
assert os.path.exists(local_master)
master_text=open(local_master,encoding='utf-8').read()
assert 'AUDIO="offline-audio"' in master_text
assert 'audio/playlist.m3u8' in master_text and 'video/playlist.m3u8' in master_text
assert os.path.exists(os.path.join(bundle_base+'.hls','video','video-00000.m4s'))
assert os.path.exists(os.path.join(bundle_base+'.hls','audio','audio-00000.m4s'))
os.remove(bundle)
downloads._cleanup_orphaned_hls()
assert not os.path.exists(bundle_base+'.hls')
'''
        result = subprocess.run(
            [sys.executable, '-c', textwrap.dedent(code), str(PLUGIN)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
