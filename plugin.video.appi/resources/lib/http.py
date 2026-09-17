from urllib.parse import urlparse
from urllib.request import Request, urlopen


DEFAULT_USER_AGENT = 'Kodi Appi/0.6.0'


def _headers(extra=None):
    headers = {
        'User-Agent': DEFAULT_USER_AGENT,
        'Accept': 'application/vnd.apple.mpegurl, application/x-mpegURL, video/mp4, text/plain, */*',
        'Accept-Encoding': 'identity',
    }
    if extra:
        headers.update(extra)
    return headers


def fetch_text(url, timeout=20):
    request = Request(url, headers=_headers())
    with urlopen(request, timeout=timeout) as response:
        raw = response.read()
        charset = response.headers.get_content_charset() or 'utf-8'
    return raw.decode(charset, errors='replace')


def classify_stream(final_url, content_type, sample):
    content_type = (content_type or '').lower()
    path = urlparse(final_url or '').path.lower()
    stripped = (sample or b'').lstrip()
    if (
        stripped.startswith(b'#EXTM3U')
        or 'mpegurl' in content_type
        or path.endswith('.m3u8')
    ):
        return 'hls'
    if (
        'video/mp4' in content_type
        or path.endswith('.mp4')
        or b'ftyp' in (sample or b'')[:64]
    ):
        return 'mp4'
    return 'unknown'


def probe_stream(url, timeout=12):
    """Probe a provider URL without downloading the complete media file."""
    request = Request(
        url,
        headers=_headers({'Range': 'bytes=0-8191'}),
    )
    with urlopen(request, timeout=timeout) as response:
        final_url = response.geturl()
        content_type = response.headers.get('Content-Type', '').split(';', 1)[0].strip().lower()
        sample = response.read(8192)
    return {
        'kind': classify_stream(final_url, content_type, sample),
        'final_url': final_url,
        'content_type': content_type,
    }
