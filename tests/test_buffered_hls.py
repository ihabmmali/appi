import importlib.util
import os
import shutil
import sys
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / 'plugin.video.appi' / 'resources' / 'lib' / 'buffered_hls.py'


def _load_module():
    temp_root = tempfile.mkdtemp(prefix='appi-buffer-test-')
    addon = types.ModuleType('xbmcaddon')
    addon.Addon = type('Addon', (), {
        'getAddonInfo': lambda self, name: temp_root if name == 'profile' else '0.7.16'
    })
    sys.modules['xbmcaddon'] = addon
    vfs = types.ModuleType('xbmcvfs')
    vfs.translatePath = lambda value: temp_root if value == 'special://temp/' else value
    sys.modules['xbmcvfs'] = vfs

    saved_modules = {
        name: sys.modules.get(name)
        for name in ('resources', 'resources.lib', 'resources.lib.hls', 'resources.lib.buffered_hls')
    }
    resources = types.ModuleType('resources')
    resources.__path__ = []
    lib = types.ModuleType('resources.lib')
    lib.__path__ = []
    hls = types.ModuleType('resources.lib.hls')

    def resolve(base_url, child):
        base_core, base_marker, base_options = base_url.partition('|')
        child_core, child_marker, child_options = child.partition('|')
        resolved = urljoin(base_core, child_core)
        base = urlparse(base_core)
        parsed = urlparse(resolved)
        child_parsed = urlparse(child_core)
        if (
            not child_parsed.scheme
            and not child_parsed.netloc
            and base.query
            and not child_parsed.query
        ):
            parsed = parsed._replace(query=base.query)
            resolved = urlunparse(parsed)
        options = child_options if child_marker else (base_options if base_marker else '')
        return resolved + ('|' + options if options else '')

    hls.resolve_variant_url = resolve
    sys.modules['resources'] = resources
    sys.modules['resources.lib'] = lib
    sys.modules['resources.lib.hls'] = hls
    spec = importlib.util.spec_from_file_location('resources.lib.buffered_hls', MODULE)
    module = importlib.util.module_from_spec(spec)
    sys.modules['resources.lib.buffered_hls'] = module
    spec.loader.exec_module(module)
    module._test_root = temp_root
    for name, previous in saved_modules.items():
        if previous is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous
    return module


def _install_fake_fetch(module, payloads, gate=None):
    def fake_fetch(url, timeout=20.0, byte_range=''):
        core = url.split('|', 1)[0]
        parsed = urlparse(core)
        if gate is not None and parsed.path.startswith('/s'):
            number = int(parsed.path.rsplit('/s', 1)[1].split('.', 1)[0])
            if number >= 1:
                gate.wait(2.0)
        data = payloads[parsed.path]
        return module._FetchResult(
            data,
            core,
            'application/vnd.apple.mpegurl'
            if parsed.path.endswith('.m3u8')
            else 'application/octet-stream',
            200,
            5.0,
            10.0,
        )

    def fake_to_path(url, path, timeout=20.0, byte_range='', **kwargs):
        result = fake_fetch(url, timeout, byte_range)
        Path(path).write_bytes(result.data)
        return result

    module._fetch = fake_fetch
    module._fetch_to_path = fake_to_path


class BufferedHlsTests(unittest.TestCase):
    def setUp(self):
        self.m = _load_module()
        self.addCleanup(lambda: shutil.rmtree(self.m._test_root, ignore_errors=True))

    def test_playlist_rewrite_startup_reserve_and_sanitized_diagnostics(self):
        master = (
            '#EXTM3U\n'
            '#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="a",NAME="English",URI="audio.m3u8"\n'
            '#EXT-X-STREAM-INF:BANDWIDTH=6500000,AVERAGE-BANDWIDTH=5800000,'
            'RESOLUTION=1920x1080,CODECS="avc1.640028,mp4a.40.2",AUDIO="a"\n'
            'video.m3u8\n'
        )
        media = (
            '#EXTM3U\n#EXT-X-TARGETDURATION:6\n#EXT-X-MEDIA-SEQUENCE:10\n'
            '#EXT-X-KEY:METHOD=AES-128,URI="key.bin?keysecret=1",IV=0x1\n'
            '#EXT-X-MAP:URI="init.mp4",BYTERANGE="4@2"\n'
            '#EXTINF:6.0,\nseg10.ts\n#EXTINF:6.0,\nseg11.ts\n'
            '#EXT-X-DISCONTINUITY\n'
            '#EXTINF:6.0,\nseg12.ts\n#EXTINF:6.0,\nseg13.ts\n'
            '#EXTINF:6.0,\nseg14.ts\n#EXTINF:6.0,\nseg15.ts\n#EXT-X-ENDLIST\n'
        )
        audio = (
            '#EXTM3U\n#EXT-X-TARGETDURATION:6\n'
            '#EXTINF:6,\na0.aac\n#EXTINF:6,\na1.aac\n'
            '#EXTINF:6,\na2.aac\n#EXTINF:6,\na3.aac\n#EXT-X-ENDLIST\n'
        )
        payloads = {
            '/master.m3u8': master.encode(),
            '/video.m3u8': media.encode(),
            '/audio.m3u8': audio.encode(),
            '/key.bin': b'0123456789abcdef',
            '/init.mp4': b'init',
        }
        for number in range(10, 16):
            payloads['/seg{}.ts'.format(number)] = b'x' * 200
        for number in range(4):
            payloads['/a{}.aac'.format(number)] = b'a' * 40
        _install_fake_fetch(self.m, payloads)

        session = self.m.BufferedHlsSession(
            'https://up.example/master.m3u8?token=SECRET',
            root=os.path.join(self.m._test_root, 'session'),
        )
        session.start()
        self.addCleanup(lambda: session.stop('test'))

        master_bytes, _ = session.serve(session.master.id)
        rewritten_master = master_bytes.decode()
        self.assertIn('#EXT-X-STREAM-INF:BANDWIDTH=6500000', rewritten_master)
        self.assertIn('#EXT-X-MEDIA:TYPE=AUDIO', rewritten_master)
        self.assertNotIn('SECRET', rewritten_master)
        self.assertNotIn('up.example', rewritten_master)

        variants = [
            resource for resource in session.resources.values()
            if resource.metadata.get('representation')
        ]
        self.assertEqual(len(variants), 1)
        self.assertEqual(variants[0].metadata['representation']['height'], 1080)

        media_bytes, _ = session.serve(variants[0].id)
        rewritten_media = media_bytes.decode()
        self.assertIn('#EXT-X-DISCONTINUITY', rewritten_media)
        self.assertIn('#EXT-X-KEY:METHOD=AES-128,URI="http://127.0.0.1:', rewritten_media)
        self.assertIn('#EXT-X-MAP:URI="http://127.0.0.1:', rewritten_media)
        map_line = next(line for line in rewritten_media.splitlines() if line.startswith('#EXT-X-MAP:'))
        self.assertNotIn('BYTERANGE', map_line)
        maps = [resource for resource in session.resources.values() if resource.kind == 'map']
        self.assertEqual(len(maps), 1)
        self.assertEqual(maps[0].byte_range, '2-5')
        self.assertNotIn('keysecret', rewritten_media)

        track = session.tracks['track-' + variants[0].id]
        self.assertTrue(track.wait_startup(2))
        ahead, count = track._ahead(0)
        self.assertGreaterEqual(ahead, 12.0)
        self.assertGreaterEqual(count, 2)
        events = session.drain_events()
        self.assertTrue(any(name == 'buffer_representation_selected' for name, _ in events))
        downloads = [fields for name, fields in events if name == 'buffer_segment_download']
        self.assertTrue(downloads)
        self.assertIn('throughput_mbps', downloads[0])
        self.assertFalse(any(
            'SECRET' in str(value)
            for _, fields in events
            for value in fields.values()
        ))

    def test_depletion_rebuilds_reserve_instead_of_releasing_one_segment(self):
        m = self.m
        gate = threading.Event()
        payloads = {'/s{}.ts'.format(i): b'z' * 50 for i in range(6)}
        _install_fake_fetch(m, payloads, gate=gate)
        session = m.BufferedHlsSession(
            'https://x/master.m3u8',
            target_seconds=30,
            startup_seconds=18,
            recovery_seconds=15,
            root=os.path.join(m._test_root, 'recovery'),
        )
        session.start()
        self.addCleanup(lambda: session.stop('test'))
        track = m._Track(session, 't', 30, 18, 15)
        session.tracks['t'] = track
        segments = []
        for i in range(6):
            resource = session._register(
                'https://x/s{}.ts'.format(i),
                'segment',
                metadata={'track_id': 't', 'index': i, 'sequence': i},
            )
            segments.append(m._Segment(resource, i, 6.0, i))
        track.replace_segments(segments)

        deadline = time.time() + 2
        while not track._cached(0) and time.time() < deadline:
            time.sleep(0.01)
        thread = threading.Thread(target=lambda: track.serve(1))
        thread.start()
        time.sleep(0.1)
        self.assertTrue(thread.is_alive(), 'request resumed after only one buffered segment')
        gate.set()
        thread.join(3)
        self.assertFalse(thread.is_alive())
        names = [name for name, _ in session.drain_events()]
        self.assertIn('buffer_depletion', names)
        self.assertIn('buffer_recovery', names)

    def test_seek_recenters_and_shutdown_removes_disk_buffer(self):
        m = self.m
        payloads = {'/s{}.ts'.format(i): b'z' * 20 for i in range(8)}
        _install_fake_fetch(m, payloads)
        root = os.path.join(m._test_root, 'seek')
        session = m.BufferedHlsSession(
            'https://x/master.m3u8',
            target_seconds=12,
            startup_seconds=6,
            recovery_seconds=6,
            root=root,
        )
        session.start()
        track = m._Track(session, 't', 12, 6, 6)
        session.tracks['t'] = track
        segments = []
        for i in range(8):
            resource = session._register(
                'https://x/s{}.ts'.format(i),
                'segment',
                metadata={'track_id': 't', 'index': i, 'sequence': i},
            )
            segments.append(m._Segment(resource, i, 3.0, i))
        track.replace_segments(segments)
        self.assertTrue(track.wait_startup(2))
        track.serve(0)
        path = track.serve(5)
        self.assertTrue(os.path.isfile(path))
        self.assertEqual(track.last_served, 5)
        self.assertIn('buffer_seek_recenter', [name for name, _ in session.drain_events()])
        session.stop('test-end')
        self.assertFalse(os.path.exists(root))

    def test_implicit_byteranges_advance(self):
        self.assertEqual(self.m._byterange('100@50'), ('50-149', 149))
        self.assertEqual(self.m._byterange('100', 149), ('150-249', 249))


    def test_startup_waits_for_video_and_default_audio_with_truthful_progress(self):
        m = self.m
        master = (
            '#EXTM3U\n'
            '#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="aud",NAME="English",LANGUAGE="eng",'
            'DEFAULT=YES,AUTOSELECT=YES,URI="audio.m3u8"\n'
            '#EXT-X-STREAM-INF:BANDWIDTH=6000000,RESOLUTION=1920x1080,AUDIO="aud"\n'
            'video.m3u8\n'
        )
        media = (
            '#EXTM3U\n#EXT-X-TARGETDURATION:6\n'
            '#EXTINF:6,\nv0.ts\n#EXTINF:6,\nv1.ts\n#EXTINF:6,\nv2.ts\n'
            '#EXT-X-ENDLIST\n'
        )
        audio = (
            '#EXTM3U\n#EXT-X-TARGETDURATION:6\n'
            '#EXTINF:6,\na0.aac\n#EXTINF:6,\na1.aac\n#EXTINF:6,\na2.aac\n'
            '#EXT-X-ENDLIST\n'
        )
        payloads = {
            '/master.m3u8': master.encode(), '/video.m3u8': media.encode(),
            '/audio.m3u8': audio.encode(),
            '/v0.ts': b'v' * 128, '/v1.ts': b'v' * 128, '/v2.ts': b'v' * 128,
            '/a0.aac': b'a' * 64, '/a1.aac': b'a' * 64, '/a2.aac': b'a' * 64,
        }
        _install_fake_fetch(m, payloads)
        original = m._fetch_to_path
        audio_gate = threading.Event()

        def gated(url, path, **kwargs):
            if urlparse(url.split('|', 1)[0]).path.startswith('/a'):
                audio_gate.wait(2)
            return original(url, path, **kwargs)

        m._fetch_to_path = gated
        session = m.BufferedHlsSession(
            'https://up.example/master.m3u8',
            root=os.path.join(m._test_root, 'associated-audio'),
        )
        session.start()
        self.addCleanup(lambda: session.stop('test'))
        worker = threading.Thread(target=session.prepare)
        worker.start()

        deadline = time.time() + 2
        while len(session._startup_track_ids) < 2 and time.time() < deadline:
            time.sleep(0.01)
        self.assertEqual(len(session._startup_track_ids), 2)

        deadline = time.time() + 2
        while time.time() < deadline:
            required = session._required_startup_tracks()
            if any(t._ahead(0)[0] >= 12 for t in required):
                break
            time.sleep(0.01)
        status = session.status()
        self.assertFalse(status['ready'])
        self.assertEqual(status['percent'], 0)
        self.assertEqual(status['startup_tracks'], 2)

        audio_gate.set()
        worker.join(3)
        self.assertFalse(worker.is_alive())
        self.assertTrue(session.ready, session.error)
        self.assertEqual(session.status()['percent'], 100)

    def test_near_complete_startup_failure_does_not_handoff(self):
        m = self.m
        m.STARTUP_TIMEOUT = 0.35
        media = (
            '#EXTM3U\n#EXT-X-TARGETDURATION:6\n'
            '#EXTINF:5.4,\ns0.ts\n#EXTINF:5.4,\ns1.ts\n#EXTINF:5.4,\ns2.ts\n'
            '#EXT-X-ENDLIST\n'
        )
        payloads = {
            '/media.m3u8': media.encode(),
            '/s0.ts': b'0' * 64, '/s1.ts': b'1' * 64, '/s2.ts': b'2' * 64,
        }
        _install_fake_fetch(m, payloads)
        original = m._fetch_to_path

        def fail_third(url, path, **kwargs):
            if urlparse(url.split('|', 1)[0]).path == '/s2.ts':
                raise RuntimeError('simulated third-segment stall')
            return original(url, path, **kwargs)

        m._fetch_to_path = fail_third
        session = m.BufferedHlsSession(
            'https://up.example/media.m3u8',
            root=os.path.join(m._test_root, 'near-complete'),
        )
        session.start()
        self.addCleanup(lambda: session.stop('test'))
        worker = threading.Thread(target=session.prepare)
        worker.start()

        observed = None
        deadline = time.time() + 1
        while time.time() < deadline:
            status = session.status()
            if (
                status['cached_ahead_bytes'] >= 128
                and not status['ready']
                and status['message'].startswith('Buffering stalled')
            ):
                observed = status
                break
            time.sleep(0.01)
        self.assertIsNotNone(observed, session.status())
        self.assertFalse(observed['ready'])
        self.assertLess(observed['percent'], 100)

        worker.join(2)
        self.assertFalse(worker.is_alive())
        self.assertFalse(session.ready)
        self.assertIn('Startup reservoir incomplete', session.error)

    def test_control_deadline_exceeds_preparation_deadline(self):
        self.assertGreater(self.m.CONTROL_TIMEOUT, self.m.STARTUP_TIMEOUT)


    def test_distinct_tracks_prefetch_concurrently_without_overcommitting_buffer(self):
        m = self.m
        session = m.BufferedHlsSession(
            'https://up.example/master.m3u8',
            root=os.path.join(m._test_root, 'parallel'),
            buffer_mb=32,
        )
        session.start()
        self.addCleanup(lambda: session.stop('test'))

        entered = []
        entered_lock = threading.Lock()
        both_entered = threading.Event()
        release = threading.Event()

        def concurrent_fetch(url, path, timeout=20.0, byte_range='', **kwargs):
            with entered_lock:
                entered.append(url)
                if len(entered) >= 2:
                    both_entered.set()
            release.wait(2)
            Path(path).write_bytes(b'x' * 64)
            return m._FetchResult(b'', url, 'application/octet-stream', 200, 1.0, 2.0, 64)

        m._fetch_to_path = concurrent_fetch
        for track_id, suffix in (('video', 'v0.ts'), ('audio', 'a0.aac')):
            track = m._Track(session, track_id, 30, 6, 6)
            session.tracks[track_id] = track
            resource = session._register(
                'https://up.example/' + suffix,
                'segment',
                metadata={'track_id': track_id, 'index': 0, 'sequence': 0},
            )
            track.replace_segments([m._Segment(resource, 0, 6.0, 0)])

        self.assertTrue(
            both_entered.wait(1.0),
            'independent track downloads were serialized behind one stalled request',
        )
        self.assertLessEqual(session._reserved_bytes, session.max_bytes)
        release.set()

        deadline = time.time() + 2
        while any(not track._cached(0) for track in session.tracks.values()) and time.time() < deadline:
            time.sleep(0.01)
        self.assertTrue(all(track._cached(0) for track in session.tracks.values()))
        self.assertEqual(session._reserved_bytes, 0)


    def test_coordinated_seek_recenters_video_and_audio_by_timeline(self):
        m = self.m
        session = m.BufferedHlsSession(
            'https://up.example/master.m3u8',
            root=os.path.join(m._test_root, 'coordinated-seek'),
        )
        tracks = []
        for track_id, count, duration in (('video', 6, 6.0), ('audio', 12, 3.0)):
            track = m._Track(session, track_id, 30, 6, 6)
            track._stop.set()
            tracks.append(track)
            session.tracks[track_id] = track
            segments = []
            for index in range(count):
                resource = session._register(
                    'https://up.example/{}/{}.bin'.format(track_id, index),
                    'segment',
                    metadata={
                        'track_id': track_id,
                        'index': index,
                        'sequence': index,
                    },
                )
                segments.append(m._Segment(resource, index, duration, index))
            track.replace_segments(segments)
        video, audio = tracks
        video.last_served = 1
        audio.last_served = 3

        session._coordinate_seek(video, 4, reason='seek')
        self.assertEqual(video.last_served, 3)
        # Video index 4 begins at 24 s; 3 s audio segments therefore re-centre
        # at audio index 8, with last_served one segment behind the target.
        self.assertEqual(audio.last_served, 7)
        names = [name for name, _ in session.drain_events()]
        self.assertEqual(names.count('buffer_seek_recenter'), 2)

    def test_cold_resume_nonzero_request_is_treated_as_random_access(self):
        m = self.m
        session = m.BufferedHlsSession(
            'https://up.example/media.m3u8',
            root=os.path.join(m._test_root, 'cold-resume'),
        )
        track = m._Track(session, 'video', 30, 6, 6)
        track._stop.set()
        session.tracks['video'] = track
        segments = []
        for index in range(6):
            resource = session._register(
                'https://up.example/s{}.ts'.format(index),
                'segment',
                metadata={'track_id':'video','index':index,'sequence':index},
            )
            segments.append(m._Segment(resource, index, 6.0, index))
        track.replace_segments(segments)
        # The fresh-epoch path must build a contiguous reserve. Cache the
        # short VOD remainder so the target epoch can become ready without
        # weakening the new reserve gate.
        for index in (4, 5):
            target = track.segments[index].resource
            target.path = os.path.join(session.data_root, 'target-{}.bin'.format(index))
            Path(target.path).write_bytes(b'target')

        path = track.serve(4)
        self.assertEqual(path, track.segments[4].resource.path)
        self.assertEqual(track.last_served, 4)
        events = session.drain_events()
        recenter = [fields for name, fields in events if name == 'buffer_seek_recenter']
        self.assertTrue(recenter)
        self.assertEqual(recenter[0].get('reason'), 'cold-resume')

    def test_recovery_policy_exhaustion_is_internal_and_clears_recovering_state(self):
        m = self.m
        session = m.BufferedHlsSession(
            'https://up.example/media.m3u8',
            root=os.path.join(m._test_root, 'retry-after-timeout'),
            tuning={'recovery_timeout_s': 5, 'retry_attempts': 1, 'retry_delay_ms': 100},
        )
        session._startup_complete = True
        track = m._Track(session, 'video', 3, 1, 1)
        session.tracks['video'] = track
        segments = []
        for index in range(5):
            resource = session._register(
                'https://up.example/s{}.ts'.format(index),
                'segment',
                metadata={'track_id':'video','index':index,'sequence':index},
            )
            segments.append(m._Segment(resource, index, 1.0, index))
        track.replace_segments(segments)

        def failing_fetch(url, path, **kwargs):
            raise TimeoutError('temporary upstream timeout')

        m._fetch_to_path = failing_fetch
        with self.assertRaises(m.RecoveryExhausted):
            track.serve(3)
        self.assertFalse(track.recovering)
        self.assertFalse(session.error)
        self.assertEqual(track.last_served, 2)
        names = [name for name, _ in session.drain_events()]
        self.assertIn('buffer_recovery_retry', names)
        self.assertIn('buffer_failure_snapshot', names)
        self.assertNotIn('buffer_request_retry', names)

        payloads = {'/s{}.ts'.format(i): bytes([65 + i]) * 32 for i in range(5)}
        _install_fake_fetch(m, payloads)
        path = track.serve(3)
        self.assertTrue(os.path.isfile(path))
        self.assertEqual(track.last_served, 3)
        self.assertFalse(session.error)
        track.stop()

    def test_repeated_forward_and_backward_seek_reprioritizes_next_missing(self):
        m = self.m
        session = m.BufferedHlsSession(
            'https://up.example/media.m3u8',
            root=os.path.join(m._test_root, 'repeated-seek'),
        )
        track = m._Track(session, 'video', 30, 6, 6)
        track._stop.set()
        session.tracks['video'] = track
        segments = []
        for index in range(10):
            resource = session._register(
                'https://up.example/s{}.ts'.format(index),
                'segment',
                metadata={'track_id':'video','index':index,'sequence':index},
            )
            segments.append(m._Segment(resource, index, 3.0, index))
        track.replace_segments(segments)

        session._coordinate_seek(track, 7, reason='seek')
        self.assertEqual(track._next_missing(), 7)
        session._coordinate_seek(track, 2, reason='seek')
        self.assertEqual(track._next_missing(), 2)


if __name__ == '__main__':
    unittest.main()
