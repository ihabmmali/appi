from . import cache

CACHE_NAME = 'playback_preferences'


def _all():
    value = cache.load_object(CACHE_NAME)
    return value if isinstance(value, dict) else {}


def _key(target, ref='', show_key=''):
    if target == 'show':
        return 'show:{}'.format(show_key)
    if target == 'episode':
        return 'episode:{}'.format(ref)
    return 'movie:{}'.format(ref)


def get_target(target, ref='', show_key=''):
    value = _all().get(_key(target, ref=ref, show_key=show_key), {})
    return dict(value) if isinstance(value, dict) else {}


def set_target(target, values, ref='', show_key=''):
    data = _all()
    key = _key(target, ref=ref, show_key=show_key)
    clean = {k: v for k, v in (values or {}).items() if v is not None}
    if clean:
        data[key] = clean
    else:
        data.pop(key, None)
    cache.save_object(CACHE_NAME, data)


def effective(catalog, ref, show_key=''):
    result = {}
    data = _all()
    if catalog == 'tv' and show_key:
        show = data.get(_key('show', show_key=show_key), {})
        if isinstance(show, dict):
            result.update(show)
        episode = data.get(_key('episode', ref=ref), {})
        if isinstance(episode, dict):
            result.update(episode)
    elif catalog == 'movies':
        movie = data.get(_key('movie', ref=ref), {})
        if isinstance(movie, dict):
            result.update(movie)
    return result
