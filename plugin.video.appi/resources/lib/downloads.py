import json
import os
import re
import shutil
import sqlite3
import threading
import time
import unicodedata
import xml.etree.ElementTree as ET
from urllib.parse import urljoin
from urllib.request import Request, urlopen

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from . import metadata
from .catalog import item_ref
from .http import _headers, fetch_text, probe_stream


ADDON = xbmcaddon.Addon()
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
CHUNK_SIZE = 256 * 1024


class PlaybackStarted(Exception):
    """Yield an active download so playback keeps priority on low-end devices."""


def _ensure_directory(path):
    os.makedirs(path, exist_ok=True)
    return path


def download_root():
    configured = (ADDON.getSetting('download_folder') or '').strip()
    path = xbmcvfs.translatePath(configured) if configured else os.path.join(PROFILE, 'downloads')
    if '://' in path:
        raise RuntimeError('Download folder must be a writable local filesystem path')
    return _ensure_directory(path)


def _db_path():
    return os.path.join(_ensure_directory(PROFILE), 'downloads.db')


def _connect():
    connection = sqlite3.connect(_db_path(), timeout=5)
    connection.execute('PRAGMA journal_mode=WAL')
    connection.execute('PRAGMA synchronous=NORMAL')
    connection.execute(
        'CREATE TABLE IF NOT EXISTS downloads ('
        'download_id TEXT PRIMARY KEY, status TEXT NOT NULL, queued_at INTEGER NOT NULL, '
        'updated_at INTEGER NOT NULL, catalog TEXT NOT NULL, show_key TEXT NOT NULL, '
        'payload TEXT NOT NULL, target_path TEXT NOT NULL DEFAULT "", '
        'progress REAL NOT NULL DEFAULT 0, error TEXT NOT NULL DEFAULT "")'
    )
    return connection


def _download_id(catalog, item):
    return '{}|{}'.format(catalog, item_ref(item))


def queue_item(catalog, item, show_key=''):
    if catalog not in {'movies', 'tv'} or not item.get('media_url'):
        return False
    try:
        download_root()
    except (OSError, RuntimeError) as exc:
        xbmc.log('Appi download destination is invalid: {}'.format(exc), xbmc.LOGWARNING)
        return False
    identifier = _download_id(catalog, item)
    now = int(time.time() * 1000)
    try:
        with _connect() as connection:
            existing = connection.execute(
                'SELECT status, target_path FROM downloads WHERE download_id=?',
                (identifier,),
            ).fetchone()
            if existing and existing[0] in {'queued', 'downloading'}:
                return False
            if existing and existing[0] == 'complete' and existing[1] and os.path.exists(existing[1]):
                return False
            connection.execute(
                'INSERT OR REPLACE INTO downloads('
                'download_id,status,queued_at,updated_at,catalog,show_key,payload,'
                'target_path,progress,error) VALUES(?,?,?,?,?,?,?,?,?,?)',
                (
                    identifier, 'queued', now, now, catalog, show_key or '',
                    json.dumps(item, ensure_ascii=False, separators=(',', ':')),
                    '', 0.0, '',
                ),
            )
        return True
    except (sqlite3.Error, TypeError, ValueError) as exc:
        xbmc.log('Appi download queue failed: {}'.format(exc), xbmc.LOGWARNING)
        return False


def _claim_next():
    try:
        with _connect() as connection:
            connection.execute('BEGIN IMMEDIATE')
            row = connection.execute(
                'SELECT download_id,catalog,show_key,payload FROM downloads '
                'WHERE status="queued" ORDER BY queued_at LIMIT 1'
            ).fetchone()
            if not row:
                return None
            connection.execute(
                'UPDATE downloads SET status="downloading",updated_at=?,error="" '
                'WHERE download_id=?',
                (int(time.time() * 1000), row[0]),
            )
        try:
            item = json.loads(row[3])
        except (TypeError, ValueError):
            item = None
        if not isinstance(item, dict):
            _finish(row[0], 'error', error='Invalid queued download data')
            return None
        return {
            'download_id': row[0], 'catalog': row[1], 'show_key': row[2], 'item': item,
        }
    except sqlite3.Error as exc:
        xbmc.log('Appi could not claim download: {}'.format(exc), xbmc.LOGWARNING)
        return None


def _progress(identifier, value, target_path=''):
    try:
        with _connect() as connection:
            connection.execute(
                'UPDATE downloads SET progress=?,target_path=?,updated_at=? WHERE download_id=?',
                (max(0.0, min(1.0, float(value))), target_path, int(time.time() * 1000), identifier),
            )
    except sqlite3.Error:
        pass


def _finish(identifier, status, target_path='', error=''):
    try:
        with _connect() as connection:
            connection.execute(
                'UPDATE downloads SET status=?,target_path=?,progress=?,error=?,updated_at=? '
                'WHERE download_id=?',
                (
                    status, target_path, 1.0 if status == 'complete' else 0.0,
                    str(error or ''), int(time.time() * 1000), identifier,
                ),
            )
    except sqlite3.Error:
        pass


def status():
    result = {'queued': 0, 'downloading': 0, 'complete': 0, 'error': 0}
    try:
        with _connect() as connection:
            for name, count in connection.execute(
                    'SELECT status, COUNT(*) FROM downloads GROUP BY status').fetchall():
                result[name] = count
    except sqlite3.Error:
        pass
    return result


def retry_errors():
    try:
        with _connect() as connection:
            connection.execute(
                'UPDATE downloads SET status="queued",error="",queued_at=?,updated_at=? '
                'WHERE status="error"',
                (int(time.time() * 1000), int(time.time() * 1000)),
            )
        return True
    except sqlite3.Error:
        return False


def clear_queue():
    try:
        with _connect() as connection:
            connection.execute('DELETE FROM downloads WHERE status != "downloading"')
        return True
    except sqlite3.Error:
        return False


def _safe_name(value, fallback):
    value = unicodedata.normalize('NFKC', str(value or '')).strip()
    value = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', value)
    value = re.sub(r'\s+', ' ', value).strip(' .')
    return (value[:160].rstrip(' .') or fallback)


def _base_destination(job, enriched=None):
    item = job['item']
    root = download_root()
    if job['catalog'] == 'movies':
        title = _safe_name(item.get('title') or item.get('display_title'), 'Movie')
        if item.get('year'):
            title = '{} ({})'.format(title, item['year'])
        folder = _ensure_directory(os.path.join(root, 'Movies', title))
        return os.path.join(folder, title)
    show = _safe_name(item.get('show_title') or item.get('group_title'), 'TV Show')
    season = int(item.get('season') or 0)
    episode = int(item.get('episode') or 0)
    episode_title = (enriched or {}).get('episode_title') or item.get('display_title') or 'Episode'
    episode_title = _safe_name(episode_title, 'Episode')
    folder = _ensure_directory(os.path.join(root, 'TV Shows', show, 'Season {:02d}'.format(season)))
    filename = '{} - S{:02d}E{:02d} - {}'.format(show, season, episode, episode_title)
    return os.path.join(folder, filename)


def _download_direct(url, target, identifier, stop_event, playing_callback=lambda: False):
    part = target + '.part'
    existing = os.path.getsize(part) if os.path.exists(part) else 0
    headers = _headers({'Range': 'bytes={}-'.format(existing)}) if existing else _headers()
    request = Request(url, headers=headers)
    with urlopen(request, timeout=30) as response:
        status_code = getattr(response, 'status', response.getcode())
        append = bool(existing and status_code == 206)
        if not append:
            existing = 0
        length = int(response.headers.get('Content-Length') or 0)
        total = existing + length if length else 0
        mode = 'ab' if append else 'wb'
        completed = existing
        last_update = 0.0
        with open(part, mode) as handle:
            while not stop_event.is_set():
                if playing_callback():
                    raise PlaybackStarted('Video playback started')
                chunk = response.read(CHUNK_SIZE)
                if not chunk:
                    break
                handle.write(chunk)
                completed += len(chunk)
                now = time.monotonic()
                if now - last_update >= 1.0:
                    _progress(identifier, completed / total if total else 0.0, target)
                    last_update = now
            if stop_event.is_set():
                raise InterruptedError('Kodi is stopping')
        if total and completed < total:
            raise RuntimeError(
                'Download ended early ({} of {} bytes)'.format(completed, total)
            )
    os.replace(part, target)


def _parse_attributes(value):
    result = {}
    for match in re.finditer(r'([A-Z0-9-]+)=("[^"]*"|[^,]*)', value, re.I):
        raw = match.group(2).strip()
        result[match.group(1).upper()] = raw[1:-1] if raw.startswith('"') and raw.endswith('"') else raw
    return result


def _media_playlist(url, text):
    lines = [line.strip() for line in (text or '').splitlines() if line.strip()]
    variants = []
    for index, line in enumerate(lines):
        if not line.startswith('#EXT-X-STREAM-INF:'):
            continue
        attrs = _parse_attributes(line.split(':', 1)[1])
        uri = next((candidate for candidate in lines[index + 1:] if not candidate.startswith('#')), '')
        if uri:
            try:
                bandwidth = int(attrs.get('AVERAGE-BANDWIDTH') or attrs.get('BANDWIDTH') or 0)
            except (TypeError, ValueError):
                bandwidth = 0
            variants.append((bandwidth, urljoin(url, uri), bool(attrs.get('AUDIO'))))
    if not variants:
        return url, text
    try:
        maximum = max(250, int(ADDON.getSetting('hls_max_bitrate_kbps') or 8000)) * 1000
    except (TypeError, ValueError):
        maximum = 8000000
    within = [entry for entry in variants if entry[0] and entry[0] <= maximum]
    selected = max(within or variants, key=lambda entry: entry[0])
    if selected[2]:
        raise RuntimeError('HLS with a separate audio rendition cannot be packaged safely')
    selected_text = fetch_text(selected[1], timeout=30)
    return _media_playlist(selected[1], selected_text)


def _byterange(value, previous_end):
    if not value:
        return None, previous_end
    length_value, separator, offset_value = value.partition('@')
    length = int(length_value)
    start = int(offset_value) if separator else previous_end
    return (start, start + length - 1), start + length


def _parse_hls(url, text):
    if '#EXT-X-ENDLIST' not in text:
        raise RuntimeError('Only completed HLS programmes can be downloaded')
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    segments = []
    init_segment = None
    pending_range = ''
    previous_end = 0
    previous_uri = ''
    for line in lines:
        if line in {'#EXT-X-DISCONTINUITY', '#EXT-X-GAP', '#EXT-X-I-FRAMES-ONLY'}:
            raise RuntimeError('HLS playlist requires remuxing and cannot be packaged safely')
        if line.startswith('#EXT-X-KEY:'):
            attrs = _parse_attributes(line.split(':', 1)[1])
            if (attrs.get('METHOD') or 'NONE').upper() != 'NONE':
                raise RuntimeError('Encrypted HLS cannot be downloaded')
        elif line.startswith('#EXT-X-MAP:'):
            attrs = _parse_attributes(line.split(':', 1)[1])
            raw_map_uri = attrs.get('URI') or ''
            if not raw_map_uri:
                raise RuntimeError('HLS initialization segment has no URI')
            map_uri = urljoin(url, raw_map_uri)
            if attrs.get('BYTERANGE') and '@' not in attrs['BYTERANGE'] and previous_uri != map_uri:
                previous_end = 0
            byte_range, previous_end = _byterange(attrs.get('BYTERANGE'), previous_end)
            candidate = (map_uri, byte_range)
            if init_segment and init_segment != candidate:
                raise RuntimeError('HLS changes initialization segments and requires remuxing')
            init_segment = candidate
            previous_uri = map_uri
        elif line.startswith('#EXT-X-BYTERANGE:'):
            pending_range = line.split(':', 1)[1]
        elif not line.startswith('#'):
            segment_uri = urljoin(url, line)
            if pending_range and '@' not in pending_range and previous_uri != segment_uri:
                raise RuntimeError('Invalid implicit HLS byte range across different resources')
            byte_range, previous_end = _byterange(pending_range, previous_end)
            pending_range = ''
            segments.append((segment_uri, byte_range))
            previous_uri = segment_uri
    if not segments:
        raise RuntimeError('HLS playlist contained no media segments')
    return init_segment, segments


def _download_resource(
        url, byte_range, path, stop_event, playing_callback=lambda: False):
    headers = _headers()
    if byte_range:
        headers['Range'] = 'bytes={}-{}'.format(byte_range[0], byte_range[1])
    with urlopen(Request(url, headers=headers), timeout=30) as response, open(path, 'wb') as handle:
        while not stop_event.is_set():
            if playing_callback():
                raise PlaybackStarted('Video playback started')
            chunk = response.read(CHUNK_SIZE)
            if not chunk:
                break
            handle.write(chunk)
    if stop_event.is_set():
        raise InterruptedError('Kodi is stopping')


def _download_hls(
        url, text, target_base, identifier, stop_event,
        playing_callback=lambda: False):
    media_url, media_text = _media_playlist(url, text)
    init_segment, segments = _parse_hls(media_url, media_text)
    extension = '.mp4' if init_segment else '.ts'
    target = target_base + extension
    part = target + '.part'
    state_path = part + '.json'
    state_identity = '{}|{}|{}'.format(media_url, len(segments), bool(init_segment))
    state = {}
    if os.path.exists(state_path):
        try:
            with open(state_path, 'r', encoding='utf-8') as handle:
                state = json.load(handle)
        except (OSError, ValueError, TypeError):
            state = {}
    if state.get('identity') != state_identity or not os.path.exists(part):
        state = {'identity': state_identity, 'next': 0, 'init_done': False}
        with open(part, 'wb'):
            pass
    if init_segment and not state.get('init_done'):
        segment_temp = part + '.segment'
        _download_resource(
            init_segment[0], init_segment[1], segment_temp, stop_event, playing_callback
        )
        with open(part, 'ab') as output, open(segment_temp, 'rb') as source:
            shutil.copyfileobj(source, output, CHUNK_SIZE)
        os.remove(segment_temp)
        state['init_done'] = True
    for index in range(int(state.get('next') or 0), len(segments)):
        segment_temp = part + '.segment'
        _download_resource(
            segments[index][0], segments[index][1], segment_temp,
            stop_event, playing_callback,
        )
        with open(part, 'ab') as output, open(segment_temp, 'rb') as source:
            shutil.copyfileobj(source, output, CHUNK_SIZE)
        os.remove(segment_temp)
        state['next'] = index + 1
        with open(state_path, 'w', encoding='utf-8') as handle:
            json.dump(state, handle, separators=(',', ':'))
        _progress(identifier, float(index + 1) / len(segments), target)
    os.replace(part, target)
    try:
        os.remove(state_path)
    except FileNotFoundError:
        pass
    return target


def _write_nfo(path, job, enriched):
    item = job['item']
    is_movie = job['catalog'] == 'movies'
    root = ET.Element('movie' if is_movie else 'episodedetails')
    title = (
        item.get('title') or item.get('display_title') or 'Movie'
        if is_movie else (enriched or {}).get('episode_title') or item.get('display_title') or 'Episode'
    )
    ET.SubElement(root, 'title').text = str(title)
    if not is_movie:
        ET.SubElement(root, 'showtitle').text = str(item.get('show_title') or '')
        ET.SubElement(root, 'season').text = str(item.get('season') or 0)
        ET.SubElement(root, 'episode').text = str(item.get('episode') or 0)
    if item.get('year'):
        ET.SubElement(root, 'year').text = str(item['year'])
    if (enriched or {}).get('plot'):
        ET.SubElement(root, 'plot').text = enriched['plot']
    if (enriched or {}).get('poster'):
        ET.SubElement(root, 'thumb', {'aspect': 'poster'}).text = enriched['poster']
    if (enriched or {}).get('imdb_rating') is not None:
        ratings = ET.SubElement(root, 'ratings')
        rating = ET.SubElement(ratings, 'rating', {'name': 'imdb', 'max': '10', 'default': 'true'})
        ET.SubElement(rating, 'value').text = str(enriched['imdb_rating'])
        ET.SubElement(rating, 'votes').text = str((enriched or {}).get('imdb_votes') or 0)
    imdb_id = (enriched or {}).get('imdb_id') or item.get('tvg_id') or ''
    if imdb_id:
        ET.SubElement(root, 'uniqueid', {'type': 'imdb', 'default': 'true'}).text = imdb_id
    for person in (enriched or {}).get('cast') or []:
        actor = ET.SubElement(root, 'actor')
        ET.SubElement(actor, 'name').text = person.get('name') or ''
        ET.SubElement(actor, 'role').text = person.get('role') or ''
        if person.get('thumbnail'):
            ET.SubElement(actor, 'thumb').text = person['thumbnail']
    for director in (enriched or {}).get('directors') or []:
        if director:
            ET.SubElement(root, 'director').text = str(director)
    tree = ET.ElementTree(root)
    ET.indent(tree, space='  ')
    tree.write(os.path.splitext(path)[0] + '.nfo', encoding='utf-8', xml_declaration=True)
    if not is_movie:
        show_root = ET.Element('tvshow')
        ET.SubElement(show_root, 'title').text = str(item.get('show_title') or 'TV Show')
        if item.get('year'):
            ET.SubElement(show_root, 'year').text = str(item['year'])
        show_id = item.get('tvg_id') or ''
        if show_id:
            ET.SubElement(
                show_root, 'uniqueid', {'type': 'imdb', 'default': 'true'}
            ).text = show_id
        show_tree = ET.ElementTree(show_root)
        ET.indent(show_tree, space='  ')
        show_tree.write(
            os.path.join(os.path.dirname(os.path.dirname(path)), 'tvshow.nfo'),
            encoding='utf-8', xml_declaration=True,
        )


def _scan(path):
    request = json.dumps({
        'jsonrpc': '2.0', 'id': 1, 'method': 'VideoLibrary.Scan',
        'params': {'directory': os.path.dirname(path), 'showdialogs': False},
    }, separators=(',', ':'))
    try:
        xbmc.executeJSONRPC(request)
    except Exception:
        pass


def _download(job, stop_event, playing_callback=lambda: False):
    item = job['item']
    payload = metadata.lookup_payload(item)
    enriched = metadata.get(payload) or {}
    base = _base_destination(job, enriched)
    stream = probe_stream(item['media_url'], timeout=20)
    kind = stream.get('kind')
    final_url = stream.get('final_url') or item['media_url']
    if kind == 'mp4':
        target = base + '.mp4'
        _download_direct(
            final_url, target, job['download_id'], stop_event, playing_callback
        )
    elif kind == 'hls':
        playlist = fetch_text(final_url, timeout=30)
        target = _download_hls(
            final_url, playlist, base, job['download_id'], stop_event, playing_callback
        )
    else:
        raise RuntimeError('The provider returned an unsupported download format')
    _write_nfo(target, job, enriched)
    _finish(job['download_id'], 'complete', target_path=target)
    _scan(target)
    xbmcgui.Dialog().notification('Appi', 'Download complete: {}'.format(os.path.basename(target)))


def worker(stop_event, playing_callback):
    while not stop_event.wait(1.0):
        if playing_callback():
            continue
        job = _claim_next()
        if not job:
            continue
        try:
            _download(job, stop_event, playing_callback)
        except PlaybackStarted:
            _finish(job['download_id'], 'queued')
            continue
        except InterruptedError:
            _finish(job['download_id'], 'queued')
            return
        except Exception as exc:
            xbmc.log('Appi download failed: {}'.format(exc), xbmc.LOGERROR)
            _finish(job['download_id'], 'error', error='{}: {}'.format(type(exc).__name__, exc))
            xbmcgui.Dialog().notification(
                'Appi', 'Download failed: {}'.format(exc), xbmcgui.NOTIFICATION_ERROR, 7000
            )


def start_worker(playing_callback):
    stop_event = threading.Event()
    thread = threading.Thread(
        target=worker, args=(stop_event, playing_callback),
        name='AppiDownloadWorker', daemon=True,
    )
    thread.start()
    return stop_event, thread
