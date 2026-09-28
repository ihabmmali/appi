import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugin.video.appi'


class BufferedOverlayTests(unittest.TestCase):
    def test_debug_overlay_uses_window_dialog_and_gui_failures_are_nonfatal(self):
        code = r"""
import sys, types
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1])))
state={'logs':[], 'labels':[], 'shown':0, 'closed':0, 'added':0, 'fail_show':False}
xbmc=types.ModuleType('xbmc'); xbmc.LOGWARNING=2
xbmc.log=lambda message, level=0: state['logs'].append(message)
sys.modules['xbmc']=xbmc
xg=types.ModuleType('xbmcgui')
class Label:
    def __init__(self,*args,**kwargs): self.value=''
    def setLabel(self,value): self.value=value; state['labels'].append(value)
class Dialog:
    def addControl(self,label): state['added']+=1
    def show(self):
        if state['fail_show']: raise RuntimeError('blocked')
        state['shown']+=1
    def close(self): state['closed']+=1
xg.ControlLabel=Label; xg.WindowDialog=Dialog
sys.modules['xbmcgui']=xg
from resources.lib import buffered_ui
status={
    'cached_ahead_bytes': 5*1024*1024,
    'buffer_target_bytes': 48*1024*1024,
    'high_water_bytes': 96*1024*1024,
    'buffer_capacity_mb': 128,
    'buffered_seconds': 9.5,
    'recovering': False,
    'buffer_state': 'filling',
    'epoch_id': 3,
    'selected_bitrate_mbps': 6.0,
    'throughput_mbps': 12.5,
}
overlay=buffered_ui.BufferOverlay()
overlay.update(status, debug=False, playing=True)
assert state['shown']==0
overlay.update(status, debug=True, playing=True)
assert state['shown']==1 and state['added']==1
assert '5.0 MB / 48.0 MB' in state['labels'][-1]
assert '9.5 s ahead' in state['labels'][-1]
assert 'epoch 3' in state['labels'][-1]
overlay.update(None, debug=True, playing=True)
assert state['closed']==1

status['recovering']=True
plain=buffered_ui.BufferOverlay()
plain.update(status, debug=False, playing=True)
assert 'Appi buffering — 5.0 MB / 48.0 MB' in state['labels'][-1]
plain.close()

state['fail_show']=True
failing=buffered_ui.BufferOverlay()
failing.update(status, debug=True, playing=True)
assert failing.label is None
assert any('show failed' in value for value in state['logs']),state['logs']
"""
        result = subprocess.run(
            [sys.executable, '-c', code, str(PLUGIN)],
            capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
