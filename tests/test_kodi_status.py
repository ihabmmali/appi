import subprocess
import sys
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugin.video.appi'


class KodiStatusTests(unittest.TestCase):
    def test_native_status_is_read_without_an_appi_copy(self):
        code = r'''
import json, sys, types
from pathlib import Path
PLUGIN=Path(sys.argv[1]); sys.path.insert(0,str(PLUGIN))
state={'request':None}
xbmc=types.ModuleType('xbmc'); xbmc.LOGWARNING=2; xbmc.log=lambda *a,**k: None
def rpc(raw):
    state['request']=json.loads(raw)
    return json.dumps({'jsonrpc':'2.0','id':1,'result':{'filedetails':{
        'playcount':2,'resume':{'position':345.5,'total':1800.0}
    }}})
xbmc.executeJSONRPC=rpc; sys.modules['xbmc']=xbmc
from resources.lib import kodi_status
path='plugin://plugin.video.appi?action=play_ref&catalog=tv&ref=e%3Att1%3A1%3A2'
value=kodi_status.details(path)
assert value=={'available':True,'playcount':2,'resume':345.5,'total':1800.0}, value
assert state['request']['method']=='Files.GetFileDetails'
assert state['request']['params']['file']==path
assert state['request']['params']['properties']==['playcount','resume']
'''
        result = subprocess.run(
            [sys.executable, '-c', textwrap.dedent(code), str(PLUGIN)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
