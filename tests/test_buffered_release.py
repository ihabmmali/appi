import ast
import hashlib
import importlib.util
import os
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.request import Request, urlopen

from test_buffered_hls import _load_module, _install_fake_fetch

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / 'plugin.video.appi/resources/lib'


def until(predicate, timeout=3):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(.01)
    return False


class BufferedReleaseTests(unittest.TestCase):
    def setUp(self):
        self.m = _load_module()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.payloads = {'/media.m3u8': self.media(40)}
        self.payloads.update({'/s%d.ts' % i: b'x' * 1024 for i in range(40)})
        _install_fake_fetch(self.m, self.payloads)

    def media(self, count):
        return ('#EXTM3U\n#EXT-X-TARGETDURATION:6\n' + ''.join(
            '#EXTINF:6,\ns%d.ts\n' % i for i in range(count)) + '#EXT-X-ENDLIST\n').encode()

    def session(self, **kwargs):
        session = self.m.BufferedHlsSession('https://provider/media.m3u8?token=SECRET',
            root=os.path.join(self.temp.name, str(time.monotonic_ns())), **kwargs)
        session.start()
        self.addCleanup(session.stop)
        return session

    def test_byte_capacity_changes_effective_lookahead_beyond_thirty_seconds(self):
        self.payloads.update({'/s%d.ts' % i: b'x' * 1024 * 1024 for i in range(40)})
        counts = []
        for mb in (32, 64):
            session = self.session(buffer_mb=mb)
            session.prepare()
            self.assertTrue(session.ready)
            track = next(iter(session.tracks.values()))
            self.assertTrue(until(lambda: track._next_missing() is None))
            counts.append(track.ahead_bytes())
            self.assertGreater(track._ahead()[0], 30)
            self.assertLessEqual(session.disk_bytes(), mb * 1048576)
        self.assertGreater(counts[1], counts[0])

    def test_vod_playlist_repeat_reuses_resources_and_never_rewinds_cursor(self):
        session = self.session()
        session.prepare()
        track = next(iter(session.tracks.values()))
        track.serve(10)
        count = len(session.resources)
        session.serve(session.master.id)
        self.assertEqual(len(session.resources), count)
        self.assertEqual(track.last_served, 10)

    def test_repeated_forward_backward_uncached_seeks_recenter(self):
        session = self.session()
        session.prepare()
        track = next(iter(session.tracks.values()))
        for index in (0, 24, 3, 35, 1):
            self.assertTrue(os.path.isfile(track.serve(index)))
            self.assertEqual(track.last_served, index)
        self.assertTrue(any(n == 'buffer_seek_recenter' for n, _ in session.drain_events()))

    def test_cached_segment_returns_without_waiting_for_recovery_reserve(self):
        session = self.session()
        session.prepare()
        track = next(iter(session.tracks.values()))
        self.assertTrue(until(lambda: track._cached(0)))
        session._wait_reservoir = lambda *a: self.fail('sequential cached segment must not block')
        self.assertTrue(track.serve(0))

    def test_depleted_sequential_segment_is_released_before_reserve_rebuild(self):
        session = self.session(buffer_mb=32)
        session.prepare()
        track = next(iter(session.tracks.values()))
        track.stop()
        track.last_served = 0
        track.last_requested = 0
        target = track.segments[1].resource
        if target.path and os.path.exists(target.path):
            os.remove(target.path)
        target.path = ''
        session._wait_reservoir = lambda *a: self.fail(
            'normal exact-segment delivery must not wait for reserve rebuild'
        )
        self.assertTrue(os.path.isfile(track.serve(1)))
        names = [name for name, _ in session.drain_events()]
        self.assertIn('buffer_required_segment_ready', names)
        self.assertIn('buffer_recovery_media_released', names)

    def test_missing_seek_fails_within_bound_without_fallback_network_wait(self):
        session = self.session()
        session.prepare()
        track = next(iter(session.tracks.values()))
        track.stop()
        resource = track.segments[30].resource
        if resource.path and os.path.exists(resource.path):
            os.remove(resource.path)
        session._wait_reservoir = lambda *args: False
        started = time.monotonic()
        with self.assertRaises(TimeoutError):
            track.serve(30)
        self.assertLess(time.monotonic() - started, .2)

    def test_highest_quality_and_prompt_preserve_master_audio_and_exact_variant(self):
        master = ('#EXTM3U\n#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="a",URI="audio.m3u8"\n'
            '#EXT-X-STREAM-INF:BANDWIDTH=1000000,RESOLUTION=640x360,AUDIO="a"\nlow.m3u8\n'
            '#EXT-X-STREAM-INF:BANDWIDTH=8000000,RESOLUTION=1920x1080,AUDIO="a"\nhigh.m3u8\n')
        self.payloads.update({
            '/media.m3u8': master.encode(),
            '/low.m3u8': self.media(4),
            '/high.m3u8': self.media(4),
            # 0.7.19 intentionally opens the selected variant's associated
            # audio rendition during preparation, so the fixture must model
            # the audio playlist that the master advertises.
            '/audio.m3u8': self.media(4),
        })
        for quality, expected in [('highest','high'), ('prompt','low')]:
            session = self.session(quality=quality)
            worker = threading.Thread(target=session.prepare)
            worker.start()
            if quality == 'prompt':
                self.assertTrue(until(lambda: bool(session.choices)))
                self.assertIn('1920x1080', session.choices[1])
                self.assertIn('8.00 Mbit/s', session.choices[1])
                session.choice = 0
                session.choice_event.set()
            worker.join(3)
            self.assertFalse(worker.is_alive())
            self.assertTrue(session.ready, session.error)
            reps = [r for r in session.resources.values() if r.metadata.get('representation')]
            self.assertEqual(len(reps), 1)
            self.assertIn('/'+expected+'.m3u8?token=SECRET', reps[0].upstream_url)
            body, _ = session.serve(session.master.id)
            self.assertIn(b'#EXT-X-MEDIA', body)
            self.assertNotIn(b'SECRET', body)

    def test_unknown_bandwidth_tie_uses_first_without_inventing_bitrate(self):
        session = self.session()
        text = '#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=bad\none.m3u8\n#EXT-X-STREAM-INF:RESOLUTION=1x1\ntwo.m3u8\n'
        selected = session._select_variant(text)
        self.assertIn('one.m3u8', selected)
        self.assertNotIn('two.m3u8', selected)

    def test_single_rendition_prompt_does_not_wait_for_choice(self):
        session = self.session(quality='prompt')
        session.prepare()
        self.assertTrue(session.ready)
        self.assertFalse(session.choices)

    def test_http_byte_range_is_honored(self):
        session = self.session()
        session.prepare()
        track = next(iter(session.tracks.values()))
        url = session._local_url(track.segments[0].resource.id)
        with urlopen(Request(url, headers={'Range':'bytes=4-9'}), timeout=3) as response:
            self.assertEqual(response.status, 206)
            self.assertEqual(response.headers['Content-Range'], 'bytes 4-9/1024')
            self.assertEqual(len(response.read()), 6)

    def test_manager_retries_navigation_independence_and_stale_stop(self):
        manager = self.m.BufferedHlsManager(root=self.temp.name)
        self.addCleanup(manager.shutdown)
        def submit(number, source='https://provider/media.m3u8'):
            rid = '%024x' % number
            self.m._json_write(os.path.join(manager.control, 'request-'+rid+'.json'),
                {'id':rid,'source_url':source,'created_at':time.time()})
            manager.poll()
            return manager.active
        # The same invalid stream fails the same way across attempts. No folder state.
        for number in (1,2):
            session = submit(number, 'https://provider/missing.m3u8')
            if session is not None:
                self.assertTrue(until(lambda: bool(session.error)))
            manager.poll()
            response=self.m._json_read(os.path.join(manager.control, 'response-%024x.json' % number))
            self.assertTrue(response['error'])
            self.assertIsNone(manager.active)
            if session is not None:
                self.assertFalse(os.path.exists(session.root))
        old = submit(3)
        self.assertTrue(until(lambda: old.ready))
        token = manager.playback_started(old.local_url)
        new = submit(4)
        manager.playback_finished(token, 'stopped')
        self.assertIs(manager.active, new)
        self.assertFalse(os.path.exists(old.root))
        self.assertTrue(until(lambda: new.ready))
        newtoken = manager.playback_started(new.local_url)
        manager.playback_finished(newtoken, 'stopped')
        self.assertIsNone(manager.active)
        self.assertFalse(os.path.exists(new.root))

    def test_cancel_while_preparing_then_next_session_succeeds(self):
        gate = threading.Event()
        original = self.m._fetch
        def slow(url, **kw):
            gate.wait(2)
            return original(url, **kw)
        self.m._fetch = slow
        session = self.session()
        thread = threading.Thread(target=session.prepare)
        thread.start()
        session.stop('cancelled')
        gate.set()
        thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertFalse(session.ready)
        self.assertFalse(session.tracks)
        self.assertFalse(os.path.exists(session.root))
        following = self.session()
        following.prepare()
        self.assertTrue(following.ready)

    def test_delayed_startup_is_not_ready_until_reserve_available(self):
        gate = threading.Event()
        original = self.m._fetch_to_path
        def delayed(*args, **kwargs):
            gate.wait(2)
            return original(*args, **kwargs)
        self.m._fetch_to_path = delayed
        session = self.session()
        worker = threading.Thread(target=session.prepare)
        worker.start()
        self.assertTrue(until(lambda: bool(session.tracks)))
        self.assertFalse(session.ready)
        status = session.status()
        self.assertIn('Filling buffer', status['message'])
        self.assertTrue('KB' in status['message'] or 'MB' in status['message'])
        self.assertGreater(status['buffer_target_bytes'], 0)
        gate.set()
        worker.join(3)
        self.assertTrue(session.ready)

    def test_deep_reservoir_uses_shared_capacity_not_equal_track_slices(self):
        master = ('#EXTM3U\n'
            '#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="a",DEFAULT=YES,URI="audio.m3u8"\n'
            '#EXT-X-STREAM-INF:BANDWIDTH=6000000,AUDIO="a"\nvideo.m3u8\n')
        media = lambda prefix, size: ('#EXTM3U\n#EXT-X-TARGETDURATION:2\n' + ''.join(
            '#EXTINF:2,\n%s%d.bin\n' % (prefix, i) for i in range(80)) + '#EXT-X-ENDLIST\n').encode()
        self.payloads.update({
            '/media.m3u8': master.encode(),
            '/video.m3u8': media('v', 0),
            '/audio.m3u8': media('a', 0),
        })
        for i in range(80):
            self.payloads['/v%d.bin' % i] = b'v' * (1024 * 1024)
            self.payloads['/a%d.bin' % i] = b'a' * (32 * 1024)
        _install_fake_fetch(self.m, self.payloads)
        session = self.session(buffer_mb=64)
        session.prepare()
        self.assertTrue(session.ready, session.error)
        self.assertGreaterEqual(session.status()['cached_ahead_bytes'], session.startup_target_bytes)
        self.assertTrue(until(lambda: session.status()['cached_ahead_bytes'] >= session.high_water_bytes, 5))
        tracks = list(session.tracks.values())
        large = max(track.ahead_bytes() for track in tracks)
        small = min(track.ahead_bytes() for track in tracks)
        self.assertGreater(large, small * 8)
        self.assertLessEqual(session.disk_bytes(), session.max_bytes)

    def test_seek_starts_new_epoch_and_late_old_download_is_ignored(self):
        session = self.session(buffer_mb=32)
        session.prepare()
        track = next(iter(session.tracks.values()))
        old_epoch = session.epoch
        resource = track.segments[20].resource
        # The tiny short-VOD fixture is fully cached by preparation. Stop its
        # worker and remove one known segment so this test owns a real in-flight
        # old-epoch transfer deterministically.
        track.stop()
        if resource.path and os.path.exists(resource.path):
            os.remove(resource.path)
        resource.path = ''
        original = self.m._fetch_to_path
        gate = threading.Event()
        started = threading.Event()

        def delayed(url, path, **kwargs):
            if resource.upstream_url.split('|', 1)[0] in url:
                started.set()
                gate.wait(2)
            return original(url, path, **kwargs)

        self.m._fetch_to_path = delayed
        holder = {}
        def old_download():
            try:
                holder['path'] = session._ensure_binary(
                    resource, segment=track.segments[20], track=track, epoch=old_epoch
                )
            except Exception as exc:
                holder['error'] = exc
        worker = threading.Thread(target=old_download)
        worker.start()
        self.assertTrue(started.wait(1))
        new_epoch = session._coordinate_seek(track, 30, reason='seek')
        self.assertGreater(new_epoch, old_epoch)
        gate.set()
        worker.join(3)
        self.assertFalse(worker.is_alive())
        self.assertIn('error', holder)
        self.assertFalse(resource.path and os.path.isfile(resource.path))
        status = session.status()
        self.assertEqual(status['epoch_id'], new_epoch)
        self.assertGreaterEqual(status['stale_jobs_cancelled_or_ignored'], 1)

    def test_status_reports_numeric_playable_bytes_and_watermarks(self):
        session = self.session(buffer_mb=32)
        worker = threading.Thread(target=session.prepare)
        worker.start()
        self.assertTrue(until(lambda: bool(session.tracks)))
        self.assertTrue(until(lambda: session.status()['cached_ahead_bytes'] > 0))
        status = session.status()
        self.assertGreater(status['buffer_target_bytes'], 0)
        self.assertGreater(status['high_water_bytes'], status['low_water_bytes'])
        self.assertGreater(status['low_water_bytes'], status['critical_water_bytes'])
        self.assertTrue('KB' in status['message'] or 'MB' in status['message'])
        worker.join(5)
        self.assertFalse(worker.is_alive())
        self.assertTrue(session.ready, session.error)


    def test_refill_hysteresis_runs_to_high_water_then_restarts_at_low_water(self):
        session = self.session(buffer_mb=32)
        session._startup_complete = True
        session._epoch_preparing = False
        session._all_required_cached = lambda: False
        state = {'bytes': session.high_water_bytes + 1}
        session._playable_reserve = lambda: (state['bytes'], 30.0, 5)
        session._refill_active = True
        self.assertFalse(session._update_refill_state())
        state['bytes'] = (session.high_water_bytes + session.low_water_bytes) // 2
        self.assertFalse(session._update_refill_state())
        state['bytes'] = session.low_water_bytes - 1
        self.assertTrue(session._update_refill_state())

    def test_cached_reservoir_masks_provider_stall_until_uncached_edge(self):
        session = self.session(buffer_mb=32)
        session.prepare()
        track = next(iter(session.tracks.values()))
        track.stop()
        # Keep five contiguous local segments and remove the rest.
        for segment in track.segments[5:]:
            if segment.resource.path and os.path.exists(segment.resource.path):
                os.remove(segment.resource.path)
            segment.resource.path = ''
        self.m._fetch_to_path = lambda *a, **k: (_ for _ in ()).throw(
            TimeoutError('simulated provider stall')
        )
        session.retry_attempts = 1
        session.retry_delay = 0
        session._wait_reservoir = lambda *args: False
        for index in range(5):
            self.assertTrue(os.path.isfile(track.serve(index)))
        with self.assertRaises(self.m.RecoveryTimeout):
            track.serve(5)

    def test_prefetch_concurrency_fetches_future_segments_in_parallel_without_duplicates(self):
        original = self.m._fetch_to_path
        lock = threading.Lock()
        gate = threading.Event()
        active = {'count': 0, 'peak': 0}
        calls = []

        def concurrent_fetch(url, path, **kwargs):
            is_segment = '/s' in url
            if is_segment:
                with lock:
                    active['count'] += 1
                    active['peak'] = max(active['peak'], active['count'])
                    calls.append(url)
                    if active['count'] >= 2:
                        gate.set()
                gate.wait(1.0)
            try:
                return original(url, path, **kwargs)
            finally:
                if is_segment:
                    with lock:
                        active['count'] -= 1

        self.m._fetch_to_path = concurrent_fetch
        session = self.session(tuning={'prefetch_concurrency': 2})
        session.prepare()
        self.assertTrue(session.ready, session.error)
        self.assertGreaterEqual(active['peak'], 2)
        self.assertEqual(len(calls), len(set(calls)))
        status = session.status()
        self.assertEqual(status['prefetch_concurrency'], 2)
        self.assertGreaterEqual(status['peak_active_fetch_count'], 2)

    def test_tuning_validation_preserves_defaults_and_rejects_bad_watermark_order(self):
        defaults=self.m.validated_tuning({})
        self.assertEqual(defaults['startup_pct'],50)
        self.assertEqual(defaults['high_water_pct'],80)
        self.assertEqual(defaults['low_water_pct'],60)
        self.assertEqual(defaults['critical_pct'],15)
        bad=self.m.validated_tuning({
            'startup_pct':90,'high_water_pct':70,'low_water_pct':80,'critical_pct':85,
            'recovery_timeout_s':1,'retry_delay_ms':1,
        })
        self.assertEqual(
            [bad[k] for k in ('startup_pct','high_water_pct','low_water_pct','critical_pct')],
            [50,80,60,15],
        )
        self.assertEqual(bad['recovery_timeout_s'],5)
        self.assertEqual(bad['retry_delay_ms'],100)

    def test_transient_depletion_retries_inside_appi_before_terminal_failure(self):
        session=self.session(buffer_mb=32,tuning={
            'recovery_timeout_s':5,'retry_attempts':3,'retry_delay_ms':100,
        })
        session.prepare()
        track=next(iter(session.tracks.values()))
        track.stop()
        index=min(20,len(track.segments)-1)
        track.last_served=index-1
        track.last_requested=index-1
        resource=track.segments[index].resource
        if resource.path and os.path.exists(resource.path):
            os.remove(resource.path)
        resource.path=''
        original=self.m._fetch_to_path
        calls={'count':0}
        def flaky(*args,**kwargs):
            calls['count']+=1
            if calls['count']<2:
                raise TimeoutError('synthetic transient timeout')
            return original(*args,**kwargs)
        self.m._fetch_to_path=flaky
        session._wait_reservoir=lambda *args: True
        self.assertTrue(os.path.isfile(track.serve(index)))
        self.assertGreaterEqual(calls['count'],2)
        names=[name for name,_ in session.drain_events()]
        self.assertIn('buffer_recovery_retry',names)
        self.assertIn('buffer_recovery_media_released',names)

    def test_failure_snapshot_contains_numeric_timeline_and_classification(self):
        session=self.session(buffer_mb=32)
        session.ready=True
        session.started_playback=True
        session._startup_complete=True
        session._epoch_preparing=False
        session._playable_reserve=lambda:(0,0.0,0)
        status=session.status()
        self.assertEqual(status['cached_ahead_bytes'],0)
        classification=session._failure_snapshot('recovery_exhausted','synthetic')
        self.assertIn(classification,{
            'reservoir_exhausted','required_track_starvation','next_segment_hole',
            'recovery_timeout_with_progress','sustained_throughput_deficit','unknown'
        })
        snapshots=[fields for name,fields in session.drain_events()
                   if name=='buffer_failure_snapshot']
        self.assertTrue(snapshots)
        self.assertTrue(snapshots[-1]['timeline'])
        latest=snapshots[-1]['timeline'][-1]
        self.assertIn('playable_bytes',latest)
        self.assertIn('total_cached_bytes',latest)
        self.assertIn('tracks',latest)

    def test_critical_sustained_deficit_is_reported_from_measured_evidence(self):
        session = self.session(buffer_mb=32)
        session.ready = True
        session.started_playback = True
        session._startup_complete = True
        session._epoch_preparing = False
        session._selected_variant_attrs = {'BANDWIDTH': '8000000'}
        session._throughput_samples = [(500000, 1000.0)]  # 4 Mbit/s measured.
        session._playable_reserve = lambda: (
            session.critical_water_bytes - 1, 5.0, 2
        )
        status = session.status()
        self.assertEqual(status['buffer_state'], 'critical')
        self.assertTrue(status['throughput_limited'])
        self.assertIn('Provider 4.00 Mbit/s', status['limitation_message'])
        self.assertIn('selected 8.00 Mbit/s', status['message'])



class ReleaseSettingsTests(unittest.TestCase):
    def load(self, name):
        spec = importlib.util.spec_from_file_location('test_'+name, LIB / (name+'.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_language_choices_migrate_aliases_and_explicit_none(self):
        m = self.load('languages')
        values={'preferred_audio_language':'English','preferred_subtitle_language':'fre'}
        addon=types.SimpleNamespace(getSetting=lambda key: values.get(key,''),
                                    setSetting=lambda key,value: values.update({key:value}))
        m.migrate_preferences(addon)
        self.assertEqual(m.preference(addon,'audio'),'en')
        self.assertEqual(m.preference(addon,'subtitle'),'fr')
        values['preferred_audio_language_choice']='none'
        m.migrate_preferences(addon)
        self.assertEqual(m.preference(addon,'audio'),'')
        self.assertEqual(m.preference(addon,'subtitle'),'fr')
        for name,code in [('Arabic','ar'),('jpn','ja'),('German','de'),('ukr','uk'),('Russian','ru')]:
            self.assertEqual(m.normalize(name),code)
        values={'preferred_audio_language':'gibberish'}
        m.migrate_preferences(addon)
        self.assertEqual(m.preference(addon,'audio'),'')

    def test_language_controls_are_lists_with_canonical_codes(self):
        root=ET.parse(ROOT/'plugin.video.appi/resources/settings.xml').getroot()
        for kind in ('audio','subtitle'):
            setting=root.find('.//setting[@id="preferred_'+kind+'_language_choice"]')
            self.assertEqual(setting.find('control').get('type'),'list')
            options=[e.text or '' for e in setting.findall('constraints/options/option')]
            self.assertIn('none', options)
            self.assertNotIn('', options)
            self.assertIn('en',options)
            self.assertIn('ar',options)
            self.assertGreater(len(options),20)

    def test_overlay_is_purely_presentational_and_disabled_is_silent(self):
        sys.modules.setdefault('xbmcgui',types.ModuleType('xbmcgui'))
        m=self.load('buffered_ui')
        status={'cached_ahead_bytes':3*1048576,'buffer_target_bytes':32*1048576,
                'high_water_bytes':50*1048576,'buffer_capacity_mb':64,
                'buffered_seconds':8.5,'recovering':False,'buffer_state':'filling',
                'epoch_id':1}
        before=dict(status)
        self.assertEqual(m.status_text(status,False,True),'')
        self.assertIn('3.0 MB / 32.0 MB', m.status_text(status,True,True))
        self.assertIn('8.5 s ahead', m.status_text(status,True,True))
        self.assertEqual(status,before)
        status['recovering']=True
        self.assertEqual(m.status_text(status,False,True),'')
        detailed=m.status_text(status,True,True)
        self.assertIn('recovering', detailed)
        self.assertGreaterEqual(detailed.count('\n'), 3)
        self.assertEqual(m.status_text(None,True,True),'')

    def test_overlay_xml_is_bounded_multiline_textbox(self):
        root=ET.parse(
            ROOT/'plugin.video.appi/resources/skins/Default/1080i/AppiBufferOverlay.xml'
        ).getroot()
        control=root.find('.//control[@id="100"]')
        self.assertIsNotNone(control)
        self.assertEqual(control.get('type'),'textbox')
        self.assertLessEqual(int(control.findtext('width')),1180)
        self.assertGreaterEqual(int(control.findtext('height')),120)

    def test_icon_exact_copy_and_manifest_reference(self):
        manifest=ET.parse(ROOT/'plugin.video.appi/addon.xml').getroot()
        icon=manifest.findtext('./extension/assets/icon')
        self.assertEqual(manifest.get('version'),'0.7.23')
        self.assertNotEqual(icon, 'resources/icon.png')
        self.assertEqual((ROOT/'plugin.video.appi'/icon).read_bytes(),
                         (ROOT/'artwork/appi-icon-selected.png').read_bytes())

    def test_about_is_direct_read_only_version_display(self):
        root=ET.parse(ROOT/'plugin.video.appi/resources/settings.xml').getroot()
        category=root.find('.//category[@id="about"]')
        self.assertIsNotNone(category)
        self.assertIsNone(category.find('.//setting[@id="about"]'))
        version=category.find('.//setting[@id="installed_version_display"]')
        self.assertIsNotNone(version)
        self.assertEqual(version.findtext('enable'),'false')
        self.assertEqual(version.find('control').get('type'),'edit')

    def test_advanced_buffer_tuning_defaults_match_0721(self):
        root=ET.parse(ROOT/'plugin.video.appi/resources/settings.xml').getroot()
        expected={
            'buffered_startup_pct':'50','buffered_high_water_pct':'80',
            'buffered_low_water_pct':'60','buffered_critical_pct':'15',
            'buffered_media_timeout_s':'15','buffered_startup_timeout_s':'180',
            'buffered_seek_reserve_s':'12','buffered_min_seek_reserve_mb':'4',
            'buffered_prefetch_lead_s':'24','buffered_prefetch_concurrency':'2',
            'buffered_recovery_timeout_s':'60',
            'buffered_retry_delay_ms':'500','buffered_retry_attempts':'0',
            'buffered_recovery_reserve_s':'6','buffered_pause_retention_min':'0',
        }
        for setting_id, default in expected.items():
            setting=root.find('.//setting[@id="{}"]'.format(setting_id))
            self.assertIsNotNone(setting, setting_id)
            self.assertEqual(setting.findtext('default'), default, setting_id)

class BufferTransferTests(unittest.TestCase):
    def test_actual_http_transfer_auth_truncation_capacity_and_range(self):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        m = _load_module()
        seen=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_GET(self):
                seen.append((self.path, self.headers.get('Referer'), self.headers.get('Range')))
                data=b'abcdefghij'
                self.send_response(206 if self.path.startswith('/range') else 200)
                self.send_header('Content-Length',str(20 if self.path.startswith('/short') else len(data)))
                self.end_headers()
                self.wfile.write(data)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        with tempfile.TemporaryDirectory() as root:
            path=os.path.join(root,'segment')
            base='http://127.0.0.1:%d'%server.server_port
            m._fetch_to_path(base+'/ok?token=signed|Referer=https%3A%2F%2Fexample',path,max_bytes=20)
            self.assertEqual(Path(path).read_bytes(),b'abcdefghij')
            self.assertEqual(seen[-1][:2],('/ok?token=signed','https://example'))
            os.remove(path)
            for suffix,options in [('/short',{}),('/ok',{'max_bytes':4}),('/ok',{'byte_range':'0-9'})]:
                with self.assertRaises(RuntimeError):
                    m._fetch_to_path(base+suffix,path,**options)
                self.assertFalse(os.path.exists(path+'.part'))
                self.assertFalse(os.path.exists(path))
            m._fetch_to_path(base+'/range',path,byte_range='0-9')
            self.assertEqual(seen[-1][2],'bytes=0-9')

    def test_control_client_cancel_timeout_and_fresh_attempt(self):
        m=_load_module()
        import shutil
        self.addCleanup(lambda:shutil.rmtree(m._test_root,ignore_errors=True))
        root=m._root_path()
        manager=m.BufferedHlsManager(root=root)
        self.addCleanup(manager.shutdown)
        payloads={'/media.m3u8':b'#EXTM3U\n#EXTINF:6,\ns.ts\n#EXT-X-ENDLIST\n','/s.ts':b'media'}
        _install_fake_fetch(m,payloads)
        state={'cancel':True,'closed':0}
        gui=types.ModuleType('xbmcgui')
        class Progress:
            def create(self,*a):pass
            def update(self,*a):pass
            def close(self):state['closed']+=1
            def iscanceled(self):return state['cancel']
        gui.DialogProgress=Progress
        xbmc=types.ModuleType('xbmc')
        class Monitor:
            def abortRequested(self):return False
            def waitForAbort(self,seconds):
                manager.poll()
                time.sleep(.01)
        xbmc.Monitor=Monitor
        from unittest.mock import patch
        with patch.dict(sys.modules,{'xbmc':xbmc,'xbmcgui':gui}):
            with self.assertRaises(m.PlaybackCancelled):
                m.request_playback('https://provider/media.m3u8')
            manager.poll()
            self.assertIsNone(manager.active)
            state['cancel']=False
            url=m.request_playback('https://provider/media.m3u8',timeout=3)
            self.assertEqual(url,manager.active.local_url)
            self.assertTrue(manager.active.ready)
            manager.stop_active()
            Monitor.waitForAbort=lambda self,seconds:time.sleep(.01)
            with self.assertRaisesRegex(RuntimeError,'timed out'):
                m.request_playback('https://provider/media.m3u8',timeout=.1)
            manager.poll()
            self.assertIsNone(manager.active)
        self.assertEqual(state['closed'],3)


    def test_media_transfer_timeout_is_inactivity_not_total_wall_clock(self):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        m = _load_module()
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                payload = b'abcdefgh'
                self.send_response(200)
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                for value in payload:
                    self.wfile.write(bytes([value]))
                    self.wfile.flush()
                    time.sleep(0.05)
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, 'slow-progress.bin')
            started = time.monotonic()
            result = m._fetch_to_path(
                'http://127.0.0.1:%d/media' % server.server_port,
                path,
                timeout=0.15,
                max_bytes=1024,
            )
            elapsed = time.monotonic() - started
            self.assertGreater(elapsed, 0.15)
            self.assertEqual(Path(path).read_bytes(), b'abcdefgh')
            self.assertEqual(result.byte_count, 8)


class BufferedDecoderTests(unittest.TestCase):
    @unittest.skipUnless(__import__('shutil').which('ffmpeg'), 'ffmpeg is required for real decoder integration')
    def test_real_ts_and_fmp4_decode_and_seek_through_proxy(self):
        import functools
        from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
        m=_load_module()
        import shutil
        self.addCleanup(lambda:shutil.rmtree(m._test_root,ignore_errors=True))
        class Quiet(SimpleHTTPRequestHandler):
            def log_message(self,*args):pass
        for kind in ('mpegts','fmp4'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as root:
                media=Path(root)/'media.m3u8'
                result=subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=size=160x90:rate=24',
                    '-f','lavfi','-i','sine=frequency=800:sample_rate=48000','-t','18',
                    '-c:v','libx264','-preset','ultrafast','-g','48','-sc_threshold','0',
                    '-c:a','aac','-f','hls','-hls_time','2','-hls_list_size','0',
                    '-hls_segment_type',kind,str(media)],capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stderr)
                server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=root))
                threading.Thread(target=server.serve_forever,daemon=True).start()
                session=m.BufferedHlsSession('http://127.0.0.1:%d/media.m3u8'%server.server_port,
                    root=os.path.join(root,'proxy'))
                try:
                    session.start();session.prepare()
                    self.assertTrue(session.ready,session.error)
                    for position in (0,12,2):
                        result=subprocess.run(['ffmpeg','-v','error','-ss',str(position),
                            '-i',session.local_url,'-t','2','-f','null','-'],
                            capture_output=True,text=True,timeout=15)
                        self.assertEqual(result.returncode,0,result.stderr)
                        self.assertFalse(session.error,session.error)
                finally:
                    session.stop();server.shutdown();server.server_close()
