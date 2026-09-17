import sys
from urllib.parse import parse_qsl, urlencode

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

from . import cache
from .http import fetch_text
from .m3u import dedupe, parse_m3u

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
HANDLE = int(sys.argv[1])
BASE_URL = sys.argv[0]


def _url(action, **params):
    query = {'action': action}
    for key, value in params.items():
        if value is not None:
            query[key] = value
    return '{}?{}'.format(BASE_URL, urlencode(query))


def _notify(message, error=False):
    icon = xbmcgui.NOTIFICATION_ERROR if error else xbmcgui.NOTIFICATION_INFO
    xbmcgui.Dialog().notification('Appi', message, icon, 4000)


def _setting(name, default=''):
    value = ADDON.getSetting(name)
    return value if value != '' else default


def _int_setting(name, default):
    try:
        return int(_setting(name, str(default)))
    except (TypeError, ValueError):
        return default


def _require_setting(name, label):
    value = _setting(name).strip()
    if value:
        return value
    xbmcgui.Dialog().ok('Appi', '{} is not configured. Open Appi settings and enter it first.'.format(label))
    ADDON.openSettings()
    return None


def _build_tv_page_url(base, page):
    if '{page}' in base:
        return base.replace('{page}', str(page))
    return '{}/{}'.format(base.rstrip('/'), page)


def refresh_movies(show_notification=True):
    movie_url = _require_setting('movie_m3u_url', 'Movie M3U URL')
    if not movie_url:
        return None
    try:
        text = fetch_text(movie_url, timeout=_int_setting('request_timeout', 20))
        items = dedupe([item for item in parse_m3u(text) if item.get('kind') == 'movie'])
        cache.save('movies', items)
        if show_notification:
            _notify('Movie list refreshed: {} titles'.format(len(items)))
        return items
    except Exception as exc:  # Kodi UI must report network/parser failures without destroying old cache.
        xbmc.log('Appi movie refresh failed: {}'.format(exc), xbmc.LOGERROR)
        xbmcgui.Dialog().ok('Appi', 'Movie refresh failed. The previous cached movie list was kept.\n\n{}'.format(exc))
        return None


def refresh_tv(show_notification=True):
    base = _require_setting('tv_m3u_base_url', 'TV Show M3U base URL')
    if not base:
        return None
    page_count = max(1, _int_setting('tv_page_count', 30))
    timeout = _int_setting('request_timeout', 20)
    progress = xbmcgui.DialogProgress()
    progress.create('Appi', 'Refreshing TV show catalogue...')
    all_items = []
    try:
        for page in range(1, page_count + 1):
            if progress.iscanceled():
                _notify('TV refresh cancelled')
                return None
            progress.update(int(((page - 1) / page_count) * 100), 'Downloading TV page {} of {}'.format(page, page_count))
            text = fetch_text(_build_tv_page_url(base, page), timeout=timeout)
            all_items.extend(item for item in parse_m3u(text) if item.get('kind') == 'episode')
        items = dedupe(all_items)
        cache.save('tv', items)
        progress.update(100, 'TV show catalogue refreshed')
        if show_notification:
            _notify('TV list refreshed: {} episodes'.format(len(items)))
        return items
    except Exception as exc:
        xbmc.log('Appi TV refresh failed: {}'.format(exc), xbmc.LOGERROR)
        xbmcgui.Dialog().ok('Appi', 'TV refresh failed. The previous cached TV list was kept.\n\n{}'.format(exc))
        return None
    finally:
        progress.close()


def refresh_all():
    movies = refresh_movies(show_notification=False)
    tv = refresh_tv(show_notification=False)
    if movies is not None and tv is not None:
        _notify('All lists refreshed')
    elif movies is not None or tv is not None:
        _notify('Refresh completed with an error', error=True)


def _load_movies():
    payload = cache.load('movies')
    if payload is not None:
        return payload['items']
    items = refresh_movies(show_notification=False)
    return items or []


def _load_tv():
    payload = cache.load('tv')
    if payload is not None:
        return payload['items']
    items = refresh_tv(show_notification=False)
    return items or []


def _set_common_video_metadata(list_item, item):
    tag = list_item.getVideoInfoTag()
    kind = item.get('kind')
    year = item.get('year')
    tvg_id = item.get('tvg_id') or ''

    if kind == 'movie':
        tag.setMediaType('movie')
        tag.setTitle(item.get('title') or item.get('display_title') or '')
    else:
        tag.setMediaType('episode')
        tag.setTitle(item.get('display_title') or '')
        tag.setTvShowTitle(item.get('show_title') or '')
        if item.get('season') is not None:
            tag.setSeason(int(item['season']))
        if item.get('episode') is not None:
            tag.setEpisode(int(item['episode']))

    if year:
        tag.setYear(int(year))
    if tvg_id:
        tag.setUniqueID(tvg_id, 'imdb', True)


def _play_url(item):
    return _url(
        'play',
        kind=item.get('kind'),
        media_url=item.get('media_url'),
        display_title=item.get('display_title'),
        title=item.get('title'),
        show_title=item.get('show_title'),
        year=item.get('year'),
        tvg_id=item.get('tvg_id'),
        season=item.get('season'),
        episode=item.get('episode'),
    )


def _add_playable(item, prefix=''):
    label = '{}{}'.format(prefix, item.get('display_title') or item.get('title') or '')
    list_item = xbmcgui.ListItem(label=label, offscreen=True)
    _set_common_video_metadata(list_item, item)
    list_item.setProperty('IsPlayable', 'true')
    xbmcplugin.addDirectoryItem(HANDLE, _play_url(item), list_item, isFolder=False)


def show_root():
    entries = [
        ('Movies', _url('movies')),
        ('TV Shows', _url('tvshows')),
        ('Search', _url('search')),
        ('Refresh Movie List', _url('refresh_movies')),
        ('Refresh TV Show List', _url('refresh_tv')),
        ('Refresh All Lists', _url('refresh_all')),
        ('Settings', _url('settings')),
    ]
    for label, url in entries:
        item = xbmcgui.ListItem(label=label, offscreen=True)
        xbmcplugin.addDirectoryItem(HANDLE, url, item, isFolder=True)
    xbmcplugin.endOfDirectory(HANDLE)


def show_movies():
    items = sorted(_load_movies(), key=lambda x: (x.get('title') or '').casefold())
    xbmcplugin.setContent(HANDLE, 'movies')
    for item in items:
        _add_playable(item)
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    xbmcplugin.endOfDirectory(HANDLE)


def _show_key(item):
    return '{}\x1f{}\x1f{}'.format(item.get('tvg_id') or '', item.get('show_title') or '', item.get('year') or '')


def show_tvshows():
    episodes = _load_tv()
    groups = {}
    for episode in episodes:
        groups.setdefault(_show_key(episode), episode)

    xbmcplugin.setContent(HANDLE, 'tvshows')
    for key, episode in sorted(groups.items(), key=lambda pair: (pair[1].get('show_title') or '').casefold()):
        label = episode.get('group_title') or episode.get('show_title') or 'TV Show'
        item = xbmcgui.ListItem(label=label, offscreen=True)
        tag = item.getVideoInfoTag()
        tag.setMediaType('tvshow')
        tag.setTitle(episode.get('show_title') or label)
        if episode.get('year'):
            tag.setYear(int(episode['year']))
        if episode.get('tvg_id'):
            tag.setUniqueID(episode['tvg_id'], 'imdb', True)
        xbmcplugin.addDirectoryItem(HANDLE, _url('episodes', show_key=key), item, isFolder=True)
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    xbmcplugin.endOfDirectory(HANDLE)


def show_episodes(show_key):
    episodes = [item for item in _load_tv() if _show_key(item) == show_key]
    episodes.sort(key=lambda x: (x.get('season') if x.get('season') is not None else 9999,
                                 x.get('episode') if x.get('episode') is not None else 9999,
                                 (x.get('display_title') or '').casefold()))
    xbmcplugin.setContent(HANDLE, 'episodes')
    for episode in episodes:
        _add_playable(episode)
    xbmcplugin.endOfDirectory(HANDLE)


def search():
    query = xbmcgui.Dialog().input('Search Appi', type=xbmcgui.INPUT_ALPHANUM).strip()
    if not query:
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return
    needle = query.casefold()
    movies = [item for item in _load_movies() if needle in (item.get('display_title') or '').casefold()]
    tv = [item for item in _load_tv() if needle in (item.get('display_title') or '').casefold() or needle in (item.get('show_title') or '').casefold()]
    results = [('Movie: ', item) for item in movies] + [('TV: ', item) for item in tv]
    results.sort(key=lambda pair: (pair[1].get('display_title') or '').casefold())
    xbmcplugin.setContent(HANDLE, 'videos')
    for prefix, item in results:
        _add_playable(item, prefix=prefix)
    xbmcplugin.endOfDirectory(HANDLE)


def play(params):
    item = {
        'kind': params.get('kind', 'movie'),
        'media_url': params.get('media_url', ''),
        'display_title': params.get('display_title', ''),
        'title': params.get('title', ''),
        'show_title': params.get('show_title', ''),
        'tvg_id': params.get('tvg_id', ''),
        'year': int(params['year']) if params.get('year', '').isdigit() else None,
        'season': int(params['season']) if params.get('season', '').isdigit() else None,
        'episode': int(params['episode']) if params.get('episode', '').isdigit() else None,
    }
    media_url = item['media_url']
    if not media_url:
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    list_item = xbmcgui.ListItem(label=item.get('display_title') or item.get('title') or '', path=media_url, offscreen=True)
    _set_common_video_metadata(list_item, item)
    list_item.setProperty('IsPlayable', 'true')
    # Deliberately pass the provider's original URL to Kodi. Kodi follows redirects and handles HLS/MP4 playback.
    xbmcplugin.setResolvedUrl(HANDLE, True, list_item)


def run():
    params = dict(parse_qsl(sys.argv[2][1:] if len(sys.argv) > 2 and sys.argv[2].startswith('?') else ''))
    action = params.get('action', 'root')

    if action == 'root':
        show_root()
    elif action == 'movies':
        show_movies()
    elif action == 'tvshows':
        show_tvshows()
    elif action == 'episodes':
        show_episodes(params.get('show_key', ''))
    elif action == 'search':
        search()
    elif action == 'play':
        play(params)
    elif action == 'refresh_movies':
        refresh_movies()
        xbmc.executebuiltin('Container.Update({})'.format(BASE_URL))
    elif action == 'refresh_tv':
        refresh_tv()
        xbmc.executebuiltin('Container.Update({})'.format(BASE_URL))
    elif action == 'refresh_all':
        refresh_all()
        xbmc.executebuiltin('Container.Update({})'.format(BASE_URL))
    elif action == 'settings':
        ADDON.openSettings()
        xbmc.executebuiltin('Container.Update({})'.format(BASE_URL))
    else:
        xbmcgui.Dialog().ok('Appi', 'Unknown action: {}'.format(action))
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
