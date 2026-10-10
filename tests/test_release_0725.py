"""0.7.25 regression checks for pause continuity and subtitle transport/capture."""
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import urlopen

from test_buffered_hls import _load_module, _install_fake_fetch


class Buffered0725Tests(unittest.TestCase):
    def setUp(self):
        self.m = _load_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        media = ('#EXTM3U\n#EXT-X-TARGETDURATION:6\n' +
                 ''.join('#EXTINF:6,\ns%d.ts\n' % i for i in range(36)) +
                 '#EXT-X-ENDLIST\n').encode()
        self.payloads = {'/media.m3u8': media}
        self.payloads.update({'/s%d.ts' % i: b'video-segment' * 200 for i in range(36)})
        _install_fake_fetch(self.m, self.payloads)

    def session(self, url='https://provider/media.m3u8?auth=hidden'):
        session = self.m.BufferedHlsSession(url, buffer_mb=32,
                                            root=os.path.join(self.tmp.name, 'cache'))
        session.start()
        self.addCleanup(session.stop)
        session.prepare()
        self.assertTrue(session.ready, session.error)
        return session

    def test_video_skips_multiple_segments_only_when_playhead_is_unchanged(self):
        session = self.session()
        track = next(iter(session.tracks.values()))
        track.serve(0)
        track.last_requested = 2
        track.last_served = 2
        session._pause_position = 30.0
        session._resume_position = 30.0
        session._player_position = 30.0
        session._resume_position_unchanged = True
        track.resume_pending = True
        track._resume_requests_left = 10
        old_epoch = session.epoch
        self.assertTrue(os.path.isfile(track.serve(5)))
        self.assertEqual(old_epoch, session.epoch)
        events = [(n, f) for n, f in session.drain_events()
                  if n == 'buffer_consumer_request']
        self.assertTrue(any(f.get('request_classification') == 'resume-continuity'
                            and f.get('pause_position_unchanged') for n, f in events))

        # Unchanged Kodi time cannot license a large timeline jump.
        track.resume_pending = True
        old_epoch = session.epoch
        self.assertTrue(os.path.isfile(track.serve(23)))
        self.assertGreater(session.epoch, old_epoch)
        # A real user seek performed while paused must also remain a seek.
        track.resume_pending = True
        session._resume_position_unchanged = False
        old_epoch = session.epoch
        self.assertTrue(os.path.isfile(track.serve(30)))
        self.assertGreater(session.epoch, old_epoch)

    def test_reread_during_pause_keeps_resume_classification_available(self):
        session = self.session()
        track = next(iter(session.tracks.values()))
        track.serve(0)
        track.last_requested = track.last_served = 2
        track.resume_pending = True
        session._pause_position = session._resume_position = 30.0
        session._resume_position_unchanged = True
        track.serve(2, request_context={'range': 'bytes=0-10'})
        self.assertTrue(track.resume_pending)
        old_epoch = session.epoch
        track.serve(5)
        self.assertEqual(session.epoch, old_epoch)

    def test_subtitle_renditions_are_lazy_http_resources_not_required_tracks(self):
        self.payloads['/media.m3u8'] = (
            '#EXTM3U\n'
            '#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="English",'
            'LANGUAGE="en",DEFAULT=YES,AUTOSELECT=YES,URI="en.m3u8"\n'
            '#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="French",'
            'LANGUAGE="fr",DEFAULT=NO,AUTOSELECT=YES,FORCED=NO,URI="fr.m3u8"\n'
            '#EXT-X-STREAM-INF:BANDWIDTH=1000000,SUBTITLES="subs"\nvideo.m3u8\n'
        ).encode()
        self.payloads['/video.m3u8'] = (
            '#EXTM3U\n#EXTINF:6,\ns0.ts\n#EXTINF:6,\ns1.ts\n#EXT-X-ENDLIST\n'
        ).encode()
        for language in ('en', 'fr'):
            self.payloads['/' + language + '.m3u8'] = (
                '#EXTM3U\n#EXTINF:6,\n' + language + '.vtt\n#EXT-X-ENDLIST\n'
            ).encode()
            self.payloads['/' + language + '.vtt'] = b'WEBVTT\n\n00:00.000 --> 00:01.000\nHello\n'
        session = self.session()
        baseline_epoch = session.epoch
        self.assertEqual(len(session._required_startup_tracks()), 1)
        body, _ = session.serve(session.master.id)
        self.assertIn(b'TYPE=SUBTITLES', body)
        self.assertIn(b'FORCED=NO', body)
        renditions = [r for r in session.resources.values()
                      if r.metadata.get('rendition_type') == 'subtitles']
        self.assertEqual(len(renditions), 2)
        for rendition in renditions:
            local = session._local_url(rendition.id)
            with urlopen(local, timeout=3) as response:
                playlist = response.read()
                self.assertEqual(response.headers.get_content_type(),
                                 'application/vnd.apple.mpegurl')
            name = rendition.metadata['language']
            self.assertIn(b'.vtt', playlist)
            text_resources = [r for r in session.resources.values()
                              if r.kind == 'subtitle-segment'
                              and ('/' + name + '.vtt') in r.upstream_url]
            self.assertEqual(len(text_resources), 1)
            with urlopen(session._local_url(text_resources[0].id), timeout=3) as response:
                self.assertEqual(response.headers.get_content_type(), 'text/vtt')
                self.assertTrue(response.read().startswith(b'WEBVTT'))
        self.assertEqual(session.epoch, baseline_epoch)
        self.assertEqual(len(session._required_startup_tracks()), 1)


class SubtitleStore0725Tests(unittest.TestCase):
    def test_nested_temp_custom_folder_and_final_capture(self):
        code = r"""
import json, os, sys, tempfile, types
from pathlib import Path
sys.path.insert(0, sys.argv[1])
profile = tempfile.mkdtemp(); temp = tempfile.mkdtemp(); custom = tempfile.mkdtemp()
xbmcaddon = types.ModuleType('xbmcaddon')
xbmcaddon.Addon = lambda: type('A', (), {'getAddonInfo': lambda self, name: profile})()
sys.modules['xbmcaddon'] = xbmcaddon
xbmcvfs = types.ModuleType('xbmcvfs')
xbmcvfs.translatePath = lambda value: temp if value == 'special://temp/' else value
sys.modules['xbmcvfs'] = xbmcvfs
xbmc = types.ModuleType('xbmc')
xbmc.LOGINFO = 1
xbmc.log = lambda *args, **kw: None
def rpc(request):
    setting = json.loads(request)['params']['setting']
    return json.dumps({'result': {'value': 1 if setting == 'subtitles.storagemode' else custom}})
xbmc.executeJSONRPC = rpc
sys.modules['xbmc'] = xbmc
from resources.lib import subtitle_store as store
store.prepare_session('movies', 'movie-a')
nested = os.path.join(temp, 'provider', 'cache', 'lang')
os.makedirs(nested)
source = os.path.join(nested, 'subtitle.srt')
with open(source, 'w') as fp: fp.write('text')
store.capture_temp_changes()
assert store.load_session()['pending']
store.capture_temp_changes(finalize=True)
os.remove(source)
assert store.last_saved_subtitle('movies', 'movie-a')
store.clear_session()
store.prepare_session('movies', 'movie-b')
with open(os.path.join(custom, 'new.srt'), 'w') as fp: fp.write('alternate')
store.capture_temp_changes(finalize=True)
assert store.last_saved_subtitle('movies', 'movie-b')
assert store.last_saved_subtitle('movies', 'movie-a') != store.last_saved_subtitle('movies', 'movie-b')
store.clear_all()
assert store.last_saved_subtitle('movies', 'movie-a') is None
"""
        root = Path(__file__).resolve().parents[1] / 'plugin.video.appi'
        result = subprocess.run([sys.executable, '-c', code, str(root)],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
