import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'plugin.video.appi'))

from resources.lib.m3u import parse_m3u  # noqa: E402


class M3UTests(unittest.TestCase):
    def test_movies_preserve_display_title_and_commas(self):
        text = '''#EXTM3U
#EXTINF:-1 tvg-id="tt1234567" tvg-name="tt1234567" tvg-type="movies" group-title="Movies 2025" ,The Good, the Bad and the Test (2025)
https://example.invalid/api/movie/tt1234567
'''
        items = parse_m3u(text)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['kind'], 'movie')
        self.assertEqual(items[0]['display_title'], 'The Good, the Bad and the Test (2025)')
        self.assertEqual(items[0]['title'], 'The Good, the Bad and the Test')
        self.assertEqual(items[0]['year'], 2025)
        self.assertEqual(items[0]['tvg_id'], 'tt1234567')

    def test_tv_metadata_from_display_title(self):
        text = '''#EXTM3U
#EXTINF:-1 tvg-id="tt8740614" tvg-name="tt8740614" tvg-type="tvshows" group-title="The Residence (2025)" ,The Residence (2025) S01 E05
https://example.invalid/api/tvshow/tt8740614/1/5
'''
        item = parse_m3u(text)[0]
        self.assertEqual(item['kind'], 'episode')
        self.assertEqual(item['show_title'], 'The Residence')
        self.assertEqual(item['year'], 2025)
        self.assertEqual(item['season'], 1)
        self.assertEqual(item['episode'], 5)

    def test_tv_season_episode_url_fallback(self):
        text = '''#EXTM3U
#EXTINF:-1 tvg-id="tt1111111" tvg-type="tvshows" group-title="Example Show (2024)" ,Example Show special
https://example.invalid/api/tvshow/tt1111111/2/9
'''
        item = parse_m3u(text)[0]
        self.assertEqual((item['season'], item['episode']), (2, 9))


if __name__ == '__main__':
    unittest.main()
