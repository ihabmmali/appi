import hashlib
import sys
import traceback
from urllib.error import HTTPError
from urllib.parse import parse_qsl, urlencode

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

from . import cache
from . import kodi_cache
from . import playback_history
from . import playback_prefs
from . import subtitle_store
from .catalog import build_tv_groups, item_ref, show_cache_name, sort_movies, sort_shows
from .http import fetch_text, probe_stream
from .m3u import dedupe, parse_m3u

ADDON = xbmcaddon.Addon()
HANDLE = int(sys.argv[1])
BASE_URL = sys.argv[0]
DIRECTORY_CHUNK = 200
BROWSE_BUCKET_LIMIT = 750
RECENT_CATALOG_LIMIT = 500
MAX_TV_CATALOG_PAGES = 10000
TV_END_HTTP_CODES = {400, 404, 405, 410, 416}


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
        xbmcgui.Dialog().ok(
            'Appi',
            'Movie refresh failed. The previous cached movie list was kept.\n\n{}: {}'.format(
                type(exc).__name__, exc
            ),
        )
        return None


def refresh_tv(show_notification=True):
    base = _require_setting('tv_m3u_base_url', 'TV Show M3U base URL')
    if not base:
        return None
    timeout = _int_setting('request_timeout', 20)
    progress = xbmcgui.DialogProgress()
    progress.create('Appi', 'Refreshing TV show catalogue...')
    all_items = []
    seen_urls = set()
    seen_pages = set()
    completed_pages = 0
    try:
        for page in range(1, MAX_TV_CATALOG_PAGES + 1):
            if progress.iscanceled():
                _notify('TV refresh cancelled')
                return None
            progress.update(
                0,
                'Downloading TV page {} ({} episodes found)'.format(page, len(all_items)),
            )
            page_url = _build_tv_page_url(base, page)
            try:
                text = fetch_text(page_url, timeout=timeout)
            except HTTPError as exc:
                if completed_pages and exc.code in TV_END_HTTP_CODES:
                    break
                raise

            fingerprint = hashlib.sha1((text or '').encode('utf-8')).hexdigest()
            if fingerprint in seen_pages:
                xbmc.log(
                    'Appi stopped TV refresh because page {} repeated earlier content'.format(page),
                    xbmc.LOGWARNING,
                )
                break
            seen_pages.add(fingerprint)

            page_items = [
                item for item in parse_m3u(text)
                if item.get('kind') == 'episode' and item.get('media_url')
            ]
            if not page_items:
                if not completed_pages:
                    raise ValueError('TV catalogue page 1 contained no episodes')
                break
            for item in page_items:
                media_url = item.get('media_url')
                if media_url in seen_urls:
                    continue
                seen_urls.add(media_url)
                all_items.append(item)
            completed_pages = page
        else:
            raise RuntimeError(
                'TV catalogue exceeded the {}-page safety limit'.format(MAX_TV_CATALOG_PAGES)
            )

        episodes = all_items
        progress.update(96, 'Building fast TV index...')
        summaries = _write_tv_index(episodes)
        _clear_stream_cache('tv')
        progress.update(100, 'TV show catalogue refreshed')
        if show_notification:
            _notify(
                'TV list refreshed: {} shows / {} episodes from {} pages'.format(
                    len(summaries), len(episodes), completed_pages
                )
            )
        return summaries
    except Exception as exc:
        xbmc.log('Appi TV refresh failed: {}'.format(exc), xbmc.LOGERROR)
        xbmcgui.Dialog().ok(
            'Appi',
            'TV refresh failed. The previous indexed catalogue was kept where possible.\n\n{}: {}'.format(
                type(exc).__name__, exc
            ),
        )
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


def _apply_resume_metadata(
    list_item, catalog_name, ref, force_start=False, resume_points=None
):
    point = (
        resume_points.get(ref)
        if resume_points is not None
        else playback_history.resume_point(catalog_name, ref)
    )
    if not point:
        return
    position, total = point
    try:
        list_item.getVideoInfoTag().setResumePoint(float(position), float(total or 0))
    except Exception:
        # Kodi 20+ supports InfoTagVideo.setResumePoint(); keep the legacy
        # properties as a harmless fallback for older skins/builds.
        try:
            list_item.setProperty('ResumeTime', str(float(position)))
            if total:
                list_item.setProperty('TotalTime', str(float(total)))
        except Exception:
            pass
    if force_start:
        try:
            list_item.setProperty('StartOffset', str(float(position)))
        except Exception:
            pass


def _context_action(action, **params):
    return 'RunPlugin({})'.format(_url(action, **params))


def _add_context(list_item, items):
    if not items:
        return
    try:
        list_item.addContextMenuItems(items)
    except Exception as exc:
        xbmc.log('Appi could not add context menu: {}'.format(exc), xbmc.LOGWARNING)


def _playable_tuple(
    item, catalog_name, key=None, resume=False, resume_points=None, label_suffix=''
):
    label = item.get('display_title') or item.get('title') or ''
    list_item = xbmcgui.ListItem(label=label + label_suffix, offscreen=True)
    list_item.setInfo('video', _directory_video_info(item))
    list_item.setProperty('IsPlayable', 'true')
    ref = item_ref(item)
    _apply_resume_metadata(
        list_item, catalog_name, ref, force_start=False, resume_points=resume_points
    )
    target = 'movie' if catalog_name == 'movies' else 'episode'
    _add_context(list_item, [
        ('Playback options...', _context_action(
            'configure_playback', target=target, catalog=catalog_name, ref=ref, show_key=key
        )),
    ])
    return (
        _url('play_ref', catalog=catalog_name, ref=ref, show_key=key, resume='1' if resume else None),
        list_item,
        False,
    )


def _folder_tuple(label, url, info=None, context_items=None):
    item = xbmcgui.ListItem(label=label, offscreen=True)
    if info:
        item.setInfo('video', info)
    _add_context(item, context_items or [])
    return (url, item, True)


def _send_items(items):
    total = len(items)
    for start in range(0, total, DIRECTORY_CHUNK):
        xbmcplugin.addDirectoryItems(HANDLE, items[start:start + DIRECTORY_CHUNK], totalItems=total)


def _finish(cache_to_disc=True):
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=cache_to_disc)


def _add_video_sort_methods():
    candidates = [
        ('SORT_METHOD_NONE',),
        ('SORT_METHOD_TITLE_IGNORE_THE', 'SORT_METHOD_TITLE'),
        ('SORT_METHOD_VIDEO_YEAR', 'SORT_METHOD_YEAR'),
    ]
    for names in candidates:
        method = next((getattr(xbmcplugin, name) for name in names if hasattr(xbmcplugin, name)), None)
        if method is None:
            continue
        try:
            xbmcplugin.addSortMethod(HANDLE, method)
        except Exception:
            pass


def _scope_items(scope, provider_order=False):
    if scope == 'movies':
        items = _load_movies()
        return list(items) if provider_order else sort_movies(items, _int_setting('movie_sort', 0))
    items = _load_tv_shows()
    return list(items) if provider_order else sort_shows(items, _int_setting('tv_sort', 0))


def _item_title(scope, item):
    if scope == 'movies':
        return item.get('title') or item.get('display_title') or ''
    return item.get('show_title') or item.get('group_title') or ''


def _index_title(scope, item):
    title = _item_title(scope, item).strip()
    folded = title.casefold()
    for article in ('the ', 'an ', 'a '):
        if folded.startswith(article):
            title = title[len(article):].lstrip()
            break
    return title or _item_title(scope, item)


def _alpha_bucket(scope, item):
    title = _index_title(scope, item)
    first = title[:1].upper()
    return first if first and first.isalnum() else '#'


def _show_media(scope, items, mixed=False):
    if mixed:
        xbmcplugin.setContent(HANDLE, 'files')
    else:
        xbmcplugin.setContent(HANDLE, 'movies' if scope == 'movies' else 'tvshows')
    _add_video_sort_methods()
    resume_points = playback_history.resume_points('movies') if scope == 'movies' else None
    tuples = []
    for item in items:
        if scope == 'movies':
            tuples.append(_playable_tuple(
                item,
                'movies',
                resume_points=resume_points,
                label_suffix=' [Movie]' if mixed else '',
            ))
        else:
            tuples.append(_show_tuple(item, label_suffix=' [TV Show]' if mixed else ''))
    _send_items(tuples)
    _finish()


def _show_mixed(items):
    xbmcplugin.setContent(HANDLE, 'files')
    _add_video_sort_methods()
    resume_points = playback_history.resume_points('movies')
    tuples = []
    for scope, item in items:
        if scope == 'movies':
            tuples.append(_playable_tuple(
                item, 'movies', resume_points=resume_points, label_suffix=' [Movie]'
            ))
        else:
            tuples.append(_show_tuple(item, label_suffix=' [TV Show]'))
    _send_items(tuples)
    _finish()


def show_root():
    entries = [
        _folder_tuple('Movies', _url('movies')),
        _folder_tuple('TV Shows', _url('tvshows')),
        _folder_tuple('Search', _url('search')),
        _folder_tuple('Recently Played Movies', _url('recent_movies', page=1)),
        _folder_tuple('Recently Played TV Shows', _url('recent_tvshows', page=1)),
        _folder_tuple('Refresh Movie List', _url('refresh_movies')),
        _folder_tuple('Refresh TV Show List', _url('refresh_tv')),
        _folder_tuple('Refresh All Lists', _url('refresh_all')),
        _folder_tuple('Settings', _url('settings')),
    ]
    _send_items(entries)
    _finish()


def _show_browse_root(scope):
    noun = 'Movies' if scope == 'movies' else 'TV Shows'
    entries = [
        _folder_tuple('Browse A-Z', _url('browse_index', scope=scope, mode='alpha')),
        _folder_tuple('Browse by Year', _url('browse_index', scope=scope, mode='year')),
        _folder_tuple(
            'Recently Added (first {} in provider order)'.format(RECENT_CATALOG_LIMIT),
            _url('browse_recent', scope=scope),
        ),
        _folder_tuple('All {} (may load slowly)'.format(noun), _url('browse_all', scope=scope)),
    ]
    _send_items(entries)
    _finish()


def show_movies():
    _show_browse_root('movies')


def show_tvshows():
    _show_browse_root('tv')


def _show_tuple(show, label_suffix=''):
    title = show.get('show_title') or show.get('group_title') or 'TV Show'
    label = show.get('group_title') or title
    info = {'mediatype': 'tvshow', 'title': title}
    if show.get('year'):
        info['year'] = int(show['year'])
    if show.get('tvg_id'):
        info['imdbnumber'] = show['tvg_id']
    context = [(
        'Playback options for this show...',
        _context_action('configure_playback', target='show', catalog='tv', show_key=show['show_key']),
    )]
    return _folder_tuple(
        label + label_suffix, _url('seasons', show_key=show['show_key']), info, context
    )


def show_browse_index(scope, mode):
    scope = 'movies' if scope == 'movies' else 'tv'
    items = _scope_items(scope)
    groups = {}
    if mode == 'year':
        for item in items:
            label = str(item.get('year') or 'Unknown year')
            groups.setdefault(label, []).append(item)
        labels = sorted(
            groups,
            key=lambda value: int(value) if value.isdigit() else -1,
            reverse=True,
        )
    else:
        mode = 'alpha'
        for item in items:
            groups.setdefault(_alpha_bucket(scope, item), []).append(item)
        labels = sorted(groups, key=lambda value: (value == '#', value))
    entries = [
        _folder_tuple(
            '{} ({})'.format(label, len(groups[label])),
            _url('browse_items', scope=scope, mode=mode, value=label),
        )
        for label in labels
    ]
    _send_items(entries)
    _finish()


def _subset_for_index(scope, mode, value):
    items = _scope_items(scope)
    if mode == 'year':
        return [item for item in items if str(item.get('year') or 'Unknown year') == value]
    return [item for item in items if _alpha_bucket(scope, item) == value]


def show_browse_items(scope, mode, value, offset=None):
    scope = 'movies' if scope == 'movies' else 'tv'
    items = _subset_for_index(scope, mode, value)
    items.sort(key=lambda item: _index_title(scope, item).casefold())
    if offset is None and len(items) > BROWSE_BUCKET_LIMIT:
        entries = []
        for start in range(0, len(items), BROWSE_BUCKET_LIMIT):
            chunk = items[start:start + BROWSE_BUCKET_LIMIT]
            first = _item_title(scope, chunk[0])
            last = _item_title(scope, chunk[-1])
            entries.append(_folder_tuple(
                '{} – {} ({} items)'.format(first, last, len(chunk)),
                _url(
                    'browse_items', scope=scope, mode=mode, value=value, offset=start
                ),
            ))
        _send_items(entries)
        _finish()
        return
    if offset is not None:
        try:
            start = max(0, int(offset))
        except (TypeError, ValueError):
            start = 0
        items = items[start:start + BROWSE_BUCKET_LIMIT]
    _show_media(scope, items)


def show_browse_recent(scope):
    scope = 'movies' if scope == 'movies' else 'tv'
    items = _scope_items(scope, provider_order=True)[:RECENT_CATALOG_LIMIT]
    _show_media(scope, items)


def show_browse_all(scope):
    scope = 'movies' if scope == 'movies' else 'tv'
    _show_media(scope, _scope_items(scope))


def show_recent_movies():
    entries = playback_history.recent_movies(limit=100)
    xbmcplugin.setContent(HANDLE, 'movies')
    _add_video_sort_methods()
    resume_points = playback_history.resume_points('movies')
    tuples = [
        _playable_tuple(item, 'movies', resume=True, resume_points=resume_points)
        for item in entries
    ]
    _send_items(tuples)
    _finish()


def _recent_show_entry(key):
    for entry in playback_history.recent_shows(limit=100):
        if entry.get('show_key') == key:
            return entry
    return None


def show_recent_tvshows():
    recent = playback_history.recent_shows(limit=100)
    summary_map = {show.get('show_key'): show for show in _load_tv_shows()}
    visible = []
    for entry in recent:
        summary = summary_map.get(entry.get('show_key', ''))
        if summary:
            visible.append((entry, summary))
    xbmcplugin.setContent(HANDLE, 'tvshows')
    _add_video_sort_methods()
    tuples = []
    for entry, summary in visible:
        title = summary.get('show_title') or entry.get('show_title') or 'TV Show'
        label = summary.get('group_title') or title
        info = {'mediatype': 'tvshow', 'title': title}
        if summary.get('year'):
            info['year'] = int(summary['year'])
        if summary.get('tvg_id'):
            info['imdbnumber'] = summary['tvg_id']
        context = [(
            'Playback options for this show...',
            _context_action('configure_playback', target='show', catalog='tv', show_key=summary['show_key']),
        )]
        tuples.append(_folder_tuple(
            label, _url('recent_show', show_key=summary['show_key']), info, context
        ))
    _send_items(tuples)
    _finish()


def _episode_sort_key(item):
    return (
        item.get('season') if item.get('season') is not None else 999999,
        item.get('episode') if item.get('episode') is not None else 999999,
        (item.get('display_title') or '').casefold(),
    )


def show_recent_show(key):
    summary = _summary_by_key(key)
    recent = _recent_show_entry(key)
    if not summary or not recent:
        xbmcgui.Dialog().ok('Appi', 'This recently played show is no longer in the cached TV catalogue.')
        _finish(cache_to_disc=False)
        return

    episodes = sorted(_load_show_episodes(key), key=_episode_sort_key)
    recent_ref = recent.get('ref')
    current_index = next((i for i, item in enumerate(episodes) if item_ref(item) == recent_ref), None)
    continuation = None
    force_resume = False
    if current_index is not None:
        if recent.get('completed') and current_index + 1 < len(episodes):
            continuation = episodes[current_index + 1]
        else:
            continuation = episodes[current_index]
            force_resume = playback_history.resume_point('tv', item_ref(continuation)) is not None

    xbmcplugin.setContent(HANDLE, 'seasons')
    tuples = []
    if continuation:
        season = continuation.get('season')
        episode = continuation.get('episode')
        prefix = 'Resume' if force_resume else 'Continue'
        label = '{}: S{:02d}E{:02d} - {}'.format(
            prefix, int(season or 0), int(episode or 0),
            continuation.get('display_title') or continuation.get('show_title') or 'Episode',
        )
        playable = _playable_tuple(continuation, 'tv', key, resume=force_resume)
        try:
            playable[1].setLabel(label)
        except Exception:
            pass
        tuples.append(playable)

    tvg_id = summary.get('tvg_id') or ''
    for season in summary.get('seasons') or []:
        info = {'mediatype': 'season', 'title': 'Season {}'.format(season), 'season': int(season)}
        if tvg_id:
            info['imdbnumber'] = tvg_id
        tuples.append(_folder_tuple(
            'Season {}'.format(season),
            _url('episodes', show_key=key, season=season),
            info,
        ))
    _send_items(tuples)
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
        directory_items.append(_folder_tuple(
            'Season {}'.format(season),
            _url('episodes', show_key=key, season=season),
            info,
        ))
    _send_items(directory_items)
    _finish()


def show_episodes(key, season):
    try:
        season_number = int(season)
    except (TypeError, ValueError):
        season_number = None
    episodes = [item for item in _load_show_episodes(key) if item.get('season') == season_number]
    episodes.sort(key=lambda item: (
        item.get('episode') if item.get('episode') is not None else 999999,
        (item.get('display_title') or '').casefold(),
    ))
    xbmcplugin.setContent(HANDLE, 'episodes')
    if hasattr(xbmcplugin, 'SORT_METHOD_EPISODE'):
        try:
            xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_EPISODE)
        except Exception:
            pass
    resume_points = playback_history.resume_points('tv')
    _send_items([
        _playable_tuple(item, 'tv', key, resume_points=resume_points)
        for item in episodes
    ])
    _finish()


def search(scope=None, query=None):
    if scope not in {'movies', 'tv', 'both'}:
        choice = xbmcgui.Dialog().select(
            'Search category', ['Movies', 'TV Shows', 'Movies and TV Shows']
        )
        if choice < 0:
            xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
            return
        scope = ('movies', 'tv', 'both')[choice]
    if query is None:
        query = xbmcgui.Dialog().input('Search', type=xbmcgui.INPUT_ALPHANUM).strip()
    else:
        query = query.strip()
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
        matches = sort_movies(matches, _int_setting('movie_sort', 0))
        _show_media('movies', matches)
        return

    show_matches = [
        show for show in _load_tv_shows()
        if needle in '{} {}'.format(show.get('show_title') or '', show.get('group_title') or '').casefold()
    ]
    show_matches = sort_shows(show_matches, _int_setting('tv_sort', 0))
    if scope == 'tv':
        _show_media('tv', show_matches)
        return

    movie_matches = [
        item for item in _load_movies()
        if needle in (item.get('display_title') or '').casefold()
        or needle in (item.get('title') or '').casefold()
    ]
    combined = [('movies', item) for item in movie_matches]
    combined.extend(('tv', show) for show in show_matches)
    combined.sort(key=lambda pair: _item_title(pair[0], pair[1]).casefold())
    _show_mixed(combined)


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
    data[key] = {
        'kind': result.get('kind', 'unknown'),
        'content_type': result.get('content_type', ''),
    }
    _save_stream_cache(data)
    return data[key]


def _configure_hls(list_item, preferences=None):
    preferences = preferences or {}
    list_item.setMimeType('application/vnd.apple.mpegurl')
    list_item.setContentLookup(False)
    mode = preferences.get('hls_mode')
    if mode is None:
        mode = _int_setting('hls_quality_mode', 1)
    try:
        mode = int(mode)
    except (TypeError, ValueError):
        mode = 1
    if mode == 0:
        return

    if not xbmc.getCondVisibility('System.HasAddon(inputstream.adaptive)'):
        _notify('InputStream Adaptive is not installed; using Kodi HLS playback', error=True)
        return

    list_item.setProperty('inputstream', 'inputstream.adaptive')
    if mode == 1:
        list_item.setProperty('inputstream.adaptive.stream_selection_type', 'ask-quality')
    elif mode == 2:
        max_kbps = preferences.get('hls_max_kbps')
        if max_kbps is None:
            max_kbps = _int_setting('hls_max_bitrate_kbps', 8000)
        try:
            max_kbps = max(250, int(max_kbps))
        except (TypeError, ValueError):
            max_kbps = 8000
        list_item.setProperty('inputstream.adaptive.stream_selection_type', 'adaptive')
        list_item.setProperty('inputstream.adaptive.chooser_bandwidth_max', str(max_kbps * 1000))


def _configure_mp4(list_item):
    list_item.setMimeType('video/mp4')
    list_item.setContentLookup(False)
    if _bool_setting('manage_mp4_buffer', True):
        kodi_cache.apply_mp4_cache(
            memory_mb=_int_setting('mp4_buffer_mb', 64),
            read_factor=_int_setting('mp4_read_factor', 4),
        )


def _subtitle_mode(preferences):
    mode = (preferences or {}).get('subtitle_mode')
    return mode if mode in {'saved', 'off', 'search'} else 'global'


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

    preferences = playback_prefs.effective(catalog_name, ref, key or '')
    list_item = xbmcgui.ListItem(
        label=item.get('display_title') or item.get('title') or '',
        path=media_url,
        offscreen=True,
    )
    _set_playback_metadata(list_item, item)
    list_item.setProperty('IsPlayable', 'true')
    _apply_resume_metadata(
        list_item, catalog_name, ref,
        force_start=(params.get('resume') == '1'),
    )

    stream = _probe_kind(catalog_name, ref, media_url)
    if stream.get('kind') == 'hls':
        _configure_hls(list_item, preferences)
    elif stream.get('kind') == 'mp4':
        _configure_mp4(list_item)

    subtitle_mode = _subtitle_mode(preferences)
    persist = _bool_setting('persist_subtitles', True)
    auto_saved = _bool_setting('auto_saved_subtitles', True)
    need_session = (
        persist
        or subtitle_mode in {'saved', 'search'}
        or (subtitle_mode == 'global' and auto_saved)
    )
    if need_session:
        saved = subtitle_store.prepare_session(catalog_name, ref, subtitle_mode=subtitle_mode)
        use_saved = (
            subtitle_mode == 'saved'
            or (subtitle_mode == 'global' and auto_saved)
        )
        if saved and use_saved:
            try:
                list_item.setSubtitles(saved)
            except Exception as exc:
                xbmc.log('Appi could not attach saved subtitles: {}'.format(exc), xbmc.LOGWARNING)

    playback_history.start_session(catalog_name, ref, item, key or '')
    xbmcplugin.setResolvedUrl(HANDLE, True, list_item)


def _dialog_select(heading, choices, preselect=0):
    try:
        return xbmcgui.Dialog().select(heading, choices, preselect=preselect)
    except TypeError:
        return xbmcgui.Dialog().select(heading, choices)


def configure_playback(params):
    target = params.get('target', 'movie')
    catalog_name = params.get('catalog', 'movies')
    ref = params.get('ref', '')
    key = params.get('show_key', '')
    if target not in {'movie', 'episode', 'show'}:
        raise ValueError('Invalid playback preference target')
    if target == 'show' and not key:
        raise ValueError('Missing TV show key')
    if target != 'show' and not ref:
        raise ValueError('Missing media reference')

    current = playback_prefs.get_target(target, ref=ref, show_key=key)
    current_hls = current.get('hls_mode')
    hls_choices = [
        'Use global HLS setting',
        'Automatic - Kodi default',
        'Ask quality before playback',
        'Limit maximum bitrate',
    ]
    hls_preselect = 0 if current_hls is None else min(3, max(1, int(current_hls) + 1))
    hls_choice = _dialog_select('HLS quality for this {}'.format('show' if target == 'show' else 'title'), hls_choices, hls_preselect)
    if hls_choice < 0:
        return

    updated = {}
    if hls_choice > 0:
        updated['hls_mode'] = hls_choice - 1
        if updated['hls_mode'] == 2:
            default_cap = str(current.get('hls_max_kbps') or _int_setting('hls_max_bitrate_kbps', 8000))
            entered = xbmcgui.Dialog().input(
                'Maximum HLS bitrate (Kbit/s)',
                defaultt=default_cap,
                type=getattr(xbmcgui, 'INPUT_NUMERIC', 1),
            ).strip()
            if not entered:
                return
            try:
                updated['hls_max_kbps'] = max(250, int(entered))
            except ValueError:
                xbmcgui.Dialog().ok('Appi', 'Maximum bitrate must be a number in Kbit/s.')
                return

    current_sub = current.get('subtitle_mode')
    subtitle_choices = [
        'Use global subtitle setting',
        'Auto-load saved subtitle',
        'Do not auto-load saved subtitle',
        'Open subtitle search after playback starts',
    ]
    subtitle_map = {1: 'saved', 2: 'off', 3: 'search'}
    reverse_sub = {'saved': 1, 'off': 2, 'search': 3}
    subtitle_choice = _dialog_select(
        'Subtitles for this {}'.format('show' if target == 'show' else 'title'),
        subtitle_choices,
        reverse_sub.get(current_sub, 0),
    )
    if subtitle_choice < 0:
        return
    if subtitle_choice in subtitle_map:
        updated['subtitle_mode'] = subtitle_map[subtitle_choice]

    playback_prefs.set_target(target, updated, ref=ref, show_key=key)
    if updated:
        _notify('Playback options saved')
    else:
        _notify('Playback options reset to global defaults')


def _run_action(params):
    action = params.get('action', 'root')
    if action == 'root':
        show_root()
    elif action == 'movies':
        show_movies()
    elif action == 'tvshows':
        show_tvshows()
    elif action == 'browse_index':
        show_browse_index(params.get('scope', 'movies'), params.get('mode', 'alpha'))
    elif action == 'browse_items':
        show_browse_items(
            params.get('scope', 'movies'),
            params.get('mode', 'alpha'),
            params.get('value', '#'),
            params.get('offset'),
        )
    elif action == 'browse_recent':
        show_browse_recent(params.get('scope', 'movies'))
    elif action == 'browse_all':
        show_browse_all(params.get('scope', 'movies'))
    elif action == 'recent_movies':
        show_recent_movies()
    elif action == 'recent_tvshows':
        show_recent_tvshows()
    elif action == 'recent_show':
        show_recent_show(params.get('show_key', ''))
    elif action == 'seasons':
        show_seasons(params.get('show_key', ''))
    elif action == 'episodes':
        show_episodes(params.get('show_key', ''), params.get('season'))
    elif action == 'search':
        search(params.get('scope'), params.get('query'))
    elif action == 'play_ref':
        play_ref(params)
    elif action == 'configure_playback':
        configure_playback(params)
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
        xbmcgui.Dialog().ok(
            'Appi error',
            'Could not open/run "{}".\n\n{}\n\nPlease report this exact message.'.format(action, detail),
        )
        if action not in {'play_ref', 'configure_playback'}:
            try:
                xbmcplugin.endOfDirectory(HANDLE, succeeded=False, cacheToDisc=False)
            except Exception:
                pass
        elif action == 'play_ref':
            try:
                xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
            except Exception:
                pass
