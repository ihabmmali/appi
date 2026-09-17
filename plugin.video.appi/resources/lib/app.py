import hashlib
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
    except Exception as exc:
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


def _load_catalog(name):
    payload = cache.load(name)
    if payload is not None:
        return payload['items']
    if name == 'movies':
        items = refresh_movies(show_notification=False)
    else:
        items = refresh_tv(show_notification=False)
    return items or []


def _load_movies():
    return _load_catalog('movies')


def _load_tv():
    return _load_catalog('tv')


def _item_ref(item):
    kind = item.get('kind') or ''
    tvg_id = item.get('tvg_id') or ''
    if kind == 'movie' and tvg_id:
        return 'm:{}'.format(tvg_id)
    if kind == 'episode' and tvg_id:
        return 'e:{}:{}:{}'.format(tvg_id, item.get('season'), item.get('episode'))
    digest = hashlib.sha1((item.get('media_url') or '').encode('utf-8')).hexdigest()
    return 'u:{}'.format(digest)


def _find_by_ref(catalog, ref):
    for item in _load_catalog(catalog):
        if _item_ref(item) == ref:
            return item
    return None


def _set_common_video_metadata(list_item, item):
    tag = list_item.getVideoInfoTag()
    kind = item.get('kind')
    year = item.get('year')
    tvg_id = item.get('tvg_id') or ''

    if kind == 'movie':
        title = item.get('title') or item.get('display_title') or ''
        tag.setMediaType('movie')
        tag.setTitle(title)
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
        tag.setIMDBNumber(tvg_id)


def _playable_tuple(item, catalog, prefix=''):
    label = '{}{}'.format(prefix, item.get('display_title') or item.get('title') or '')
    list_item = xbmcgui.ListItem(label=label, offscreen=True)
    _set_common_video_metadata(list_item, item)
    list_item.setProperty('IsPlayable', 'true')
    url = _url('play_ref', catalog=catalog, ref=_item_ref(item))
    return (url, list_item, False)


def _folder_tuple(label, url, media_type=None, title=None, year=None, tvg_id=None, season=None):
    item = xbmcgui.ListItem(label=label, offscreen=True)
    if media_type:
        tag = item.getVideoInfoTag()
        tag.setMediaType(media_type)
        tag.setTitle(title or label)
        if year:
            tag.setYear(int(year))
        if tvg_id:
            tag.setUniqueID(tvg_id, 'imdb', True)
            tag.setIMDBNumber(tvg_id)
        if season is not None:
            tag.setSeason(int(season))
    return (url, item, True)


def _send_items(items):
    if items:
        xbmcplugin.addDirectoryItems(HANDLE, items, totalItems=len(items))


def _finish():
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=True)


def show_root():
    entries = [
        _folder_tuple('Movies', _url('movies')),
        _folder_tuple('TV Shows', _url('tvshows')),
        _folder_tuple('Search Movies', _url('search', scope='movies')),
        _folder_tuple('Search TV Shows', _url('search', scope='tv')),
        _folder_tuple('Refresh Movie List', _url('refresh_movies')),
        _folder_tuple('Refresh TV Show List', _url('refresh_tv')),
        _folder_tuple('Refresh All Lists', _url('refresh_all')),
        _folder_tuple('Settings', _url('settings')),
    ]
    _send_items(entries)
    _finish()


def show_movies():
    items = _load_movies()
    xbmcplugin.setContent(HANDLE, 'movies')
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_TITLE_IGNORE_THE)
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_YEAR)
    _send_items([_playable_tuple(item, 'movies') for item in items])
    _finish()


def _show_key(item):
    return '{}\x1f{}\x1f{}'.format(item.get('tvg_id') or '', item.get('show_title') or '', item.get('year') or '')


def show_tvshows():
    episodes = _load_tv()
    groups = {}
    for episode in episodes:
        groups.setdefault(_show_key(episode), episode)

    xbmcplugin.setContent(HANDLE, 'tvshows')
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_TITLE_IGNORE_THE)
    directory_items = []
    for key, episode in groups.items():
        label = episode.get('group_title') or episode.get('show_title') or 'TV Show'
        directory_items.append(_folder_tuple(
            label,
            _url('seasons', show_key=key),
            media_type='tvshow',
            title=episode.get('show_title') or label,
            year=episode.get('year'),
            tvg_id=episode.get('tvg_id'),
        ))
    _send_items(directory_items)
    _finish()


def show_seasons(show_key):
    episodes = [item for item in _load_tv() if _show_key(item) == show_key]
    seasons = sorted({item.get('season') for item in episodes if item.get('season') is not None})
    show_title = episodes[0].get('show_title') if episodes else ''
    tvg_id = episodes[0].get('tvg_id') if episodes else ''

    xbmcplugin.setContent(HANDLE, 'seasons')
    directory_items = []
    for season in seasons:
        directory_items.append(_folder_tuple(
            'Season {}'.format(season),
            _url('episodes', show_key=show_key, season=season),
            media_type='season',
            title='Season {}'.format(season),
            tvg_id=tvg_id,
            season=season,
        ))
    _send_items(directory_items)
    _finish()


def show_episodes(show_key, season):
    try:
        season_number = int(season)
    except (TypeError, ValueError):
        season_number = None
    episodes = [
        item for item in _load_tv()
        if _show_key(item) == show_key and item.get('season') == season_number
    ]
    episodes.sort(key=lambda item: (
        item.get('episode') if item.get('episode') is not None else 999999,
        (item.get('display_title') or '').casefold(),
    ))
    xbmcplugin.setContent(HANDLE, 'episodes')
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_EPISODE)
    _send_items([_playable_tuple(item, 'tv') for item in episodes])
    _finish()


def search(scope):
    scope = scope if scope in {'movies', 'tv'} else 'movies'
    label = 'Search Movies' if scope == 'movies' else 'Search TV Shows'
    query = xbmcgui.Dialog().input(label, type=xbmcgui.INPUT_ALPHANUM).strip()
    if not query:
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return

    needle = query.casefold()
    if scope == 'movies':
        matches = [
            item for item in _load_movies()
            if needle in (item.get('display_title') or '').casefold()
            or needle in (item.get('title') or '').casefold()
        ]
        xbmcplugin.setContent(HANDLE, 'movies')
        xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_TITLE_IGNORE_THE)
        xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_YEAR)
        _send_items([_playable_tuple(item, 'movies') for item in matches])
        _finish()
        return

    # Search TV by show title, then present matching shows rather than every
    # matching episode. Selecting a result continues through Seasons -> Episodes.
    groups = {}
    for episode in _load_tv():
        haystack = '{} {}'.format(
            episode.get('show_title') or '',
            episode.get('group_title') or '',
        ).casefold()
        if needle in haystack:
            groups.setdefault(_show_key(episode), episode)

    xbmcplugin.setContent(HANDLE, 'tvshows')
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_TITLE_IGNORE_THE)
    directory_items = []
    for key, episode in groups.items():
        title = episode.get('show_title') or episode.get('group_title') or 'TV Show'
        label = episode.get('group_title') or title
        directory_items.append(_folder_tuple(
            label,
            _url('seasons', show_key=key),
            media_type='tvshow',
            title=title,
            year=episode.get('year'),
            tvg_id=episode.get('tvg_id'),
        ))
    _send_items(directory_items)
    _finish()


def play_ref(params):
    catalog = params.get('catalog', '')
    ref = params.get('ref', '')
    if catalog not in {'movies', 'tv'} or not ref:
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    item = _find_by_ref(catalog, ref)
    if not item:
        xbmcgui.Dialog().ok('Appi', 'This cached item could not be found. Refresh the catalogue and try again.')
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    media_url = item.get('media_url') or ''
    if not media_url:
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    list_item = xbmcgui.ListItem(label=item.get('display_title') or item.get('title') or '', path=media_url, offscreen=True)
    _set_common_video_metadata(list_item, item)
    list_item.setProperty('IsPlayable', 'true')
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
    elif action == 'seasons':
        show_seasons(params.get('show_key', ''))
    elif action == 'episodes':
        show_episodes(params.get('show_key', ''), params.get('season'))
    elif action == 'search':
        search(params.get('scope', 'movies'))
    elif action == 'play_ref':
        play_ref(params)
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
