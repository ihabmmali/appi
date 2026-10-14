"""0.7.26 HLS-28 WebVTT compatibility checks; no target-device claim."""
import os
import tempfile
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen

from test_buffered_hls import _install_fake_fetch, _load_module


class BufferedSubtitleSidecarTests(unittest.TestCase):
    def setUp(self):
        self.m = _load_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _session(self, missing=False):
        master = (
            '#EXTM3U\n'
            '#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="unused",NAME="German",'
            'LANGUAGE="de",URI="de.m3u8"\n'
            '#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="English",'
            'LANGUAGE="en",DEFAULT=YES,AUTOSELECT=YES,URI="en.m3u8"\n'
            '#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="French",'
            'LANGUAGE="fr",DEFAULT=NO,FORCED=NO,URI="fr.m3u8"\n'
            '#EXT-X-STREAM-INF:BANDWIDTH=2000000,SUBTITLES="subs"\nvideo.m3u8\n'
            '#EXT-X-STREAM-INF:BANDWIDTH=1000000,SUBTITLES="unused"\nlow.m3u8\n'
        )
        video = '#EXTM3U\n#EXTINF:6,\na.ts\n#EXTINF:6,\nb.ts\n#EXT-X-ENDLIST\n'
        en = '#EXTM3U\n#EXTINF:6,\nen0.vtt\n#EXTINF:6,\nen1.vtt\n#EXT-X-ENDLIST\n'
        fr = '#EXTM3U\n#EXTINF:6,\nfr0.vtt\n#EXT-X-ENDLIST\n'
        data = {
            '/master.m3u8': master.encode(), '/video.m3u8': video.encode(),
            '/a.ts': b'video' * 200, '/b.ts': b'video' * 200,
            '/en.m3u8': en.encode(), '/fr.m3u8': fr.encode(),
            '/en0.vtt': b'WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nOne\n',
            '/en1.vtt': b'WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nTwo\n',
            '/fr0.vtt': b'WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nBonjour\n',
        }
        if missing:
            data.pop('/en0.vtt')
        _install_fake_fetch(self.m, data)
        session = self.m.BufferedHlsSession(
            'https://provider/master.m3u8?secret=hidden',
            root=os.path.join(self.tmp.name, 'buffer'), buffer_mb=32)
        session.start()
        self.addCleanup(session.stop)
        session.prepare()
        self.assertTrue(session.ready, session.error)
        return session

    def test_selected_variant_only_tracks_lazily_exposed_and_combined(self):
        session = self._session()
        self.assertEqual(len(session.subtitle_urls), 2)
        self.assertIn('.en.vtt', session.subtitle_urls[0])
        self.assertIn('.fr.vtt', session.subtitle_urls[1])
        self.assertNotIn('.de.vtt', ' '.join(session.subtitle_urls))
        before = len(session._required_startup_tracks())
        epoch = session.epoch
        self.assertFalse(any(r.kind == 'subtitle-segment'
                             for r in session.resources.values()))
        body, _ = session.serve(session.master.id)
        self.assertIn(b'SUBTITLES="subs"', body)
        self.assertIn(b'FORCED=NO', body)
        self.assertEqual(len(session._required_startup_tracks()), before)
        self.assertEqual(session.epoch, epoch)

        with urlopen(session.subtitle_urls[0], timeout=10) as response:
            data = response.read().decode()
            self.assertEqual(response.headers.get_content_type(), 'text/vtt')
        self.assertIn('00:00:01.000 --> 00:00:02.000', data)
        self.assertIn('00:00:07.000 --> 00:00:08.000', data)
        self.assertIn('One', data)
        self.assertIn('Two', data)
        with urlopen(session.subtitle_urls[1], timeout=10) as response:
            self.assertIn(b'Bonjour', response.read())
        self.assertEqual(len(session._required_startup_tracks()), before)
        self.assertEqual(session.epoch, epoch)
        self.assertFalse(session.error)

    def test_unavailable_subtitle_never_fails_active_av_session(self):
        session = self._session(missing=True)
        epoch = session.epoch
        with self.assertRaises(HTTPError) as exception:
            urlopen(session.subtitle_urls[0], timeout=10)
        self.assertEqual(exception.exception.code, 404)
        self.assertEqual(session.error, '')
        self.assertTrue(session.ready)
        self.assertEqual(session.epoch, epoch)
        self.assertEqual(len(session._required_startup_tracks()), 1)

    def test_no_subtitle_group_has_no_external_paths(self):
        session = self._session()
        self.assertEqual(session._selected_variant_attrs.get('SUBTITLES'), 'subs')
        status = session.status()
        self.assertEqual(list(status['subtitle_urls']), session.subtitle_urls)


if __name__ == '__main__':
    unittest.main()
