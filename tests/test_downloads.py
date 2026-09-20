import subprocess
import sys
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugin.video.appi'


class DownloadScriptTests(unittest.TestCase):
    def test_atomic_ffmpeg_script_generation_through_kodi_vfs(self):
        code = r'''
import os, subprocess, sys, tempfile, types
from pathlib import Path
PLUGIN=Path(sys.argv[1]); sys.path.insert(0,str(PLUGIN))
profile=tempfile.mkdtemp(prefix='appi-script-')
watch=os.path.join(profile,'watch')
settings={'download_folder':watch}
xbmc=types.ModuleType('xbmc'); xbmc.LOGWARNING=2
xbmc.log=lambda *a,**k:None; xbmc.getCondVisibility=lambda q:True
class Player:
    def isPlayingVideo(self): return False
xbmc.Player=Player; sys.modules['xbmc']=xbmc
xa=types.ModuleType('xbmcaddon')
class Addon:
    def getSetting(self,n): return settings.get(n,'')
    def getAddonInfo(self,n): return profile if n=='profile' else ''
xa.Addon=Addon; sys.modules['xbmcaddon']=xa
xv=types.ModuleType('xbmcvfs'); xv.translatePath=lambda p:p
xv.exists=os.path.exists
xv.mkdirs=lambda p: (os.makedirs(p,exist_ok=True) or True)
xv.rename=lambda source,target: (os.replace(source,target) or True)
xv.delete=lambda p: (os.remove(p) or True) if os.path.exists(p) else True
xv.listdir=lambda p: ([],os.listdir(p))
class File:
    def __init__(self,path,mode): self.handle=open(path,mode,encoding='utf-8')
    def write(self,value): self.handle.write(value); return True
    def close(self): self.handle.close()
xv.File=File; sys.modules['xbmcvfs']=xv
from resources.lib import downloads
movie={
  'kind':'movie','title':'Synthetic/Feature','display_title':'Synthetic/Feature (2042)',
  'year':2042,'tvg_id':'tt9900001',
  'media_url':"https://media.invalid/token/stream.m3u8?label=a'b"
}
result=downloads.generate('movies',movie)
assert result['created'] is True
assert result['path'].endswith('.sh') and os.path.isfile(result['path'])
assert not any('.tmp-' in name for name in os.listdir(watch))
script=open(result['path'],encoding='utf-8').read()
assert subprocess.run(['sh','-n',result['path']],capture_output=True).returncode==0
assert '#!/bin/sh' in script and 'set -eu' in script
assert '-c copy' in script and '-sn -dn' in script and '-f mp4' in script
assert '-map ' not in script and 'ffprobe' not in script
assert 'stream.m3u8' in script and "'\"'\"'" in script
assert 'script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)' in script
assert 'output="$script_dir"/' in script
assert "Synthetic_Feature (2042).mp4" in script
assert '/srv/' not in script
assert '.part.mp4' in script and 'mv -f --' in script
duplicate=downloads.generate('movies',movie)
assert duplicate['created'] is False and duplicate['path']==result['path']
value=downloads.status()
assert value['scripts']==1 and value['folder']==watch

episode={
  'kind':'episode','show_title':'Synthetic Series','display_title':'Synthetic Series S02 E03',
  'year':2042,'tvg_id':'tt9900002','season':2,'episode':3,
  'media_url':'https://media.invalid/episode.mp4'
}
episode_result=downloads.generate('tv',episode,'synthetic-show')
episode_script=open(episode_result['path'],encoding='utf-8').read()
assert 'Synthetic Series - S02E03 - ' in episode_script
assert downloads.status()['scripts']==2
'''
        result = subprocess.run(
            [sys.executable, '-c', textwrap.dedent(code), str(PLUGIN)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
