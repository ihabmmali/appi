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
SCHEMA_VERSION = 2
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
        'cache_key TEXT PRIMARY KEY, fetched_at INTEGER NOT NULL, data TEXT NOT NULL)'
    )
    connection.execute(
        'CREATE TABLE IF NOT EXISTS queue ('
        'cache_key TEXT PRIMARY KEY, queued_at INTEGER NOT NULL, payload TEXT NOT NULL, '
        'priority INTEGER NOT NULL DEFAULT 0)'
    )
    columns = {
        row[1] for row in connection.execute('PRAGMA table_info(queue)').fetchall()
    }
    if 'priority' not in columns:
        connection.execute(
            'ALTER TABLE queue ADD COLUMN priority INTEGER NOT NULL DEFAULT 0'
        )
    current_version = connection.execute('PRAGMA user_version').fetchone()[0]
    if current_version and current_version < SCHEMA_VERSION:
        # Metadata fetched by 0.7.x did not include directors and could miss
        # Kodi's structured IMDb ratings. Re-fetch it rather than carrying an
        # incomplete cache into the live browser.
        connection.execute('DELETE FROM metadata')
        connection.execute('DELETE FROM queue')
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
        return cache_map.get(key)
    try:
        with _connect() as connection:
            row = connection.execute(
                'SELECT data FROM metadata WHERE cache_key=?', (key,)
            ).fetchone()
    except sqlite3.Error:
        return None
    if not row:
        return None
    try:
        return json.loads(row[0])
    except (TypeError, ValueError):
        return None


def get_many(payloads):
    """Return cached metadata keyed by payload cache key in one SQLite read."""
    if not enabled():
        return {}
    keys = [cache_key(payload) for payload in payloads if payload]
    if not keys:
        return {}
    placeholders = ','.join('?' for _ in keys)
    try:
        with _connect() as connection:
            rows = connection.execute(
                'SELECT cache_key, data FROM metadata WHERE cache_key IN ({})'.format(
                    placeholders
                ),
                keys,
            ).fetchall()
    except sqlite3.Error:
        return {}
    result = {}
    for key, encoded in rows:
        try:
            value = json.loads(encoded)
        except (TypeError, ValueError):
            continue
        if isinstance(value, dict):
            result[key] = value
    return result


def queue_many(payloads, force=False, priority=0):
    """Queue a bounded viewport in one transaction without network activity."""
    if not enabled():
        return 0
    unique = []
    seen = set()
    for payload in payloads:
        if not payload or not payload.get('title'):
            continue
        key = cache_key(payload)
        if key in seen:
            continue
        seen.add(key)
        unique.append((key, payload))
    if not unique:
        return 0
    queued = 0
    now = int(time.time() * 1000)
    try:
        with _connect() as connection:
            for offset, (key, payload) in enumerate(unique):
                if not force and connection.execute(
                        'SELECT 1 FROM metadata WHERE cache_key=?', (key,)).fetchone():
                    continue
                connection.execute(
                    'INSERT OR REPLACE INTO queue('
                    'cache_key, queued_at, payload, priority) VALUES(?,?,?,?)',
                    (key, now + offset, encode_focus(payload), int(priority)),
                )
                queued += 1
        return queued
    except sqlite3.Error as exc:
        xbmc.log('Appi metadata queue failed: {}'.format(exc), xbmc.LOGWARNING)
        return 0


def queue(payload, force=False, priority=0):
    if not enabled() or not payload or not payload.get('title'):
        return False
    return bool(queue_many([payload], force=force, priority=priority))


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


def _custom_properties(item):
    """Normalise JSON-RPC custom properties across Kodi versions."""
    properties = item.get('customproperties') or {}
    if isinstance(properties, dict):
        return {str(key).casefold(): value for key, value in properties.items()}
    result = {}
    if isinstance(properties, list):
        for entry in properties:
            if not isinstance(entry, dict):
                continue
            key = entry.get('key') or entry.get('name')
            if key:
                result[str(key).casefold()] = entry.get('value')
    return result


def _imdb_rating(item, lower_props):
    """Return IMDb only; never relabel a generic/TMDb score as IMDb."""
    rating = _float(lower_props.get('imdb_rating'))
    votes = _int(lower_props.get('imdb_votes'))
    ratings = item.get('ratings') or {}
    imdb = None
    if isinstance(ratings, dict):
        imdb = next(
            (value for key, value in ratings.items() if str(key).casefold() == 'imdb'),
            None,
        )
    if rating is None and isinstance(imdb, dict):
        rating = _float(imdb.get('rating') if 'rating' in imdb else imdb.get('value'))
        votes = _int(imdb.get('votes')) or votes
    elif rating is None and imdb is not None:
        rating = _float(imdb)
    return rating, votes


def _directors(item):
    value = item.get('director') or item.get('directors') or []
    if isinstance(value, str):
        value = [part.strip() for part in value.split(' / ')]
    if not isinstance(value, (list, tuple)):
        return []
    return [str(name).strip() for name in value if str(name).strip()][:6]


def _normalise_result(item, payload):
    lower_props = _custom_properties(item)
    art = item.get('art') or {}
    cast = []
    for person in (item.get('cast') or [])[:12]:
        if isinstance(person, dict) and person.get('name'):
            cast.append({
                'name': person['name'],
                'role': person.get('role') or '',
                'thumbnail': person.get('thumbnail') or '',
            })
    rating, votes = _imdb_rating(item, lower_props)
    result = {
        'plot': item.get('plot') or '',
        'poster': art.get('poster') or item.get('thumbnail') or '',
        'cast': cast,
        'directors': _directors(item),
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
        'SELECT cache_key FROM metadata ORDER BY fetched_at DESC LIMIT -1 OFFSET ?)',
        (maximum,),
    )


def process_one():
    if not enabled() or xbmc.Player().isPlayingVideo():
        return False
    if not xbmc.getCondVisibility('System.HasAddon({})'.format(HELPER_ID)):
        return False
    with _connect() as connection:
        row = connection.execute(
            'SELECT cache_key, payload FROM queue '
            'ORDER BY priority DESC, queued_at LIMIT 1'
        ).fetchone()
    if not row:
        return False
    key, encoded = row
    payload = decode_focus(encoded)
    try:
        properties = [
            'title', 'plot', 'year', 'cast', 'director', 'thumbnail', 'art',
            'ratings', 'imdbnumber', 'uniqueid', 'customproperties',
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
            # customproperties is not accepted by every Kodi JSON-RPC build.
            # Structured ratings remains the preferred fallback because it lets
            # us select IMDb explicitly instead of mislabelling a generic score.
            request['properties'] = [
                value for value in properties if value != 'customproperties'
            ]
            result = _jsonrpc('Files.GetDirectory', request)
        files = result.get('files') or []
        if not files:
            raise RuntimeError('TMDb Helper returned no match')
        data = _normalise_result(files[0], payload)
        with _connect() as connection:
            connection.execute(
                'INSERT OR REPLACE INTO metadata(cache_key, fetched_at, data) VALUES(?,?,?)',
                (key, int(time.time()), json.dumps(data, ensure_ascii=False, separators=(',', ':'))),
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


def status():
    try:
        with _connect() as connection:
            cached = connection.execute('SELECT COUNT(*) FROM metadata').fetchone()[0]
            queued = connection.execute('SELECT COUNT(*) FROM queue').fetchone()[0]
    except sqlite3.Error:
        cached, queued = 0, 0
    return {'cached': cached, 'queued': queued, 'helper': bool(
        xbmc.getCondVisibility('System.HasAddon({})'.format(HELPER_ID))
    )}
