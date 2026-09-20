import time

from . import cache


FAVORITES_CACHE = 'favorites'


def _data():
    value = cache.load_object(FAVORITES_CACHE)
    if not isinstance(value, dict):
        value = {}
    movies = value.get('movies') if isinstance(value.get('movies'), dict) else {}
    shows = value.get('shows') if isinstance(value.get('shows'), dict) else {}
    return {'movies': movies, 'shows': shows}


def _save(value):
    cache.save_object(FAVORITES_CACHE, value)


def contains(kind, key):
    bucket = 'movies' if kind == 'movie' else 'shows'
    return bool(key and key in _data()[bucket])


def keys(kind):
    bucket = 'movies' if kind == 'movie' else 'shows'
    return set(_data()[bucket])


def set_favorite(kind, key, item, enabled=True):
    if kind not in {'movie', 'show'} or not key:
        return False
    value = _data()
    bucket = value['movies' if kind == 'movie' else 'shows']
    if enabled:
        previous = bucket.get(key) if isinstance(bucket.get(key), dict) else {}
        bucket[key] = {
            'key': key,
            'title': item.get('title') or item.get('show_title') or item.get('group_title') or '',
            'year': item.get('year'),
            'added_at': float(previous.get('added_at') or time.time()),
        }
    else:
        bucket.pop(key, None)
    _save(value)
    return True


def entries(kind):
    bucket = _data()['movies' if kind == 'movie' else 'shows']
    values = list(bucket.values())
    values.sort(key=lambda item: float(item.get('added_at') or 0), reverse=True)
    return values
