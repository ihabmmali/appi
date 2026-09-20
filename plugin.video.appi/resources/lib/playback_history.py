import time

from . import cache


HISTORY_CACHE = 'recent_media_v2'
SESSION_CACHE = 'recent_media_session_v2'
RESET_MARKER = 'kodi_native_status_v1'
LEGACY_CACHES = ('playback_history', 'playback_history_session', 'watched_episodes')
MAX_MOVIES = 100
MAX_EPISODES = 500


def _initialize():
    """Discard the superseded Appi status store once; Kodi now owns that state."""
    if cache.load_object(RESET_MARKER):
        return
    for name in LEGACY_CACHES:
        cache.remove(name)
    cache.remove(HISTORY_CACHE)
    cache.remove(SESSION_CACHE)
    cache.save_object(RESET_MARKER, {'initialized_at': time.time()})


def _history():
    _initialize()
    value = cache.load_object(HISTORY_CACHE)
    if not isinstance(value, dict):
        value = {}
    movies = value.get('movies') if isinstance(value.get('movies'), dict) else {}
    episodes = value.get('episodes') if isinstance(value.get('episodes'), dict) else {}
    return {'movies': movies, 'episodes': episodes}


def _save_history(value):
    cache.save_object(HISTORY_CACHE, value)


def _bucket(catalog):
    return 'movies' if catalog == 'movies' else 'episodes'


def _trim(entries, maximum):
    if len(entries) <= maximum:
        return entries
    keep = sorted(
        entries.items(),
        key=lambda pair: float((pair[1] or {}).get('last_played') or 0),
        reverse=True,
    )[:maximum]
    return dict(keep)


def start_session(catalog, ref, item, show_key=''):
    """Record recent-media identity only; resume and watched state belong to Kodi."""
    if catalog not in {'movies', 'tv'} or not ref:
        return
    history = _history()
    bucket_name = _bucket(catalog)
    now = time.time()
    history[bucket_name][ref] = {
        'catalog': catalog,
        'ref': ref,
        'show_key': show_key or '',
        'kind': item.get('kind') or ('movie' if catalog == 'movies' else 'episode'),
        'display_title': item.get('display_title') or item.get('title') or '',
        'title': item.get('title') or '',
        'show_title': item.get('show_title') or '',
        'year': item.get('year'),
        'tvg_id': item.get('tvg_id') or '',
        'season': item.get('season'),
        'episode': item.get('episode'),
        'last_played': now,
    }
    history['movies'] = _trim(history['movies'], MAX_MOVIES)
    history['episodes'] = _trim(history['episodes'], MAX_EPISODES)
    _save_history(history)
    cache.save_object(SESSION_CACHE, {
        'catalog': catalog,
        'ref': ref,
        'show_key': show_key or '',
        'started_at': now,
    })


def load_session():
    _initialize()
    value = cache.load_object(SESSION_CACHE)
    return value if isinstance(value, dict) and value.get('ref') else None


def clear_session():
    cache.remove(SESSION_CACHE)


def clear_all():
    cache.remove(HISTORY_CACHE)
    cache.remove(SESSION_CACHE)
    for name in LEGACY_CACHES:
        cache.remove(name)


def remove(catalog, ref):
    if catalog not in {'movies', 'tv'} or not ref:
        return False
    history = _history()
    bucket = history[_bucket(catalog)]
    if ref not in bucket:
        return False
    bucket.pop(ref, None)
    _save_history(history)
    session = load_session()
    if session and session.get('catalog') == catalog and session.get('ref') == ref:
        clear_session()
    return True


def remove_show(show_key):
    if not show_key:
        return False
    history = _history()
    episodes = history['episodes']
    refs = [
        ref for ref, entry in episodes.items()
        if isinstance(entry, dict) and entry.get('show_key') == show_key
    ]
    if not refs:
        return False
    for ref in refs:
        episodes.pop(ref, None)
    _save_history(history)
    session = load_session()
    if session and session.get('catalog') == 'tv' and session.get('show_key') == show_key:
        clear_session()
    return True


def finish_session():
    session = load_session()
    clear_session()
    return session


def get_entry(catalog, ref):
    history = _history()
    value = history.get(_bucket(catalog), {}).get(ref)
    return dict(value) if isinstance(value, dict) else None


def recent_movies(limit=50):
    values = list(_history()['movies'].values())
    values.sort(key=lambda item: float(item.get('last_played') or 0), reverse=True)
    return [dict(item) for item in values[:max(1, int(limit))]]


def recent_shows(limit=50):
    grouped = {}
    for entry in _history()['episodes'].values():
        if not isinstance(entry, dict):
            continue
        key = entry.get('show_key') or '{}\x1f{}\x1f{}'.format(
            entry.get('tvg_id') or '', entry.get('show_title') or '', entry.get('year') or ''
        )
        previous = grouped.get(key)
        if previous is None or float(entry.get('last_played') or 0) > float(previous.get('last_played') or 0):
            grouped[key] = dict(entry)
            grouped[key]['show_key'] = key
    values = list(grouped.values())
    values.sort(key=lambda item: float(item.get('last_played') or 0), reverse=True)
    return values[:max(1, int(limit))]
