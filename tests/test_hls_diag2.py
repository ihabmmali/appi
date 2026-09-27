import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / 'plugin.video.appi' / 'resources' / 'lib'


def _load_hls():
    spec = importlib.util.spec_from_file_location('appi_hls_test', LIB / 'hls.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_diagnostics():
    xbmc = types.ModuleType('xbmc')
    xbmc.getInfoLabel = lambda name: ''
    xbmc.getCondVisibility = lambda name: False
    sys.modules['xbmc'] = xbmc

    xbmcaddon = types.ModuleType('xbmcaddon')

    class Addon:
        def getAddonInfo(self, name):
            return '/tmp/appi-test-profile' if name == 'profile' else ('0.7.14' if name == 'version' else '')

        def getSetting(self, name):
            return 'true' if name == 'diagnostics_enabled' else ''

    xbmcaddon.Addon = Addon
    sys.modules['xbmcaddon'] = xbmcaddon

    xbmcvfs = types.ModuleType('xbmcvfs')
    xbmcvfs.translatePath = lambda value: value
    xbmcvfs.exists = lambda value: True
    xbmcvfs.mkdirs = lambda value: True
    xbmcvfs.copy = lambda source, target: True
    sys.modules['xbmcvfs'] = xbmcvfs

    spec = importlib.util.spec_from_file_location('appi_diagnostics_test', LIB / 'diagnostics.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HlsRegressionTests(unittest.TestCase):
    def test_signed_master_query_is_inherited_by_relative_variant(self):
        hls = _load_hls()
        resolved = hls.resolve_variant_url(
            'https://media.example/master.m3u8?token=abc&sig=xyz',
            'video/720.m3u8',
        )
        self.assertEqual(
            resolved,
            'https://media.example/video/720.m3u8?token=abc&sig=xyz',
        )

    def test_child_query_is_not_overwritten(self):
        hls = _load_hls()
        resolved = hls.resolve_variant_url(
            'https://media.example/master.m3u8?token=master',
            '720.m3u8?token=child',
        )
        self.assertEqual(resolved, 'https://media.example/720.m3u8?token=child')

    def test_cross_origin_absolute_variant_does_not_inherit_master_query(self):
        hls = _load_hls()
        resolved = hls.resolve_variant_url(
            'https://media.example/master.m3u8?secret=yes',
            'https://cdn.example/1080.m3u8',
        )
        self.assertEqual(resolved, 'https://cdn.example/1080.m3u8')

    def test_kodi_url_options_survive_variant_resolution(self):
        hls = _load_hls()
        resolved = hls.resolve_variant_url(
            'https://media.example/master.m3u8?token=abc|User-Agent=Kodi&Referer=https%3A%2F%2Fexample',
            '720.m3u8',
        )
        self.assertEqual(
            resolved,
            'https://media.example/720.m3u8?token=abc|User-Agent=Kodi&Referer=https%3A%2F%2Fexample',
        )

    def test_parser_keeps_stream_inf_metadata_with_same_variant(self):
        hls = _load_hls()
        variants = hls.parse_master(
            '#EXTM3U\n'
            '#EXT-X-STREAM-INF:BANDWIDTH=6500000,AVERAGE-BANDWIDTH=5800000,RESOLUTION=1920x1080,CODECS="avc1.640028,mp4a.40.2"\n'
            '1080/index.m3u8\n'
            '#EXT-X-STREAM-INF:BANDWIDTH=3200000,RESOLUTION=1280x720,CODECS="avc1.4d401f,mp4a.40.2"\n'
            '720/index.m3u8\n',
            'https://media.example/master.m3u8?token=abc',
        )
        self.assertEqual(len(variants), 2)
        self.assertEqual(variants[0]['height'], 1080)
        self.assertEqual(variants[0]['average_bandwidth'], 5800000)
        self.assertEqual(variants[0]['peak_bandwidth'], 6500000)
        self.assertEqual(variants[0]['url'], 'https://media.example/1080/index.m3u8?token=abc')
        self.assertIn('avg 5.8 / peak 6.5 Mbit/s', hls.variant_label(variants[0]))
        self.assertIn('avc1.640028,mp4a.40.2', hls.variant_label(variants[0]))


class DiagnosticAnalysisTests(unittest.TestCase):
    def test_stall_with_empty_cache_is_classified_as_suggestive(self):
        diagnostics = _load_diagnostics()
        payload = {
            'events': [
                {
                    'at': 100.0,
                    'event': 'sample',
                    'fields': {
                        'cache_json': '{"level_percent":{"raw":"2%","numeric":2.0}}'
                    },
                },
                {'at': 105.0, 'event': 'stall_start', 'fields': {}},
            ]
        }
        result = diagnostics._analysis(payload)
        categories = {item['category']: item['support'] for item in result['classifications']}
        self.assertEqual(result['stall_count'], 1)
        self.assertEqual(categories.get('shallow_or_empty_read_ahead'), 'suggestive')
        self.assertEqual(categories.get('server_or_segment_delay'), 'insufficient_evidence')

    def test_buffered_proxy_declares_direct_segment_and_buffer_observability(self):
        diagnostics = _load_diagnostics()
        diagnostics.prepare_playback(
            'movies', 'm:test', 'https://provider.example/master.m3u8?token=secret',
            'hls', 'appi-buffered-lookahead',
            {
                'hls_mode': 3,
                'buffered_proxy': True,
                'buffer_target_seconds': 30,
                'buffer_startup_seconds': 18,
            },
        )
        payload = diagnostics._read(diagnostics.ACTIVE)
        self.assertTrue(payload['availability']['per_segment_http_timing'])
        self.assertTrue(payload['availability']['playlist_refresh_history'])
        self.assertTrue(payload['availability']['proxy_buffer_depth'])
        self.assertFalse(payload['availability']['raw_authenticated_url'])
        self.assertEqual(payload['options']['buffer_target_seconds'], 30)
        self.assertNotIn('secret', str(payload))

    def test_representation_changes_are_reported_without_claiming_segment_timing(self):
        diagnostics = _load_diagnostics()
        payload = {
            'events': [
                {'at': 1.0, 'event': 'representation_change', 'fields': {}},
                {'at': 2.0, 'event': 'representation_change', 'fields': {}},
            ]
        }
        result = diagnostics._analysis(payload)
        self.assertEqual(result['representation_change_count'], 2)
        self.assertTrue(any(
            item['category'] == 'abr_transition_behavior' and item['support'] == 'observed'
            for item in result['classifications']
        ))


if __name__ == '__main__':
    unittest.main()
