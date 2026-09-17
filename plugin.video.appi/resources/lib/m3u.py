import re
from urllib.parse import urlparse

_ATTR_RE = re.compile(r'([A-Za-z0-9_-]+)="([^"]*)"')
_YEAR_RE = re.compile(r'^(?P<title>.*?)(?:\s*\((?P<year>\d{4})\))\s*$')
_EP_RE = re.compile(r'\bS(?P<season>\d{1,3})\s*E(?P<episode>\d{1,4})\b', re.IGNORECASE)


def _split_extinf(line):
    """Split #EXTINF metadata from display title at the first comma outside quotes."""
    in_quotes = False
    for index, char in enumerate(line):
        if char == '"':
            in_quotes = not in_quotes
        elif char == ',' and not in_quotes:
            return line[:index], line[index + 1:].strip()
    return line, ''


def _attributes(meta):
    return {key.lower(): value for key, value in _ATTR_RE.findall(meta)}


def _split_title_year(value):
    value = (value or '').strip()
    match = _YEAR_RE.match(value)
    if not match:
        return value, None
    title = match.group('title').strip()
    try:
        year = int(match.group('year'))
    except (TypeError, ValueError):
        year = None
    return title, year


def _season_episode_from_url(url):
    try:
        parts = [p for p in urlparse(url).path.split('/') if p]
        if len(parts) >= 2:
            return int(parts[-2]), int(parts[-1])
    except (TypeError, ValueError):
        pass
    return None, None


def parse_m3u(text):
    """Parse Appi movie and TV entries from an M3U document."""
    lines = [line.strip() for line in (text or '').splitlines()]
    items = []
    pending = None

    for line in lines:
        if not line:
            continue
        if line.startswith('#EXTINF'):
            meta, display_title = _split_extinf(line)
            pending = (_attributes(meta), display_title)
            continue
        if line.startswith('#'):
            continue
        if pending is None:
            continue

        attrs, display_title = pending
        pending = None
        media_url = line
        media_type = attrs.get('tvg-type', '').lower()
        tvg_id = attrs.get('tvg-id') or attrs.get('tvg-name') or ''
        group_title = attrs.get('group-title', '')

        if media_type == 'movies':
            title, year = _split_title_year(display_title)
            if year is None:
                _, year = _split_title_year(group_title.replace('Movies ', '').strip())
            items.append({
                'kind': 'movie',
                'display_title': display_title,
                'title': title or display_title,
                'year': year,
                'tvg_id': tvg_id,
                'group_title': group_title,
                'media_url': media_url,
            })
            continue

        if media_type == 'tvshows':
            show_title, year = _split_title_year(group_title)
            ep_match = _EP_RE.search(display_title)
            if ep_match:
                season = int(ep_match.group('season'))
                episode = int(ep_match.group('episode'))
            else:
                season, episode = _season_episode_from_url(media_url)

            if not show_title:
                prefix = _EP_RE.split(display_title, maxsplit=1)[0].strip()
                show_title, display_year = _split_title_year(prefix)
                if year is None:
                    year = display_year

            items.append({
                'kind': 'episode',
                'display_title': display_title,
                'show_title': show_title or display_title,
                'year': year,
                'tvg_id': tvg_id,
                'group_title': group_title,
                'season': season,
                'episode': episode,
                'media_url': media_url,
            })

    return items


def dedupe(items):
    seen = set()
    result = []
    for item in items:
        key = item.get('media_url')
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result
