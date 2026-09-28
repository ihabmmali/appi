import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugin.video.appi'


class BufferedOverlayTests(unittest.TestCase):
    def test_debug_overlay_and_gui_failures_are_nonfatal_and_specific(self):
        code = r"""
import sys, types
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1])))
state={'logs':[], 'labels':[], 'added':0, 'removed':0, 'fail_add':False}
xbmc=types.ModuleType('xbmc'); xbmc.LOGWARNING=2
xbmc.log=lambda message, level=0: state['logs'].append(message)
sys.modules['xbmc']=xbmc
xg=types.ModuleType('xbmcgui')
class Label:
    def __init__(self,*args,**kwargs): self.value=''
    def setLabel(self,value): self.value=value; state['labels'].append(value)
class Window:
    def __init__(self,window_id): self.window_id=window_id
    def addControl(self,label):
        if state['fail_add']: raise RuntimeError('blocked')
        state['added']+=1
    def removeControl(self,label): state['removed']+=1
xg.ControlLabel=Label; xg.Window=Window
sys.modules['xbmcgui']=xg
from resources.lib import buffered_ui
status={
    'cached_ahead_bytes': 5*1024*1024,
    'buffer_capacity_mb': 128,
    'buffered_seconds': 9.5,
    'recovering': False,
}
overlay=buffered_ui.BufferOverlay()
overlay.update(status, debug=False, playing=True)
assert state['added']==0
overlay.update(status, debug=True, playing=True)
assert state['added']==1
assert '5.0 MB / 128 MB' in state['labels'][-1]
assert '9.5 s ahead' in state['labels'][-1]
overlay.update(None, debug=True, playing=True)
assert state['removed']==1

state['fail_add']=True
failing=buffered_ui.BufferOverlay()
failing.update(status, debug=True, playing=True)
assert failing.label is None
assert any('addControl failed' in value for value in state['logs']),state['logs']
"""
        result = subprocess.run(
            [sys.executable, '-c', code, str(PLUGIN)],
            capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
