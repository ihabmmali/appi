import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'plugin.video.appi'))

from resources.lib.m3u import parse_m3u  # noqa: E402


class M3UTests(unittest.TestCase):
    def test_movies_preserve_display_title_and_commas(self):
        text = '''#EXTM3U
#EXTINF:-1 tvg-id="tt9900001" tvg-name="tt9900001" tvg-type="movies" group-title="Synthetic Movies 2042" ,Azure, Copper and the Test (2042)
https://media.invalid/api/movie/tt9900001
'''
        items = parse_m3u(text)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['kind'], 'movie')
        self.assertEqual(items[0]['display_title'], 'Azure, Copper and the Test (2042)')
        self.assertEqual(items[0]['title'], 'Azure, Copper and the Test')
        self.assertEqual(items[0]['year'], 2042)
        self.assertEqual(items[0]['tvg_id'], 'tt9900001')

    def test_tv_metadata_from_display_title(self):
        text = '''#EXTM3U
#EXTINF:-1 tvg-id="tt9900002" tvg-name="tt9900002" tvg-type="tvshows" group-title="Synthetic Series (2042)" ,Synthetic Series (2042) S01 E05
https://media.invalid/api/tvshow/tt9900002/1/5
'''
        item = parse_m3u(text)[0]
        self.assertEqual(item['kind'], 'episode')
        self.assertEqual(item['show_title'], 'Synthetic Series')
        self.assertEqual(item['year'], 2042)
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
