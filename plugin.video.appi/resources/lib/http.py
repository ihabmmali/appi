from urllib.request import Request, urlopen


DEFAULT_USER_AGENT = 'Kodi Appi/0.4.0'


def fetch_text(url, timeout=20):
    request = Request(
        url,
        headers={
            'User-Agent': DEFAULT_USER_AGENT,
            'Accept': 'application/vnd.apple.mpegurl, application/x-mpegURL, text/plain, */*',
            'Accept-Encoding': 'identity',
        },
    )
    with urlopen(request, timeout=timeout) as response:
        raw = response.read()
        charset = response.headers.get_content_charset() or 'utf-8'
    return raw.decode(charset, errors='replace')
