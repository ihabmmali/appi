import subprocess
import sys
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugin.video.appi'


class BrowserTests(unittest.TestCase):
    def test_viewport_queue_and_live_listitem_update(self):
        code = r'''
import os, sys, tempfile, types
from pathlib import Path
PLUGIN=Path(sys.argv[1]); sys.path.insert(0,str(PLUGIN))
profile=tempfile.mkdtemp(prefix='appi-browser-')
xbmc=types.ModuleType('xbmc'); xbmc.LOGWARNING=2
xbmc.log=lambda *a,**k: None; xbmc.Actor=lambda name,role='',order=0,thumbnail='':{'name':name,'role':role}
xbmc.executebuiltin=lambda *a,**k: None; sys.modules['xbmc']=xbmc
xa=types.ModuleType('xbmcaddon')
class Addon:
    def getSetting(self,n): return ''
    def getAddonInfo(self,n): return profile if n=='profile' else str(PLUGIN)
xa.Addon=Addon; sys.modules['xbmcaddon']=xa
xv=types.ModuleType('xbmcvfs'); xv.translatePath=lambda p:p; xv.exists=os.path.exists; xv.mkdirs=lambda p:os.makedirs(p,exist_ok=True)
sys.modules['xbmcvfs']=xv
xg=types.ModuleType('xbmcgui'); xg.NOTIFICATION_ERROR=1
class Tag:
    def __init__(self,owner): self.owner=owner
    def setPlot(self,v): self.owner.plot=v
    def setRating(self,*v): self.owner.rating=v
    def setCast(self,v): self.owner.cast=v
    def setDirectors(self,v): self.owner.directors=v
    def setTitle(self,v): self.owner.title=v
    def __getattr__(self,n): return lambda *a,**k: None
class ListItem:
    def __init__(self,label='',offscreen=False,**k): self.label=label; self.offscreen=offscreen; self.props={}; self.art={}; self.title=''; self.plot=''
    def setProperty(self,k,v): self.props[k]=v
    def getVideoInfoTag(self): return Tag(self)
    def setArt(self,v): self.art.update(v)
    def setLabel(self,v): self.label=v
class ControlList:
    def __init__(self): self.items=[]; self.position=0
    def reset(self): self.items=[]
    def addItems(self,v): self.items.extend(v)
    def selectItem(self,v): self.position=v
    def getSelectedPosition(self): return self.position
class Label:
    def setLabel(self,v): self.value=v
class WindowXML:
    def __init__(self,*a,**k): self.controls={1:Label(),50:ControlList()}
    def getControl(self,i): return self.controls[i]
    def setFocusId(self,i): pass
    def close(self): pass
class Dialog:
    def notification(self,*a,**k): pass
    def select(self,*a,**k): return -1
xg.ListItem=ListItem; xg.WindowXML=WindowXML; xg.Dialog=Dialog; sys.modules['xbmcgui']=xg
from resources.lib import browser, metadata
queued=[]
metadata.queue_many=lambda payloads,priority=0,**k: queued.append((payloads,priority)) or len(payloads)
movies=[{'kind':'movie','title':'Movie %03d'%i,'display_title':'Movie %03d'%i,'year':2025,'tvg_id':'tt%03d'%i,'media_url':'https://x/%d'%i} for i in range(450)]
window=browser.AppiBrowser('x',str(PLUGIN),'Default','1080i',False)
window.configure(browser.movie_entries(movies),'Movies','plugin://plugin.video.appi')
window.list_control=window.getControl(50)
window._rebuild(0)
assert len(queued[-1][0])==13 and queued[-1][1]==100, queued[-1]
assert len(window.list_items)==browser.INITIAL_LIST_ITEMS
assert all(item.offscreen is False for item in window.list_items)
window.list_control.selectItem(20); window._queue_viewport(20)
assert len(queued[-1][0])==25, len(queued[-1][0])
payload=metadata.lookup_payload(movies[20])
data={'plot':'Live plot','poster':'https://img/poster.jpg','cast':[{'name':'Actor','role':'Lead'}],'directors':['Director'],'imdb_rating':8.4,'imdb_votes':9}
metadata.get_many=lambda payloads:{metadata.cache_key(payload):data}
window._refresh_viewport(20)
item=window.list_items[20]
assert item.plot=='Live plot' and item.art['poster']=='https://img/poster.jpg'
assert item.rating==(8.4,9,'imdb',True)
assert item.directors==['Director']
window.list_control.selectItem(browser.INITIAL_LIST_ITEMS-browser.LOAD_AHEAD_ITEMS)
window._load_ahead(window.list_control.getSelectedPosition())
assert len(window.list_items)==browser.INITIAL_LIST_ITEMS+browser.LIST_ITEM_BATCH
'''
        result = subprocess.run(
            [sys.executable, '-c', textwrap.dedent(code), str(PLUGIN)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
