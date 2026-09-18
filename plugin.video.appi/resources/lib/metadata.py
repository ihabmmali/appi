import hashlib
import json
import os
import sqlite3
import time
from urllib.parse import urlencode

import xbmc
import xbmcaddon
import xbmcvfs


ADDON = xbmcaddon.Addon()
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
HELPER_ID = 'plugin.video.themoviedb.helper'
SCHEMA_VERSION = 3
DEFAULT_MAX_ITEMS = 1000


def enabled():
    value = ADDON.getSetting('metadata_enabled')
    return True if value == '' else value.lower() == 'true'


def _max_items():
    try:
        return max(100, min(5000, int(ADDON.getSetting('metadata_cache_items') or DEFAULT_MAX_ITEMS)))
    except (TypeError, ValueError):
        return DEFAULT_MAX_ITEMS


def _ensure_profile():
    if not xbmcvfs.exists(PROFILE):
        xbmcvfs.mkdirs(PROFILE)


def _db_path():
    _ensure_profile()
    return os.path.join(PROFILE, 'metadata.db')


def _connect():
    connection = sqlite3.connect(_db_path(), timeout=5)
    connection.execute('PRAGMA journal_mode=WAL')
    connection.execute('PRAGMA synchronous=NORMAL')
    connection.execute(
        'CREATE TABLE IF NOT EXISTS metadata ('
        'cache_key TEXT PRIMARY KEY, fetched_at INTEGER NOT NULL, data TEXT NOT NULL, '
        'pinned INTEGER NOT NULL DEFAULT 0)'
    )
    connection.execute(
        'CREATE TABLE IF NOT EXISTS queue ('
        'cache_key TEXT PRIMARY KEY, queued_at INTEGER NOT NULL, payload TEXT NOT NULL, '
        'pinned INTEGER NOT NULL DEFAULT 0)'
    )
    current_version = connection.execute('PRAGMA user_version').fetchone()[0]
    if current_version and current_version < SCHEMA_VERSION:
        # Versions 1 and 2 used incompatible layouts and stored a full copy of
        # show artwork/cast in every episode. Re-fetch under the normalised
        # schema instead of carrying duplication or missing columns forward.
        connection.execute('DROP TABLE metadata')
        connection.execute('DROP TABLE queue')
        connection.execute(
            'CREATE TABLE metadata ('
            'cache_key TEXT PRIMARY KEY, fetched_at INTEGER NOT NULL, data TEXT NOT NULL, '
            'pinned INTEGER NOT NULL DEFAULT 0)'
        )
        connection.execute(
            'CREATE TABLE queue ('
            'cache_key TEXT PRIMARY KEY, queued_at INTEGER NOT NULL, payload TEXT NOT NULL, '
            'pinned INTEGER NOT NULL DEFAULT 0)'
        )
    connection.execute('PRAGMA user_version={}'.format(SCHEMA_VERSION))
    return connection


def _clean_id(value):
    value = str(value or '').strip()
    return value if value.startswith('tt') and value[2:].isdigit() else ''


def lookup_payload(item, media_type=None):
    kind = item.get('kind') or media_type or ''
    is_movie = kind == 'movie' or media_type == 'movie'
    is_episode = kind == 'episode' or media_type == 'episode'
    payload = {
        'media_type': 'movie' if is_movie else ('episode' if is_episode else 'tvshow'),
        'title': (
            item.get('title') or item.get('display_title') or ''
            if is_movie else item.get('show_title') or item.get('group_title') or ''
        ),
        'year': item.get('year') or '',
        'imdb_id': _clean_id(item.get('tvg_id')),
    }
    if is_episode:
        payload['season'] = item.get('season')
        payload['episode'] = item.get('episode')
    return payload


def cache_key(payload):
    identity = '|'.join(str(payload.get(key, '') or '') for key in (
        'media_type', 'imdb_id', 'title', 'year', 'season', 'episode'
    ))
    return hashlib.sha1(identity.encode('utf-8')).hexdigest()


def show_payload(payload):
    if not payload or payload.get('media_type') not in {'episode', 'tvshow'}:
        return None
    return {
        'media_type': 'tvshow',
        'title': payload.get('title') or '',
        'year': payload.get('year') or '',
        'imdb_id': payload.get('imdb_id') or '',
    }


def encode_focus(payload):
    return json.dumps(payload, ensure_ascii=False, separators=(',', ':'))


def decode_focus(value):
    try:
        payload = json.loads(value or '')
    except (TypeError, ValueError):
        return None
    return payload if isinstance(payload, dict) and payload.get('title') else None


def load_all():
    if not enabled():
        return {}
    try:
        with _connect() as connection:
            rows = connection.execute('SELECT cache_key, data FROM metadata').fetchall()
    except sqlite3.Error as exc:
        xbmc.log('Appi metadata cache read failed: {}'.format(exc), xbmc.LOGWARNING)
        return {}
    result = {}
    for key, value in rows:
        try:
            data = json.loads(value)
        except (TypeError, ValueError):
            continue
        if isinstance(data, dict):
            result[key] = data
    return result


def get(payload, cache_map=None):
    if not enabled() or not payload:
        return None
    key = cache_key(payload)
    if cache_map is not None:
        value = cache_map.get(key)
        if payload.get('media_type') == 'episode':
            parent = cache_map.get(cache_key(show_payload(payload))) or {}
            if parent or value:
                merged = dict(parent)
                merged.update(value or {})
                return merged
        return value
    try:
        with _connect() as connection:
            row = connection.execute(
                'SELECT data FROM metadata WHERE cache_key=?', (key,)
            ).fetchone()
    except sqlite3.Error:
        return None
    value = None
    if row:
        try:
            value = json.loads(row[0])
        except (TypeError, ValueError):
            value = None
    if payload.get('media_type') == 'episode':
        parent = get(show_payload(payload)) or {}
        if parent or value:
            merged = dict(parent)
            merged.update(value or {})
            return merged
    return value


def queue_many(payloads, force=False, pinned=False):
    if not enabled():
        return 0
    queued = 0
    now = int(time.time() * 1000)
    try:
        with _connect() as connection:
            for offset, payload in enumerate(payloads):
                if not payload or not payload.get('title'):
                    continue
                key = cache_key(payload)
                cached = connection.execute(
                    'SELECT 1 FROM metadata WHERE cache_key=?', (key,)
                ).fetchone()
                if not force and cached:
                    if pinned:
                        connection.execute(
                            'UPDATE metadata SET pinned=1 WHERE cache_key=?', (key,)
                        )
                    continue
                connection.execute(
                    'INSERT OR REPLACE INTO queue('
                    'cache_key,queued_at,payload,pinned) VALUES(?,?,?,?)',
                    (key, now + offset, encode_focus(payload), 1 if pinned else 0),
                )
                queued += 1
        return queued
    except sqlite3.Error as exc:
        xbmc.log('Appi metadata batch queue failed: {}'.format(exc), xbmc.LOGWARNING)
        return 0


def queue(payload, force=False):
    return bool(queue_many([payload], force=force))


def _helper_url(payload):
    params = {
        'info': 'details',
        'tmdb_type': 'movie' if payload.get('media_type') == 'movie' else 'tv',
        'query': payload.get('title') or '',
    }
    if payload.get('year'):
        params['year'] = payload['year']
    if payload.get('imdb_id'):
        params['imdb_id'] = payload['imdb_id']
    if payload.get('media_type') == 'episode':
        if payload.get('season') is not None:
            params['season'] = payload['season']
        if payload.get('episode') is not None:
            params['episode'] = payload['episode']
        if payload.get('year'):
            params['episode_year'] = payload['year']
    return 'plugin://{}/?{}'.format(HELPER_ID, urlencode(params))


def _jsonrpc(method, params):
    request = json.dumps({
        'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params,
    }, separators=(',', ':'))
    response = json.loads(xbmc.executeJSONRPC(request) or '{}')
    if response.get('error'):
        raise RuntimeError(response['error'].get('message') or 'Kodi JSON-RPC error')
    return response.get('result') or {}


def _float(value):
    try:
        result = float(value)
        return result if 0.0 <= result <= 10.0 else None
    except (TypeError, ValueError):
        return None


def _int(value):
    try:
        return int(str(value).replace(',', '').strip())
    except (TypeError, ValueError):
        return 0


def _normalise_result(item, payload):
    properties = item.get('customproperties') or {}
    lower_props = {str(key).casefold(): value for key, value in properties.items()}
    art = item.get('art') or {}
    cast = []
    for person in (item.get('cast') or [])[:12]:
        if isinstance(person, dict) and person.get('name'):
            cast.append({
                'name': person['name'],
                'role': person.get('role') or '',
                'thumbnail': person.get('thumbnail') or '',
            })
    rating = _float(lower_props.get('imdb_rating'))
    votes = _int(lower_props.get('imdb_votes'))
    result = {
        'plot': item.get('plot') or '',
        'poster': art.get('poster') or item.get('thumbnail') or '',
        'cast': cast,
        'imdb_rating': rating,
        'imdb_votes': votes,
        'imdb_id': _clean_id(
            lower_props.get('imdb_id') or item.get('imdbnumber') or payload.get('imdb_id')
        ),
        'tmdb_id': lower_props.get('tmdb_id') or (item.get('uniqueid') or {}).get('tmdb') or '',
    }
    if payload.get('media_type') == 'episode':
        title = item.get('title') or item.get('label') or ''
        if title and title.casefold() != (payload.get('title') or '').casefold():
            result['episode_title'] = title
    return result


def _prune(connection):
    maximum = _max_items()
    connection.execute(
        'DELETE FROM metadata WHERE cache_key IN ('
        'SELECT cache_key FROM metadata WHERE pinned=0 '
        'ORDER BY fetched_at DESC LIMIT -1 OFFSET ?)',
        (maximum,),
    )


def process_one():
    if not enabled() or xbmc.Player().isPlayingVideo():
        return False
    if not xbmc.getCondVisibility('System.HasAddon({})'.format(HELPER_ID)):
        return False
    with _connect() as connection:
        row = connection.execute(
            'SELECT cache_key, payload, pinned FROM queue ORDER BY queued_at LIMIT 1'
        ).fetchone()
    if not row:
        return False
    key, encoded, pinned = row
    payload = decode_focus(encoded)
    try:
        properties = [
            'title', 'plot', 'year', 'cast', 'thumbnail', 'art',
            'imdbnumber', 'uniqueid', 'customproperties',
        ]
        request = {
            'directory': _helper_url(payload),
            'media': 'video',
            'properties': properties,
            'limits': {'start': 0, 'end': 1},
        }
        try:
            result = _jsonrpc('Files.GetDirectory', request)
        except RuntimeError as exc:
            if 'invalid' not in str(exc).casefold() or 'param' not in str(exc).casefold():
                raise
            # customproperties was added to newer JSON-RPC versions. Older Kodi
            # builds can still provide every requested field except IMDb ratings.
            request['properties'] = [
                value for value in properties if value != 'customproperties'
            ]
            result = _jsonrpc('Files.GetDirectory', request)
        files = result.get('files') or []
        if not files:
            raise RuntimeError('TMDb Helper returned no match')
        data = _normalise_result(files[0], payload)
        with _connect() as connection:
            if payload.get('media_type') == 'episode':
                parent_payload = show_payload(payload)
                parent_key = cache_key(parent_payload)
                existing = connection.execute(
                    'SELECT data,pinned FROM metadata WHERE cache_key=?', (parent_key,)
                ).fetchone()
                parent_data = {}
                parent_pinned = bool(pinned)
                if existing:
                    try:
                        parent_data = json.loads(existing[0])
                    except (TypeError, ValueError):
                        parent_data = {}
                    parent_pinned = parent_pinned or bool(existing[1])
                # Store shared show artwork/cast/IDs once. Episode rows retain
                # only their title, plot and episode-specific rating fields.
                for name in ('poster', 'cast', 'imdb_id', 'tmdb_id'):
                    if data.get(name):
                        parent_data[name] = data[name]
                connection.execute(
                    'INSERT OR REPLACE INTO metadata('
                    'cache_key,fetched_at,data,pinned) VALUES(?,?,?,?)',
                    (parent_key, int(time.time()), json.dumps(
                        parent_data, ensure_ascii=False, separators=(',', ':')
                    ), 1 if parent_pinned else 0),
                )
                data = {
                    name: data[name] for name in (
                        'episode_title', 'plot', 'imdb_rating', 'imdb_votes'
                    ) if data.get(name) not in (None, '', [], {})
                }
            connection.execute(
                'INSERT OR REPLACE INTO metadata('
                'cache_key,fetched_at,data,pinned) VALUES(?,?,?,?)',
                (key, int(time.time()), json.dumps(
                    data, ensure_ascii=False, separators=(',', ':')
                ), 1 if pinned else 0),
            )
            connection.execute('DELETE FROM queue WHERE cache_key=?', (key,))
            _prune(connection)
        return True
    except Exception as exc:
        xbmc.log('Appi metadata lookup failed: {}'.format(exc), xbmc.LOGWARNING)
        # Drop a failed request so a bad match or network outage cannot create a tight loop.
        with _connect() as connection:
            connection.execute('DELETE FROM queue WHERE cache_key=?', (key,))
        return False


def clear_all():
    for suffix in ('', '-wal', '-shm'):
        try:
            os.remove(_db_path() + suffix)
        except FileNotFoundError:
            pass


def clear_queue():
    try:
        with _connect() as connection:
            queued = connection.execute('SELECT COUNT(*) FROM queue').fetchone()[0]
            connection.execute('DELETE FROM queue')
        return int(queued or 0)
    except sqlite3.Error as exc:
        xbmc.log('Appi metadata queue clear failed: {}'.format(exc), xbmc.LOGWARNING)
        return 0


def _disk_usage():
    total = 0
    for suffix in ('', '-wal', '-shm'):
        try:
            total += os.path.getsize(_db_path() + suffix)
        except OSError:
            pass
    return total


def status():
    try:
        with _connect() as connection:
            cached = connection.execute('SELECT COUNT(*) FROM metadata').fetchone()[0]
            queued = connection.execute('SELECT COUNT(*) FROM queue').fetchone()[0]
    except sqlite3.Error:
        cached, queued = 0, 0
    return {'cached': cached, 'queued': queued, 'bytes': _disk_usage(), 'helper': bool(
        xbmc.getCondVisibility('System.HasAddon({})'.format(HELPER_ID))
    )}
