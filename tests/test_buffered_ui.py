import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugin.video.appi'


class BufferedOverlayTests(unittest.TestCase):
    def test_debug_overlay_prefers_window_xml_dialog(self):
        code = r"""
import sys, types
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1])))
state={'logs':[], 'labels':[], 'shown':0, 'closed':0, 'xml':0}
xbmc=types.ModuleType('xbmc'); xbmc.LOGWARNING=2; xbmc.LOGINFO=1
xbmc.log=lambda message, level=0: state['logs'].append(message)
sys.modules['xbmc']=xbmc
xa=types.ModuleType('xbmcaddon')
class Addon:
    def getAddonInfo(self,name): return str(Path(sys.argv[1])) if name=='path' else ''
xa.Addon=Addon; sys.modules['xbmcaddon']=xa
xg=types.ModuleType('xbmcgui')
class Label:
    def setLabel(self,value): state['labels'].append(value)
    def setText(self,value): state['labels'].append(value)
class XMLDialog:
    def __init__(self,*args,**kwargs): state['xml']+=1; self.control=Label()
    def getControl(self,id): return self.control
    def show(self): state['shown']+=1; self.onInit()
    def close(self): state['closed']+=1
xg.WindowXMLDialog=XMLDialog
class Dialog:
    def __init__(self): raise RuntimeError('fallback should not be used')
xg.WindowDialog=Dialog
xg.ControlLabel=lambda *a,**k:Label()
sys.modules['xbmcgui']=xg
from resources.lib import buffered_ui
status={'cached_ahead_bytes':5*1024*1024,'buffer_target_bytes':48*1024*1024,
'high_water_bytes':96*1024*1024,'buffer_capacity_mb':128,'buffered_seconds':9.5,
'recovering':False,'buffer_state':'filling','epoch_id':3,'epoch_reason':'seek',
'selected_bitrate_mbps':6.0,'throughput_mbps':12.5,'total_cached_bytes':20*1024*1024}
overlay=buffered_ui.BufferOverlay()
overlay.update(status,debug=False,playing=True); assert state['shown']==0
overlay.update(status,debug=True,playing=True)
assert state['shown']==1 and state['xml']==1
assert '5.0 MB / 48.0 MB' in state['labels'][-1]
assert '9.5 s ahead' in state['labels'][-1]
assert 'epoch 3 (seek)' in state['labels'][-1]
assert '20.0 MB total' in state['labels'][-1]
assert state['labels'][-1].count('\n') == 3
assert any('WindowXMLDialog' in value for value in state['logs'])
overlay.update(status,debug=False,playing=True)
assert state['closed']==1
overlay.update(None,debug=True,playing=True); assert state['closed']==1
"""
        result = subprocess.run(
            [sys.executable, '-c', code, str(PLUGIN)],
            capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_overlay_falls_back_and_logs_xml_failure(self):
        code = r"""
import sys, types
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1])))
state={'logs':[], 'labels':[], 'shown':0}
xbmc=types.ModuleType('xbmc'); xbmc.LOGWARNING=2; xbmc.LOGINFO=1
xbmc.log=lambda message, level=0: state['logs'].append(message)
sys.modules['xbmc']=xbmc
xa=types.ModuleType('xbmcaddon')
class Addon:
    def getAddonInfo(self,name): return str(Path(sys.argv[1])) if name=='path' else ''
xa.Addon=Addon; sys.modules['xbmcaddon']=xa
xg=types.ModuleType('xbmcgui')
class BrokenXML:
    def __init__(self,*a,**k): raise RuntimeError('xml blocked')
xg.WindowXMLDialog=BrokenXML
class Label:
    def __init__(self,*a,**k): pass
    def setLabel(self,value): state['labels'].append(value)
class Dialog:
    def addControl(self,label): self.label=label
    def show(self): state['shown']+=1
    def close(self): pass
xg.ControlLabel=Label; xg.WindowDialog=Dialog
sys.modules['xbmcgui']=xg
from resources.lib import buffered_ui
status={'cached_ahead_bytes':1024,'buffer_target_bytes':2048,'buffered_seconds':1,
'recovering':True,'buffer_state':'filling','epoch_id':1}
overlay=buffered_ui.BufferOverlay(); overlay.update(status,debug=True,playing=True)
assert state['shown']==1 and state['labels']
assert any('WindowXMLDialog failed' in value for value in state['logs']),state['logs']
"""
        result = subprocess.run(
            [sys.executable, '-c', code, str(PLUGIN)],
            capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
