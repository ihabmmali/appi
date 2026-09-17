import sys
import traceback
from urllib.parse import parse_qsl, urlencode

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

from . import cache
from . import kodi_cache
from . import subtitle_store
from .catalog import build_tv_groups, item_ref, show_cache_name, show_key, sort_movies, sort_shows
from .http import fetch_text, probe_stream
from .m3u import dedupe, parse_m3u

ADDON = xbmcaddon.Addon()
HANDLE = int(sys.argv[1])
BASE_URL = sys.argv[0]
DIRECTORY_CHUNK = 200


def _url(action, **params):
    query = {'action': action}
    for key, value in params.items():
        if value is not None:
            query[key] = value
    return '{}?{}'.format(BASE_URL, urlencode(query))


def _notify(message, error=False):
    icon = xbmcgui.NOTIFICATION_ERROR if error else xbmcgui.NOTIFICATION_INFO
    xbmcgui.Dialog().notification('Appi', message, icon, 4500)


def _setting(name, default=''):
    value = ADDON.getSetting(name)
    return value if value != '' else default


def _int_setting(name, default):
    try:
        return int(_setting(name, str(default)))
    except (TypeError, ValueError):
        return default


def _bool_setting(name, default=False):
    value = ADDON.getSetting(name)
    if value == '':
        return default
    return value.lower() == 'true'


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


def _stream_cache():
    data = cache.load_object('stream_types')
    return data if data else {}


def _save_stream_cache(data):
    cache.save_object('stream_types', data)


def _stream_key(catalog_name, ref):
    return '{}|{}'.format(catalog_name, ref)


def _clear_stream_cache(catalog_name):
    data = _stream_cache()
    prefix = catalog_name + '|'
    changed = False
    for key in list(data):
        if key.startswith(prefix):
            data.pop(key, None)
            changed = True
    if changed:
        _save_stream_cache(data)


def _write_tv_index(episodes):
    summaries, groups = build_tv_groups(episodes)
    keep = set()
    for summary in summaries:
        cache_name = summary['cache_name']
        keep.add(cache_name)
        cache.save(cache_name, groups[summary['show_key']])
    cache.save('tv_shows', summaries)
    cache.remove_prefix('tv_show_', keep=keep)
    cache.remove('tv')
    return summaries


def _migrate_legacy_tv_cache():
    indexed = cache.load('tv_shows')
    if indexed is not None:
        return indexed['items']
    legacy = cache.load('tv')
    if legacy is None:
        return None
    try:
        summaries = _write_tv_index(legacy['items'])
        _notify('TV cache upgraded for faster navigation')
        return summaries
    except Exception as exc:
        xbmc.log('Appi TV cache migration failed: {}'.format(exc), xbmc.LOGERROR)
        return None


def refresh_movies(show_notification=True):
    movie_url = _require_setting('movie_m3u_url', 'Movie M3U URL')
    if not movie_url:
        return None
    try:
        text = fetch_text(movie_url, timeout=_int_setting('request_timeout', 20))
        items = dedupe([item for item in parse_m3u(text) if item.get('kind') == 'movie'])
        cache.save('movies', items)
        _clear_stream_cache('movies')
        if show_notification:
            _notify('Movie list refreshed: {} titles'.format(len(items)))
        return items
    except Exception as exc:
        xbmc.log('Appi movie refresh failed: {}'.format(exc), xbmc.LOGERROR)
        xbmcgui.Dialog().ok('Appi', 'Movie refresh failed. The previous cached movie list was kept.\n\n{}: {}'.format(type(exc).__name__, exc))
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
        episodes = dedupe(all_items)
        progress.update(96, 'Building fast TV index...')
        summaries = _write_tv_index(episodes)
        _clear_stream_cache('tv')
        progress.update(100, 'TV show catalogue refreshed')
        if show_notification:
            _notify('TV list refreshed: {} shows / {} episodes'.format(len(summaries), len(episodes)))
        return summaries
    except Exception as exc:
        xbmc.log('Appi TV refresh failed: {}'.format(exc), xbmc.LOGERROR)
        xbmcgui.Dialog().ok('Appi', 'TV refresh failed. The previous indexed catalogue was kept where possible.\n\n{}: {}'.format(type(exc).__name__, exc))
        return None
    finally:
        progress.close()


def refresh_all():
    movies = refresh_movies(show_notification=False)
    tv = refresh_tv(show_notification=False)
    if movies is not None and tv is not None:
        _notify('All lists refreshed')
    else:
        _notify('Refresh completed with an error', error=True)


def _load_movies():
    payload = cache.load('movies')
    if payload is not None:
        return payload['items']
    return refresh_movies(show_notification=False) or []


def _load_tv_shows():
    payload = cache.load('tv_shows')
    if payload is not None:
        return payload['items']
    migrated = _migrate_legacy_tv_cache()
    if migrated is not None:
        return migrated
    return refresh_tv(show_notification=False) or []


def _summary_by_key(key):
    for summary in _load_tv_shows():
        if summary.get('show_key') == key:
            return summary
    return None


def _load_show_episodes(key):
    summary = _summary_by_key(key)
    cache_name = summary.get('cache_name') if summary else show_cache_name(key)
    payload = cache.load(cache_name)
    return payload['items'] if payload is not None else []


def _find_by_ref(catalog_name, ref, key=None):
    if catalog_name == 'movies':
        source = _load_movies()
    elif key:
        source = _load_show_episodes(key)
    else:
        source = []
        for summary in _load_tv_shows():
            payload = cache.load(summary.get('cache_name') or show_cache_name(summary.get('show_key', '')))
            if payload:
                source.extend(payload['items'])
    for item in source:
        if item_ref(item) == ref:
            return item
    return None


def _directory_video_info(item, media_type=None):
    kind = item.get('kind')
    info = {'mediatype': media_type or ('movie' if kind == 'movie' else 'episode')}
    if kind == 'movie':
        info['title'] = item.get('title') or item.get('display_title') or ''
    else:
        info['title'] = item.get('display_title') or item.get('show_title') or ''
        if item.get('show_title'):
            info['tvshowtitle'] = item['show_title']
        if item.get('season') is not None:
            info['season'] = int(item['season'])
        if item.get('episode') is not None:
            info['episode'] = int(item['episode'])
    if item.get('year'):
        info['year'] = int(item['year'])
    if item.get('tvg_id'):
        info['imdbnumber'] = item['tvg_id']
    return info


def _set_playback_metadata(list_item, item):
    tag = list_item.getVideoInfoTag()
    kind = item.get('kind')
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
    if item.get('year'):
        tag.setYear(int(item['year']))
    if item.get('tvg_id'):
        try:
            tag.setUniqueID(item['tvg_id'], 'imdb', True)
        except Exception:
            pass
        try:
            tag.setIMDBNumber(item['tvg_id'])
        except Exception:
            pass


def _playable_tuple(item, catalog_name, key=None):
    label = item.get('display_title') or item.get('title') or ''
    list_item = xbmcgui.ListItem(label=label, offscreen=True)
    list_item.setInfo('video', _directory_video_info(item))
    list_item.setProperty('IsPlayable', 'true')
    return (_url('play_ref', catalog=catalog_name, ref=item_ref(item), show_key=key), list_item, False)


def _folder_tuple(label, url, info=None):
    item = xbmcgui.ListItem(label=label, offscreen=True)
    if info:
        item.setInfo('video', info)
    return (url, item, True)


def _send_items(items):
    total = len(items)
    for start in range(0, total, DIRECTORY_CHUNK):
        xbmcplugin.addDirectoryItems(HANDLE, items[start:start + DIRECTORY_CHUNK], totalItems=total)


def _finish(cache_to_disc=True):
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=cache_to_disc)


def _add_movie_sort_methods():
    methods = []
    for name in ('SORT_METHOD_TITLE_IGNORE_THE', 'SORT_METHOD_TITLE'):
        if hasattr(xbmcplugin, name):
            methods.append(getattr(xbmcplugin, name))
            break
    for name in ('SORT_METHOD_VIDEO_YEAR', 'SORT_METHOD_YEAR'):
        if hasattr(xbmcplugin, name):
            methods.append(getattr(xbmcplugin, name))
            break
    for method in methods:
        try:
            xbmcplugin.addSortMethod(HANDLE, method)
        except Exception:
            pass


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
    items = sort_movies(_load_movies(), _int_setting('movie_sort', 0))
    xbmcplugin.setContent(HANDLE, 'movies')
    _add_movie_sort_methods()
    total = len(items)
    for start in range(0, total, DIRECTORY_CHUNK):
        tuples = [_playable_tuple(item, 'movies') for item in items[start:start + DIRECTORY_CHUNK]]
        xbmcplugin.addDirectoryItems(HANDLE, tuples, totalItems=total)
    _finish()


def show_tvshows():
    shows = sort_shows(_load_tv_shows(), _int_setting('tv_sort', 0))
    xbmcplugin.setContent(HANDLE, 'tvshows')
    directory_items = []
    for show in shows:
        title = show.get('show_title') or show.get('group_title') or 'TV Show'
        label = show.get('group_title') or title
        info = {'mediatype': 'tvshow', 'title': title}
        if show.get('year'):
            info['year'] = int(show['year'])
        if show.get('tvg_id'):
            info['imdbnumber'] = show['tvg_id']
        directory_items.append(_folder_tuple(label, _url('seasons', show_key=show['show_key']), info))
    _send_items(directory_items)
    _finish()


def show_seasons(key):
    summary = _summary_by_key(key)
    seasons = (summary or {}).get('seasons') or []
    tvg_id = (summary or {}).get('tvg_id') or ''
    xbmcplugin.setContent(HANDLE, 'seasons')
    directory_items = []
    for season in seasons:
        info = {'mediatype': 'season', 'title': 'Season {}'.format(season), 'season': int(season)}
        if tvg_id:
            info['imdbnumber'] = tvg_id
        directory_items.append(_folder_tuple('Season {}'.format(season), _url('episodes', show_key=key, season=season), info))
    _send_items(directory_items)
    _finish()


def show_episodes(key, season):
    try:
        season_number = int(season)
    except (TypeError, ValueError):
        season_number = None
    episodes = [item for item in _load_show_episodes(key) if item.get('season') == season_number]
    episodes.sort(key=lambda item: (item.get('episode') if item.get('episode') is not None else 999999, (item.get('display_title') or '').casefold()))
    xbmcplugin.setContent(HANDLE, 'episodes')
    if hasattr(xbmcplugin, 'SORT_METHOD_EPISODE'):
        try:
            xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_EPISODE)
        except Exception:
            pass
    _send_items([_playable_tuple(item, 'tv', key) for item in episodes])
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
        matches = [item for item in _load_movies() if needle in (item.get('display_title') or '').casefold() or needle in (item.get('title') or '').casefold()]
        matches = sort_movies(matches, _int_setting('movie_sort', 0))
        xbmcplugin.setContent(HANDLE, 'movies')
        _add_movie_sort_methods()
        _send_items([_playable_tuple(item, 'movies') for item in matches])
        _finish()
        return
    matches = [show for show in _load_tv_shows() if needle in '{} {}'.format(show.get('show_title') or '', show.get('group_title') or '').casefold()]
    matches = sort_shows(matches, _int_setting('tv_sort', 0))
    xbmcplugin.setContent(HANDLE, 'tvshows')
    directory_items = []
    for show in matches:
        title = show.get('show_title') or show.get('group_title') or 'TV Show'
        label = show.get('group_title') or title
        info = {'mediatype': 'tvshow', 'title': title}
        if show.get('year'):
            info['year'] = int(show['year'])
        if show.get('tvg_id'):
            info['imdbnumber'] = show['tvg_id']
        directory_items.append(_folder_tuple(label, _url('seasons', show_key=show['show_key']), info))
    _send_items(directory_items)
    _finish()


def _probe_kind(catalog_name, ref, media_url):
    data = _stream_cache()
    key = _stream_key(catalog_name, ref)
    existing = data.get(key)
    if isinstance(existing, dict) and existing.get('kind') in {'hls', 'mp4', 'unknown'}:
        return existing
    try:
        result = probe_stream(media_url, timeout=min(12, _int_setting('request_timeout', 20)))
    except Exception as exc:
        xbmc.log('Appi stream probe failed: {}'.format(exc), xbmc.LOGWARNING)
        result = {'kind': 'unknown', 'final_url': media_url, 'content_type': ''}
    data[key] = {'kind': result.get('kind', 'unknown'), 'content_type': result.get('content_type', '')}
    _save_stream_cache(data)
    return data[key]


def _configure_hls(list_item):
    list_item.setMimeType('application/vnd.apple.mpegurl')
    list_item.setContentLookup(False)
    mode = _int_setting('hls_quality_mode', 1)
    if mode == 0:
        return
    if not xbmc.getCondVisibility('System.HasAddon(inputstream.adaptive)'):
        _notify('InputStream Adaptive is not installed; using Kodi HLS playback', error=True)
        return
    list_item.setProperty('inputstream', 'inputstream.adaptive')
    if mode == 1:
        list_item.setProperty('inputstream.adaptive.stream_selection_type', 'ask-quality')
    elif mode == 2:
        max_kbps = max(250, _int_setting('hls_max_bitrate_kbps', 8000))
        list_item.setProperty('inputstream.adaptive.stream_selection_type', 'adaptive')
        list_item.setProperty('inputstream.adaptive.chooser_bandwidth_max', str(max_kbps * 1000))


def _configure_mp4(list_item):
    list_item.setMimeType('video/mp4')
    list_item.setContentLookup(False)
    if _bool_setting('manage_mp4_buffer', True):
        kodi_cache.apply_mp4_cache(memory_mb=_int_setting('mp4_buffer_mb', 64), read_factor=_int_setting('mp4_read_factor', 4))


def play_ref(params):
    catalog_name = params.get('catalog', '')
    ref = params.get('ref', '')
    key = params.get('show_key') or None
    if catalog_name not in {'movies', 'tv'} or not ref:
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    item = _find_by_ref(catalog_name, ref, key)
    if not item:
        xbmcgui.Dialog().ok('Appi', 'This cached item could not be found. Refresh the catalogue and try again.')
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    media_url = item.get('media_url') or ''
    if not media_url:
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    list_item = xbmcgui.ListItem(label=item.get('display_title') or item.get('title') or '', path=media_url, offscreen=True)
    _set_playback_metadata(list_item, item)
    list_item.setProperty('IsPlayable', 'true')
    stream = _probe_kind(catalog_name, ref, media_url)
    if stream.get('kind') == 'hls':
        _configure_hls(list_item)
    elif stream.get('kind') == 'mp4':
        _configure_mp4(list_item)
    if _bool_setting('persist_subtitles', True):
        saved = subtitle_store.prepare_session(catalog_name, ref)
        if saved:
            try:
                list_item.setSubtitles(saved)
            except Exception as exc:
                xbmc.log('Appi could not attach saved subtitles: {}'.format(exc), xbmc.LOGWARNING)
    xbmcplugin.setResolvedUrl(HANDLE, True, list_item)


def _run_action(params):
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
        raise ValueError('Unknown action: {}'.format(action))


def run():
    params = dict(parse_qsl(sys.argv[2][1:] if len(sys.argv) > 2 and sys.argv[2].startswith('?') else ''))
    action = params.get('action', 'root')
    try:
        _run_action(params)
    except Exception as exc:
        detail = '{}: {}'.format(type(exc).__name__, exc)
        xbmc.log('Appi action {} failed: {}\n{}'.format(action, detail, traceback.format_exc()), xbmc.LOGERROR)
        xbmcgui.Dialog().ok('Appi error', 'Could not open/run "{}".\n\n{}\n\nPlease report this exact message.'.format(action, detail))
        if action != 'play_ref':
            try:
                xbmcplugin.endOfDirectory(HANDLE, succeeded=False, cacheToDisc=False)
            except Exception:
                pass
        else:
            try:
                xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
            except Exception:
                pass
