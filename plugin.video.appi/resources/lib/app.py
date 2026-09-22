import hashlib
import sys
import time
import traceback
from datetime import datetime
from urllib.error import HTTPError
from urllib.parse import parse_qsl, urlencode

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

from . import cache
from . import favorites
from . import kodi_cache
from . import kodi_status
from . import metadata
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
        for source_index, item in enumerate(items):
            item['source_index'] = source_index
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


def clear_data(scope):
    choices = {
        'movies': (
            'Clear Movie List Cache?',
            'The cached movie catalogue and movie stream checks will be deleted. Your source URL is kept.',
        ),
        'tv': (
            'Clear TV Show List Cache?',
            'The cached TV index, episode data and TV stream checks will be deleted. Your source URL is kept.',
        ),
        'catalogs': (
            'Clear Both List Caches?',
            'The cached movie and TV catalogues and stream checks will be deleted. Your source URLs are kept.',
        ),
        'subtitles': (
            'Clear Saved Subtitles?',
            'All external subtitle files saved by Appi will be deleted.',
        ),
        'recent': (
            'Clear Recent Media?',
            'Recently Played items and their resume positions will be deleted.',
        ),
        'metadata': (
            'Clear Metadata Cache?',
            'Cached plots, posters, cast, episode names and IMDb ratings will be deleted.',
        ),
    }
    if scope not in choices:
        raise ValueError('Unknown clear-data scope: {}'.format(scope))
    heading, message = choices[scope]
    if not xbmcgui.Dialog().yesno(heading, message):
        return False

    if scope in {'movies', 'catalogs'}:
        cache.remove('movies')
        _clear_stream_cache('movies')
    if scope in {'tv', 'catalogs'}:
        cache.remove('tv_shows')
        cache.remove('tv')
        cache.remove_prefix('tv_show_')
        _clear_stream_cache('tv')
    if scope == 'subtitles':
        subtitle_store.clear_all()
    if scope == 'recent':
        playback_history.clear_all()
    if scope == 'metadata':
        metadata.clear_all()
    _notify('Data cleared')
    return True


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


def _year_label(value, year):
    value = value or ''
    if not year:
        return value
    suffix = ' ({})'.format(year)
    return value if suffix in value else value + suffix


def _decorate_provider_order(items):
    result = []
    for index, source in enumerate(items):
        item = dict(source)
        source_index = item.get('source_index', index)
        item['source_index'] = source_index
        result.append(item)
    return result


def _directory_video_info(item, media_type=None):
    kind = item.get('kind')
    info = {'mediatype': media_type or ('movie' if kind == 'movie' else 'episode')}
    if kind == 'movie':
        plain_title = item.get('title') or item.get('display_title') or ''
        info['title'] = _year_label(plain_title, item.get('year'))
        info['sorttitle'] = plain_title
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


def _metadata_payload(item, media_type=None):
    return metadata.lookup_payload(item, media_type=media_type)


def _metadata_context(payload):
    return (
        'Fetch / refresh metadata',
        _context_action(
            'fetch_metadata',
            media_type=payload.get('media_type'),
            title=payload.get('title'),
            year=payload.get('year'),
            imdb_id=payload.get('imdb_id'),
            season=payload.get('season'),
            episode=payload.get('episode'),
        ),
    )


def _download_context(item, catalog_name, key=None):
    return (
        'Generate FFmpeg download script',
        _context_action(
            'download_ref', catalog=catalog_name, ref=item_ref(item), show_key=key
        ),
    )


def _remove_recent_context(catalog_name, item=None, show_key=None):
    return (
        'Remove from Recently Played',
        _context_action(
            'remove_recent', catalog=catalog_name,
            ref=item_ref(item) if item else None, show_key=show_key,
        ),
    )


def _favorite_context(kind, key, item, favorite_keys=None):
    enabled = key in favorite_keys if favorite_keys is not None else favorites.contains(kind, key)
    return (
        'Remove from Appi Favorites' if enabled else 'Add to Appi Favorites',
        _context_action(
            'set_favorite', kind=kind, key=key,
            enabled='0' if enabled else '1',
        ),
    )


def _metadata_batch_context(label=None, **params):
    return (
        label or 'Fetch metadata for everything in this folder',
        _context_action('fetch_metadata_batch', **params),
    )


def _season_watched_context(show_key, season):
    return (
        'Mark season as watched',
        _context_action('set_season_watched', show_key=show_key, season=season),
    )


def _apply_metadata(list_item, payload, data):
    if not payload:
        return
    try:
        list_item.setProperty('Appi.MetadataLookup', metadata.encode_focus(payload))
    except Exception:
        pass
    if not data:
        return
    poster = data.get('poster') or ''
    if poster:
        try:
            list_item.setArt({'poster': poster, 'thumb': poster})
        except Exception:
            pass
    try:
        tag = list_item.getVideoInfoTag()
    except Exception:
        return
    plot_details = []
    if data.get('imdb_rating') is not None:
        plot_details.append('IMDb: {:.1f}/10'.format(float(data['imdb_rating'])))
    if data.get('directors'):
        plot_details.append('Director: {}'.format(', '.join(data['directors'])))
    cast_names = [person.get('name') for person in (data.get('cast') or []) if person.get('name')]
    if cast_names:
        plot_details.append('Cast: {}'.format(', '.join(cast_names[:8])))
    display_plot = '\n'.join(plot_details)
    if data.get('plot'):
        display_plot += ('\n\n' if display_plot else '') + data['plot']
    if display_plot:
        try:
            tag.setPlot(display_plot)
        except Exception:
            pass
    if data.get('episode_title') and payload.get('media_type') == 'episode':
        try:
            tag.setTitle(data['episode_title'])
        except Exception:
            pass
    rating = data.get('imdb_rating')
    if rating is not None:
        try:
            tag.setRating(float(rating), int(data.get('imdb_votes') or 0), 'imdb', True)
        except Exception:
            pass
    actors = []
    for order, person in enumerate(data.get('cast') or []):
        try:
            actors.append(xbmc.Actor(
                person.get('name') or '',
                person.get('role') or '',
                order,
                person.get('thumbnail') or '',
            ))
        except Exception:
            continue
    if actors:
        try:
            tag.setCast(actors)
        except Exception:
            pass
    if data.get('directors'):
        try:
            tag.setDirectors(data['directors'])
        except Exception:
            pass


def _episode_label(item, data=None):
    if data and data.get('episode_title'):
        season = item.get('season')
        episode = item.get('episode')
        if season is not None and episode is not None:
            return 'S{:02d}E{:02d} - {}'.format(
                int(season), int(episode), data['episode_title']
            )
        return data['episode_title']
    return item.get('display_title') or item.get('show_title') or ''


def _set_playback_metadata(list_item, item, enriched=None):
    tag = list_item.getVideoInfoTag()
    kind = item.get('kind')
    if kind == 'movie':
        tag.setMediaType('movie')
        tag.setTitle(item.get('title') or item.get('display_title') or '')
    else:
        tag.setMediaType('episode')
        tag.setTitle((enriched or {}).get('episode_title') or item.get('display_title') or '')
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
    _apply_metadata(list_item, _metadata_payload(item), enriched)


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
    item, catalog_name, key=None, label_suffix='', metadata_cache=None,
    recent=False, favorite_keys=None,
):
    payload = _metadata_payload(item)
    enriched = metadata.get(payload, metadata_cache)
    label = _year_label(
        _episode_label(item, enriched) if item.get('kind') == 'episode'
        else item.get('display_title') or item.get('title') or '',
        item.get('year'),
    )
    display_label = label + label_suffix
    list_item = xbmcgui.ListItem(label=display_label, offscreen=True)
    info = _directory_video_info(item)
    info['title'] = display_label
    list_item.setInfo('video', info)
    _apply_metadata(list_item, payload, enriched)
    list_item.setProperty('IsPlayable', 'true')
    ref = item_ref(item)
    target = 'movie' if catalog_name == 'movies' else 'episode'
    context = []
    if catalog_name == 'movies':
        context.append(_favorite_context('movie', ref, item, favorite_keys))
    context.extend([
        ('Playback options...', _context_action(
            'configure_playback', target=target, catalog=catalog_name, ref=ref, show_key=key
        )),
        _download_context(item, catalog_name, key),
        _metadata_context(payload),
    ])
    if recent:
        context.append(_remove_recent_context(catalog_name, item=item))
    _add_context(list_item, context)
    return (
        _play_ref_url(catalog_name, ref, key),
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
        ('SORT_METHOD_UNSORTED', 'SORT_METHOD_NONE'),
        ('SORT_METHOD_TITLE_IGNORE_THE', 'SORT_METHOD_TITLE'),
        ('SORT_METHOD_VIDEO_YEAR', 'SORT_METHOD_YEAR'),
    ]
    for names in candidates:
        method = next((getattr(xbmcplugin, name) for name in names if hasattr(xbmcplugin, name)), None)
        if method is None:
            continue
        try:
            xbmcplugin.addSortMethod(HANDLE, method, '%T', '')
        except TypeError:
            xbmcplugin.addSortMethod(HANDLE, method)
        except Exception:
            pass


def _scope_items(scope, provider_order=False):
    if scope == 'movies':
        items = _decorate_provider_order(_load_movies())
        return items if provider_order else sort_movies(items, _int_setting('movie_sort', 0))
    items = _decorate_provider_order(_load_tv_shows())
    return items if provider_order else sort_shows(items, _int_setting('tv_sort', 0))


def _play_ref_url(catalog_name, ref, key=None):
    return _url('play_ref', catalog=catalog_name, ref=ref, show_key=key)


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
    metadata_cache = metadata.load_all()
    favorite_keys = favorites.keys('movie' if scope == 'movies' else 'show')
    tuples = []
    for item in items:
        if scope == 'movies':
            tuples.append(_playable_tuple(
                item,
                'movies',
                label_suffix=' [Movie]' if mixed else '',
                metadata_cache=metadata_cache,
                favorite_keys=favorite_keys,
            ))
        else:
            tuples.append(_show_tuple(
                item,
                label_suffix=' [TV Show]' if mixed else '',
                metadata_cache=metadata_cache,
                favorite_keys=favorite_keys,
            ))
    _send_items(tuples)
    _finish()


def _show_mixed(items):
    xbmcplugin.setContent(HANDLE, 'files')
    _add_video_sort_methods()
    metadata_cache = metadata.load_all()
    movie_favorites = favorites.keys('movie')
    show_favorites = favorites.keys('show')
    tuples = []
    for scope, item in items:
        if scope == 'movies':
            tuples.append(_playable_tuple(
                item, 'movies', label_suffix=' [Movie]',
                metadata_cache=metadata_cache,
                favorite_keys=movie_favorites,
            ))
        else:
            tuples.append(_show_tuple(
                item, label_suffix=' [TV Show]', metadata_cache=metadata_cache,
                favorite_keys=show_favorites,
            ))
    _send_items(tuples)
    _finish()


def show_root():
    entries = [
        _folder_tuple(
            'Movies', _url('movies'), context_items=[
                _metadata_batch_context(scope='movies', mode='all')
            ],
        ),
        _folder_tuple(
            'TV Shows', _url('tvshows'), context_items=[
                _metadata_batch_context(scope='tv', mode='all')
            ],
        ),
        _folder_tuple('Search', _url('search')),
        _folder_tuple(
            'Recently Played Movies', _url('recent_movies', page=1),
            context_items=[_metadata_batch_context(
                'Fetch metadata for all Recently Played Movies',
                scope='movies', mode='recent_played',
            )],
        ),
        _folder_tuple(
            'Recently Played TV Shows', _url('recent_tvshows', page=1),
            context_items=[_metadata_batch_context(
                'Fetch metadata for all Recently Played TV Shows',
                scope='tv', mode='recent_played',
            )],
        ),
        _folder_tuple('Favorite Movies', _url('favorite_movies')),
        _folder_tuple('Favorite TV Shows', _url('favorite_tvshows')),
        _folder_tuple('Settings', _url('settings')),
    ]
    _send_items(entries)
    # Root context menus are release functionality, not static catalogue data.
    # Do not let Kodi reuse an older cached ListItem that lacks a newly added
    # folder action after an add-on upgrade.
    _finish(cache_to_disc=False)


def show_favorite_movies():
    current = {item_ref(item): item for item in _load_movies()}
    items = [
        current[entry['key']] for entry in favorites.entries('movie')
        if entry.get('key') in current
    ]
    _show_media('movies', items)


def show_favorite_tvshows():
    current = {show.get('show_key'): show for show in _load_tv_shows()}
    items = [
        current[entry['key']] for entry in favorites.entries('show')
        if entry.get('key') in current
    ]
    _show_media('tv', items)


def _show_browse_root(scope):
    noun = 'Movies' if scope == 'movies' else 'TV Shows'
    entries = [
        _folder_tuple('Browse A-Z', _url('browse_index', scope=scope, mode='alpha')),
        _folder_tuple('Browse by Year', _url('browse_index', scope=scope, mode='year')),
        _folder_tuple(
            'Recently Added (first {} in provider order)'.format(RECENT_CATALOG_LIMIT),
            _url('browse_recent', scope=scope),
            context_items=[_metadata_batch_context(scope=scope, mode='recent')],
        ),
        _folder_tuple(
            'All {} (may load slowly)'.format(noun),
            _url('browse_all', scope=scope, order='provider'),
            context_items=[_metadata_batch_context(scope=scope, mode='all')],
        ),
    ]
    _send_items(entries)
    _finish()


def show_movies():
    _show_browse_root('movies')


def show_tvshows():
    _show_browse_root('tv')


def _show_tuple(show, label_suffix='', metadata_cache=None, favorite_keys=None):
    title = show.get('show_title') or show.get('group_title') or 'TV Show'
    label = _year_label(show.get('group_title') or title, show.get('year'))
    display_label = label + label_suffix
    info = {'mediatype': 'tvshow', 'title': display_label, 'sorttitle': title}
    if show.get('year'):
        info['year'] = int(show['year'])
    if show.get('tvg_id'):
        info['imdbnumber'] = show['tvg_id']
    payload = _metadata_payload(show, media_type='tvshow')
    context = [_favorite_context('show', show['show_key'], show, favorite_keys), (
        'Playback options for this show...',
        _context_action('configure_playback', target='show', catalog='tv', show_key=show['show_key']),
    ), _metadata_context(payload), _metadata_batch_context(show_key=show['show_key'])]
    result = _folder_tuple(
        display_label, _url('seasons', show_key=show['show_key']), info, context
    )
    _apply_metadata(result[1], payload, metadata.get(payload, metadata_cache))
    return result


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
            context_items=[_metadata_batch_context(
                scope=scope, mode=mode, value=label
            )],
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
                context_items=[_metadata_batch_context(
                    scope=scope, mode=mode, value=value, offset=start
                )],
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
    _show_media(scope, _scope_items(scope, provider_order=True))


def show_recent_movies():
    entries = _decorate_provider_order(playback_history.recent_movies(limit=100))
    xbmcplugin.setContent(HANDLE, 'movies')
    _add_video_sort_methods()
    metadata_cache = metadata.load_all()
    favorite_keys = favorites.keys('movie')
    tuples = []
    for item in entries:
        playable = _playable_tuple(
            item, 'movies',
            metadata_cache=metadata_cache, recent=True,
            favorite_keys=favorite_keys,
        )
        _add_context(playable[1], [_metadata_batch_context(
            'Fetch metadata for all Recently Played Movies',
            scope='movies', mode='recent_played',
        )])
        tuples.append(playable)
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
    metadata_cache = metadata.load_all()
    favorite_keys = favorites.keys('show')
    for entry, summary in visible:
        title = summary.get('show_title') or entry.get('show_title') or 'TV Show'
        label = _year_label(summary.get('group_title') or title, summary.get('year'))
        info = {'mediatype': 'tvshow', 'title': label, 'sorttitle': title}
        if summary.get('year'):
            info['year'] = int(summary['year'])
        if summary.get('tvg_id'):
            info['imdbnumber'] = summary['tvg_id']
        payload = _metadata_payload(summary, media_type='tvshow')
        context = [_favorite_context('show', summary['show_key'], summary, favorite_keys), (
            'Playback options for this show...',
            _context_action('configure_playback', target='show', catalog='tv', show_key=summary['show_key']),
        ), _metadata_context(payload), _metadata_batch_context(
            'Fetch metadata for this entire show', show_key=summary['show_key']
        ), _metadata_batch_context(
            'Fetch metadata for all Recently Played TV Shows',
            scope='tv', mode='recent_played',
        ),
            _remove_recent_context('tv', show_key=summary['show_key'])]
        result = _folder_tuple(
            label, _url('recent_show', show_key=summary['show_key']), info, context
        )
        _apply_metadata(result[1], payload, metadata.get(payload, metadata_cache))
        tuples.append(result)
    _send_items(tuples)
    _finish()


def _episode_sort_key(item):
    return (
        item.get('season') if item.get('season') is not None else 999999,
        item.get('episode') if item.get('episode') is not None else 999999,
        (item.get('display_title') or '').casefold(),
    )


def _native_episode_status(key, item):
    return kodi_status.details(_play_ref_url('tv', item_ref(item), key))


def _next_episode_for_show(key, after_ref='', after_completed=False):
    episodes = sorted(_load_show_episodes(key), key=_episode_sort_key)
    if not episodes:
        return None
    start = 0
    if after_ref:
        index = next((i for i, item in enumerate(episodes) if item_ref(item) == after_ref), None)
        if index is not None:
            if after_completed:
                start = index + 1
            else:
                status = _native_episode_status(key, episodes[index])
                if status['resume'] > 0:
                    return episodes[index]
                start = index + 1 if status['available'] and status['playcount'] > 0 else index
    for item in episodes[start:]:
        status = _native_episode_status(key, item)
        if not status['available'] or status['playcount'] <= 0:
            return item
    return None


def show_recent_show(key):
    summary = _summary_by_key(key)
    recent = _recent_show_entry(key)
    if not summary or not recent:
        xbmcgui.Dialog().ok('Appi', 'This recently played show is no longer in the cached TV catalogue.')
        _finish(cache_to_disc=False)
        return

    recent_ref = recent.get('ref')
    continuation = _next_episode_for_show(key, recent_ref)
    force_resume = bool(continuation and _native_episode_status(key, continuation)['resume'] > 0)

    xbmcplugin.setContent(HANDLE, 'seasons')
    metadata_cache = metadata.load_all()
    tuples = []
    if continuation:
        season = continuation.get('season')
        episode = continuation.get('episode')
        prefix = 'Resume' if force_resume else 'Continue'
        label = '{}: S{:02d}E{:02d} - {}'.format(
            prefix, int(season or 0), int(episode or 0),
            continuation.get('display_title') or continuation.get('show_title') or 'Episode',
        )
        playable = _playable_tuple(
            continuation, 'tv', key,
            metadata_cache=metadata_cache, recent=True,
        )
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
            [
                _season_watched_context(key, season),
                _metadata_batch_context(show_key=key, season=season),
            ],
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
            [
                _season_watched_context(key, season),
                _metadata_batch_context(show_key=key, season=season),
            ],
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
    metadata_cache = metadata.load_all()
    _send_items([
        _playable_tuple(
            item, 'tv', key, metadata_cache=metadata_cache,
        )
        for item in episodes
    ])
    _finish()


def search(scope=None, query=None):
    if scope not in {'movies', 'tv', 'both'}:
        choice = xbmcgui.Dialog().select(
            'Search category', ['Movies and TV Shows', 'Movies', 'TV Shows']
        )
        if choice < 0:
            xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
            return
        scope = ('both', 'movies', 'tv')[choice]
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
            item for item in _scope_items('movies', provider_order=True)
            if needle in (item.get('display_title') or '').casefold()
            or needle in (item.get('title') or '').casefold()
        ]
        matches = sort_movies(matches, _int_setting('movie_sort', 0))
        _show_media('movies', matches)
        return

    show_matches = [
        show for show in _scope_items('tv', provider_order=True)
        if needle in '{} {}'.format(show.get('show_title') or '', show.get('group_title') or '').casefold()
    ]
    show_matches = sort_shows(show_matches, _int_setting('tv_sort', 0))
    if scope == 'tv':
        _show_media('tv', show_matches)
        return

    movie_matches = [
        item for item in _scope_items('movies', provider_order=True)
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

    # Kodi uses this side-effect-free existence probe before reading status for
    # plugin URLs through Files.GetFileDetails. Do not create a recent session,
    # probe the provider, or queue metadata for this internal request.
    if params.get('kodi_action') == 'check_exists':
        list_item = xbmcgui.ListItem(path=media_url, offscreen=True)
        _set_playback_metadata(list_item, item)
        list_item.setProperty('IsPlayable', 'true')
        xbmcplugin.setResolvedUrl(HANDLE, True, list_item)
        return

    preferences = playback_prefs.effective(catalog_name, ref, key or '')
    lookup = _metadata_payload(item)
    enriched = metadata.get(lookup)
    # Queue a cache miss without waiting for network access. Whether the service
    # pauses metadata processing during playback is user-configurable.
    if not enriched:
        metadata.queue(lookup)
    list_item = xbmcgui.ListItem(
        label=_episode_label(item, enriched) if item.get('kind') == 'episode'
        else item.get('display_title') or item.get('title') or '',
        path=media_url,
        offscreen=True,
    )
    _set_playback_metadata(list_item, item, enriched)
    list_item.setProperty('IsPlayable', 'true')
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


def fetch_metadata(params):
    payload = {
        'media_type': params.get('media_type') or 'movie',
        'title': params.get('title') or '',
        'year': params.get('year') or '',
        'imdb_id': params.get('imdb_id') or '',
    }
    for name in ('season', 'episode'):
        if params.get(name) not in (None, ''):
            try:
                payload[name] = int(params[name])
            except (TypeError, ValueError):
                pass
    status = metadata.status()
    if not status['helper']:
        xbmcgui.Dialog().ok(
            'Appi metadata',
            'TMDb Helper is not installed. Install and configure plugin.video.themoviedb.helper, then try again.',
        )
        return
    if metadata.queue(payload, force=True):
        _notify('Metadata queued. It will appear when this list is next opened.')
    else:
        _notify('Metadata could not be queued', error=True)


def _metadata_payloads_for_shows(shows, season=None):
    for show in shows:
        yield _metadata_payload(show, media_type='tvshow')
        key = show.get('show_key') or ''
        if not key:
            continue
        for episode in _load_show_episodes(key):
            if season is not None and episode.get('season') != season:
                continue
            yield _metadata_payload(episode, media_type='episode')


def _metadata_batch_selection(params):
    key = params.get('show_key') or ''
    if key:
        show = _summary_by_key(key)
        if not show:
            return 0, iter(())
        season = None
        if params.get('season') not in (None, ''):
            try:
                season = int(params['season'])
            except (TypeError, ValueError):
                season = None
        episode_count = sum(
            1 for item in _load_show_episodes(key)
            if season is None or item.get('season') == season
        )
        return 1 + episode_count, _metadata_payloads_for_shows([show], season)

    scope = 'movies' if params.get('scope') == 'movies' else 'tv'
    mode = params.get('mode') or 'all'
    if mode == 'recent_played':
        if scope == 'movies':
            items = _decorate_provider_order(playback_history.recent_movies(limit=100))
        else:
            summary_map = {show.get('show_key'): show for show in _load_tv_shows()}
            items = [
                summary_map[entry.get('show_key')]
                for entry in playback_history.recent_shows(limit=100)
                if entry.get('show_key') in summary_map
            ]
    elif mode == 'recent':
        items = _scope_items(scope, provider_order=True)[:RECENT_CATALOG_LIMIT]
    elif mode in {'alpha', 'year'} and params.get('value') is not None:
        items = _subset_for_index(scope, mode, params.get('value', '#'))
        if params.get('offset') not in (None, ''):
            try:
                start = max(0, int(params['offset']))
            except (TypeError, ValueError):
                start = 0
            items = items[start:start + BROWSE_BUCKET_LIMIT]
    else:
        items = _scope_items(scope, provider_order=True)

    if scope == 'movies':
        return len(items), (
            _metadata_payload(item, media_type='movie') for item in items
        )
    total = sum(1 + int(show.get('episode_count') or 0) for show in items)
    return total, _metadata_payloads_for_shows(items)


def fetch_metadata_batch(params):
    status = metadata.status()
    if not status['helper']:
        xbmcgui.Dialog().ok(
            'Appi metadata',
            'TMDb Helper is not installed. Install and configure '
            'plugin.video.themoviedb.helper, then try again.',
        )
        return
    total, payloads = _metadata_batch_selection(params)
    if not total:
        _notify('This folder contains no media to queue', error=True)
        return
    if (ADDON.getSetting('metadata_confirm_bulk') or '').lower() == 'true':
        message = (
            'Queue metadata for {:,} titles?\n\n'
            'Lookups run one at a time in the background and may take a long '
            'time for large folders.'
        ).format(total)
        if not xbmcgui.Dialog().yesno('Appi batch metadata', message):
            return
    queued = metadata.queue_many(payloads, pinned=True)
    _notify('{:,} metadata lookups queued'.format(queued))


def queue_download(params):
    from . import downloads
    catalog_name = params.get('catalog', '')
    ref = params.get('ref', '')
    key = params.get('show_key') or None
    if catalog_name not in {'movies', 'tv'} or not ref:
        raise ValueError('Invalid download target')
    item = _find_by_ref(catalog_name, ref, key)
    if not item:
        xbmcgui.Dialog().ok(
            'Appi download',
            'This item is no longer present in the cached catalogue.',
        )
        return
    try:
        result = downloads.generate(catalog_name, item, key or '')
    except Exception as exc:
        xbmcgui.Dialog().ok('Appi download script', str(exc))
        return
    if result['created']:
        _notify('FFmpeg download script created')
    else:
        _notify('A download script for this item already exists')


def show_download_status():
    from . import downloads
    value = downloads.status()
    details = (
        'Scripts currently in watch folder: {scripts}\n\n'
        'Kodi script/output folder:\n{folder}'
    ).format(
        scripts=value['scripts'], folder=value['folder'],
    )
    if value.get('error'):
        details += '\n\nFolder read error:\n' + value['error']
    details += (
        '\n\nEach script writes its MP4 beside the script itself. Appi only '
        'creates scripts; actual progress and failures are managed by the '
        'external watcher and FFmpeg.'
    )
    xbmcgui.Dialog().ok('Appi download scripts', details)


def show_metadata_status():
    status = metadata.status()
    helper = 'installed' if status['helper'] else 'not installed'
    size = _format_bytes(status.get('bytes', 0))
    last_activity = (
        datetime.fromtimestamp(status['last_finished']).strftime('%Y-%m-%d %H:%M:%S')
        if status.get('last_finished') else 'None yet'
    )
    oldest_age = 'None'
    if status.get('oldest_queued'):
        seconds = max(0, int(time.time() - status['oldest_queued'] / 1000.0))
        oldest_age = '{}m {}s'.format(seconds // 60, seconds % 60)
    last_item = status.get('last_title') or 'None yet'
    if status.get('last_result'):
        last_item += ' ({})'.format(status['last_result'])
    detail = (
        'TMDb Helper: {helper}\n'
        'Worker: {worker}\n'
        'Current item: {current}\n'
        'Queued lookups: {queued} ({pinned_queue} bulk-pinned)\n'
        'Oldest queued: {oldest}\n'
        'Successful lookups: {success}\n'
        'Failed/no-match lookups: {failed}\n'
        'Last item: {last_item}\n'
        'Last activity: {last_activity}\n\n'
        'Cached rows: {cached} ({pinned_cache} bulk-pinned)\n'
        'Movies / shows / episodes: {movies} / {shows} / {episodes}\n'
        'Legacy unclassified rows: {unknown}\n'
        'Automatic cache limit: {limit}\n'
        'Disk usage: {size}\n'
        'Pause during playback: {pause}'
    ).format(
        helper=helper, worker=status['worker_state'],
        current=status.get('current_title') or 'None', queued=status['queued'],
        pinned_queue=status['pinned_queued'], oldest=oldest_age,
        success=status['successful'], failed=status['failed'],
        last_item=last_item, last_activity=last_activity,
        cached=status['cached'], pinned_cache=status['pinned_cached'],
        movies=status['movie_cached'], shows=status['show_cached'],
        episodes=status['episode_cached'], unknown=status['unknown_cached'],
        limit=status['max_items'], size=size,
        pause='yes' if status['pause_playback'] else 'no',
    )
    if status.get('last_error'):
        detail += '\n\nLast failure:\n' + status['last_error']
    detail += (
        '\n\nIMDb ratings require the OMDb ratings source to be configured in TMDb Helper.'
    )
    xbmcgui.Dialog().ok(
        'Appi metadata', detail,
    )


def _format_bytes(value):
    size = float(value or 0)
    for unit in ('bytes', 'KB', 'MB', 'GB'):
        if size < 1024 or unit == 'GB':
            return '{} {}'.format(int(size) if unit == 'bytes' else '{:.1f}'.format(size), unit)
        size /= 1024


def clear_metadata_queue():
    count = metadata.clear_queue()
    _notify('Stopped and cleared {:,} queued metadata lookups'.format(count))


def remove_recent(params):
    catalog_name = params.get('catalog', '')
    if catalog_name == 'movies':
        removed = playback_history.remove('movies', params.get('ref', ''))
    elif catalog_name == 'tv' and params.get('show_key') and not params.get('ref'):
        removed = playback_history.remove_show(params['show_key'])
    elif catalog_name == 'tv':
        removed = playback_history.remove('tv', params.get('ref', ''))
    else:
        raise ValueError('Invalid recently played target')
    _notify('Removed from Recently Played' if removed else 'Item was not in Recently Played')
    xbmc.executebuiltin('Container.Refresh')


def set_season_watched(params):
    key = params.get('show_key') or ''
    try:
        season = int(params.get('season'))
    except (TypeError, ValueError):
        raise ValueError('Invalid season')
    episodes = [
        item for item in _load_show_episodes(key)
        if item.get('season') == season
    ]
    if not episodes:
        _notify('No episodes were found for this season', error=True)
        return
    progress = xbmcgui.DialogProgress()
    progress.create('Appi', 'Marking Season {} as watched...'.format(season))
    updated = 0
    attempted = 0
    canceled = False
    try:
        total = len(episodes)
        for index, item in enumerate(episodes):
            if progress.iscanceled():
                canceled = True
                break
            attempted += 1
            if kodi_status.set_watched(
                _play_ref_url('tv', item_ref(item), key), True
            ):
                updated += 1
            progress.update(
                int(((index + 1) * 100) / total),
                'Marked {:,} of {:,} episodes'.format(updated, total),
            )
    finally:
        progress.close()
    failed = attempted - updated
    if canceled:
        _notify('Stopped after marking {:,} episodes as watched'.format(updated))
    elif failed:
        _notify(
            'Marked {:,} episodes; {:,} could not be updated'.format(updated, failed),
            error=True,
        )
    else:
        _notify('Marked all {:,} episodes as watched'.format(updated))
    xbmc.executebuiltin('Container.Refresh')


def set_favorite(params):
    kind = params.get('kind') or ''
    key = params.get('key') or ''
    if kind == 'movie':
        item = _find_by_ref('movies', key)
    elif kind == 'show':
        item = _summary_by_key(key)
    else:
        item = None
    if not item:
        _notify('Favorite target is no longer present in the catalogue', error=True)
        return
    enabled = params.get('enabled') != '0'
    favorites.set_favorite(kind, key, item, enabled)
    _notify('Added to Appi Favorites' if enabled else 'Removed from Appi Favorites')
    xbmc.executebuiltin('Container.Refresh')


def play_next(params):
    key = params.get('show_key') or ''
    item = _next_episode_for_show(
        key, params.get('after_ref') or '', params.get('completed') == '1'
    )
    if not item:
        _notify('No unwatched next episode is available')
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    play_ref({
        'catalog': 'tv', 'ref': item_ref(item), 'show_key': key,
    })


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
    elif action == 'favorite_movies':
        show_favorite_movies()
    elif action == 'favorite_tvshows':
        show_favorite_tvshows()
    elif action == 'seasons':
        show_seasons(params.get('show_key', ''))
    elif action == 'episodes':
        show_episodes(params.get('show_key', ''), params.get('season'))
    elif action == 'search':
        search(params.get('scope'), params.get('query'))
    elif action == 'play_ref':
        play_ref(params)
    elif action == 'play_next':
        play_next(params)
    elif action == 'configure_playback':
        configure_playback(params)
    elif action == 'fetch_metadata':
        fetch_metadata(params)
    elif action == 'fetch_metadata_batch':
        fetch_metadata_batch(params)
    elif action == 'download_ref':
        queue_download(params)
    elif action == 'download_status':
        show_download_status()
    elif action == 'metadata_status':
        show_metadata_status()
    elif action == 'clear_metadata_queue':
        clear_metadata_queue()
    elif action == 'remove_recent':
        remove_recent(params)
    elif action == 'set_season_watched':
        set_season_watched(params)
    elif action == 'set_favorite':
        set_favorite(params)
    elif action == 'refresh_movies':
        refresh_movies()
        xbmc.executebuiltin('Container.Update({})'.format(BASE_URL))
    elif action == 'refresh_tv':
        refresh_tv()
        xbmc.executebuiltin('Container.Update({})'.format(BASE_URL))
    elif action == 'refresh_all':
        refresh_all()
        xbmc.executebuiltin('Container.Update({})'.format(BASE_URL))
    elif action == 'clear_data':
        clear_data(params.get('scope', ''))
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
