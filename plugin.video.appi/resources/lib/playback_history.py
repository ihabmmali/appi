import time

from . import cache

HISTORY_CACHE = 'playback_history'
SESSION_CACHE = 'playback_history_session'
MAX_MOVIES = 100
MAX_EPISODES = 500


def _history():
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
    if catalog not in {'movies', 'tv'} or not ref:
        return
    history = _history()
    bucket_name = _bucket(catalog)
    bucket = history[bucket_name]
    previous = bucket.get(ref, {}) if isinstance(bucket.get(ref), dict) else {}
    now = time.time()
    entry = {
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
        'position': float(previous.get('position') or 0),
        'total': float(previous.get('total') or 0),
        'completed': bool(previous.get('completed', False)),
        'last_played': now,
    }
    bucket[ref] = entry
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
    value = cache.load_object(SESSION_CACHE)
    return value if isinstance(value, dict) and value.get('ref') else None


def clear_session():
    cache.remove(SESSION_CACHE)


def clear_all():
    cache.remove(HISTORY_CACHE)
    cache.remove(SESSION_CACHE)


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


def update_progress(position, total=0):
    session = load_session()
    if not session:
        return
    catalog = session.get('catalog')
    ref = session.get('ref')
    if catalog not in {'movies', 'tv'} or not ref:
        return
    history = _history()
    bucket = history[_bucket(catalog)]
    entry = bucket.get(ref)
    if not isinstance(entry, dict):
        return
    try:
        position = max(0.0, float(position or 0))
    except (TypeError, ValueError):
        position = 0.0
    try:
        total = max(0.0, float(total or 0))
    except (TypeError, ValueError):
        total = 0.0
    if total > 0:
        entry['total'] = total
    if position >= 0:
        entry['position'] = position
    # Do not move the item to the top every polling cycle. last_played records
    # when playback was started, which is the useful ordering for Recent lists.
    entry['completed'] = False
    bucket[ref] = entry
    _save_history(history)


def finish_session(completed=False):
    session = load_session()
    if not session:
        return
    catalog = session.get('catalog')
    ref = session.get('ref')
    history = _history()
    bucket = history.get(_bucket(catalog), {})
    entry = bucket.get(ref)
    if isinstance(entry, dict):
        if completed:
            entry['completed'] = True
            entry['position'] = 0.0
        bucket[ref] = entry
        _save_history(history)
    clear_session()


def get_entry(catalog, ref):
    history = _history()
    value = history.get(_bucket(catalog), {}).get(ref)
    return dict(value) if isinstance(value, dict) else None


def resume_point(catalog, ref):
    entry = get_entry(catalog, ref)
    return _resume_point_from_entry(entry)


def _resume_point_from_entry(entry):
    if not entry or entry.get('completed'):
        return None
    try:
        position = float(entry.get('position') or 0)
        total = float(entry.get('total') or 0)
    except (TypeError, ValueError):
        return None
    # Avoid offering a resume for accidental starts and for items essentially
    # at the end. If total is not known yet, keep a meaningful position.
    if position < 30:
        return None
    if total > 0 and (position >= total - 30 or position / total >= 0.97):
        return None
    return position, total


def resume_points(catalog):
    entries = _history().get(_bucket(catalog), {})
    result = {}
    for ref, entry in entries.items():
        point = _resume_point_from_entry(entry)
        if point:
            result[ref] = point
    return result


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
