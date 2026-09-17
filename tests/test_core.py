import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugin.video.appi'
sys.path.insert(0, str(PLUGIN))

from resources.lib.catalog import build_tv_groups, paginate, sort_movies, sort_shows  # noqa: E402
from resources.lib.http import classify_stream  # noqa: E402
from resources.lib.m3u import parse_m3u  # noqa: E402


class CoreTests(unittest.TestCase):
    def test_movie_parser_preserves_year_in_display_label(self):
        text = '''#EXTM3U\n#EXTINF:-1 tvg-id="tt1234567" tvg-name="tt1234567" tvg-type="movies" group-title="Movies 2025" ,The Good, the Bad (2025)\nhttps://example.invalid/movie/tt1234567\n'''
        item = parse_m3u(text)[0]
        self.assertEqual(item['display_title'], 'The Good, the Bad (2025)')
        self.assertEqual(item['title'], 'The Good, the Bad')
        self.assertEqual(item['year'], 2025)

    def test_tv_group_index(self):
        text = '''#EXTM3U\n#EXTINF:-1 tvg-id="tt8740614" tvg-type="tvshows" group-title="The Residence (2025)" ,The Residence (2025) S01 E01\nhttps://example.invalid/tvshow/tt8740614/1/1\n#EXTINF:-1 tvg-id="tt8740614" tvg-type="tvshows" group-title="The Residence (2025)" ,The Residence (2025) S02 E03\nhttps://example.invalid/tvshow/tt8740614/2/3\n'''
        episodes = parse_m3u(text)
        summaries, groups = build_tv_groups(episodes)
        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0]['seasons'], [1, 2])
        self.assertEqual(summaries[0]['episode_count'], 2)
        self.assertEqual(len(groups[summaries[0]['show_key']]), 2)

    def test_sort_modes(self):
        movies = [
            {'title': 'Beta', 'year': 2020},
            {'title': 'Alpha', 'year': 2025},
            {'title': 'Gamma', 'year': 2022},
        ]
        self.assertEqual([x['title'] for x in sort_movies(movies, 0)], ['Alpha', 'Beta', 'Gamma'])
        self.assertEqual([x['title'] for x in sort_movies(movies, 1)], ['Gamma', 'Beta', 'Alpha'])
        self.assertEqual([x['title'] for x in sort_movies(movies, 2)], ['Alpha', 'Gamma', 'Beta'])
        self.assertEqual([x['title'] for x in sort_movies(movies, 3)], ['Beta', 'Gamma', 'Alpha'])
        self.assertEqual([x['title'] for x in sort_movies(movies, 4)], ['Beta', 'Alpha', 'Gamma'])
        self.assertEqual([x['title'] for x in sort_movies(movies, 5)], ['Gamma', 'Alpha', 'Beta'])
        shows = [{'show_title': x['title'], 'year': x['year']} for x in movies]
        self.assertEqual([x['show_title'] for x in sort_shows(shows, 2)], ['Alpha', 'Gamma', 'Beta'])
        self.assertEqual([x['show_title'] for x in sort_shows(shows, 4)], ['Beta', 'Alpha', 'Gamma'])
        self.assertEqual([x['show_title'] for x in sort_shows(shows, 5)], ['Gamma', 'Alpha', 'Beta'])

    def test_fixed_size_pagination(self):
        items = list(range(225))
        page, number, pages, total = paginate(items, 2, 100)
        self.assertEqual(number, 2)
        self.assertEqual(pages, 3)
        self.assertEqual(total, 225)
        self.assertEqual(page, list(range(100, 200)))
        page, number, pages, total = paginate(items, 99, 100)
        self.assertEqual(number, 3)
        self.assertEqual(page, list(range(200, 225)))

    def test_stream_classifier(self):
        self.assertEqual(classify_stream('https://x/master', 'application/vnd.apple.mpegurl', b'#EXTM3U\n'), 'hls')
        self.assertEqual(classify_stream('https://x/video.mp4', 'application/octet-stream', b'0000ftypisom'), 'mp4')
        self.assertEqual(classify_stream('https://x/video', 'application/octet-stream', b'hello'), 'unknown')


class SubtitleStoreTests(unittest.TestCase):
    def test_new_temp_subtitle_is_copied_on_second_stable_poll(self):
        # Import subtitle_store with temporary Kodi paths.
        temp_root = tempfile.TemporaryDirectory()
        profile = os.path.join(temp_root.name, 'profile')
        kodi_temp = os.path.join(temp_root.name, 'temp')
        os.makedirs(profile)
        os.makedirs(kodi_temp)

        fake_addon = types.ModuleType('xbmcaddon')
        class Addon:
            def getAddonInfo(self, name):
                return profile if name == 'profile' else ''
        fake_addon.Addon = Addon

        fake_vfs = types.ModuleType('xbmcvfs')
        fake_vfs.translatePath = lambda value: kodi_temp if value == 'special://temp/' else value
        sys.modules['xbmcaddon'] = fake_addon
        sys.modules['xbmcvfs'] = fake_vfs
        sys.modules.pop('resources.lib.subtitle_store', None)
        from resources.lib import subtitle_store

        subtitle_store.prepare_session('movies', 'm:tt1')
        source = os.path.join(kodi_temp, 'downloaded.en.srt')
        with open(source, 'w', encoding='utf-8') as handle:
            handle.write('1\n00:00:00,000 --> 00:00:01,000\nHello\n')
        self.assertEqual(subtitle_store.capture_temp_changes(), [])
        copied = subtitle_store.capture_temp_changes()
        self.assertEqual(len(copied), 1)
        self.assertTrue(os.path.isfile(copied[0]))
        self.assertEqual(subtitle_store.last_saved_subtitle('movies', 'm:tt1'), copied[0])
        temp_root.cleanup()


if __name__ == '__main__':
    unittest.main()
