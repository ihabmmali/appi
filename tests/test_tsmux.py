import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugin.video.appi'


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg tools unavailable')
class TransportStreamMuxTests(unittest.TestCase):
    def test_separate_hls_renditions_become_one_decodable_file(self):
        with tempfile.TemporaryDirectory(prefix='appi-tsmux-') as value:
            folder = Path(value)
            subprocess.run([
                'ffmpeg', '-v', 'error', '-f', 'lavfi',
                '-i', 'testsrc2=size=160x90:rate=25', '-t', '2',
                '-c:v', 'mpeg2video', '-an', '-f', 'hls', '-hls_time', '0.7',
                '-hls_segment_filename', str(folder / 'video-%03d.ts'),
                str(folder / 'video.m3u8'),
            ], check=True)
            subprocess.run([
                'ffmpeg', '-v', 'error', '-f', 'lavfi',
                '-i', 'sine=frequency=1000:sample_rate=48000', '-t', '2',
                '-c:a', 'aac', '-vn', '-f', 'hls', '-hls_time', '0.55',
                '-hls_segment_filename', str(folder / 'audio-%03d.ts'),
                str(folder / 'audio.m3u8'),
            ], check=True)
            code = r'''
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from resources.lib import tsmux
folder = Path(sys.argv[2])
def segments(name):
    return [folder / line.strip() for line in (folder / name).read_text().splitlines()
            if line.strip() and not line.startswith('#')]
tsmux.mux_segments(segments('video.m3u8'), segments('audio.m3u8'), folder / 'combined.ts')
'''
            subprocess.run(
                [sys.executable, '-c', code, str(PLUGIN), str(folder)], check=True,
            )
            probe = subprocess.run([
                'ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type',
                '-of', 'json', str(folder / 'combined.ts'),
            ], check=True, capture_output=True, text=True)
            types = {stream['codec_type'] for stream in json.loads(probe.stdout)['streams']}
            self.assertEqual(types, {'video', 'audio'})
            subprocess.run([
                'ffmpeg', '-v', 'error', '-i', str(folder / 'combined.ts'),
                '-f', 'null', '-',
            ], check=True)


if __name__ == '__main__':
    unittest.main()
