import hashlib
import json
import os
import queue
import re
import secrets
import shutil
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, urlparse
from urllib.request import Request, urlopen

import xbmcaddon
import xbmcvfs

from . import hls

ADDON = xbmcaddon.Addon()
DEFAULT_TARGET_SECONDS = 30.0
DEFAULT_STARTUP_SECONDS = 18.0
DEFAULT_RECOVERY_SECONDS = 15.0
REQUEST_TIMEOUT = 20.0
RECOVERY_TIMEOUT = 45.0
CONTROL_TIMEOUT = 10.0
STALE_SESSION_SECONDS = 90.0
MAX_SESSION_BYTES = 384 * 1024 * 1024
_USER_AGENT = 'Kodi Appi Buffered/0.7.16'
_URI_RE = re.compile(r'URI=(?P<quoted>"(?P<qvalue>[^"]*)"|(?P<uvalue>[^,]*))', re.IGNORECASE)
_ATTR_RE = re.compile(r'([A-Z0-9-]+)=(?:"([^"]*)"|([^,]*))', re.IGNORECASE)


def _root_path():
    root = xbmcvfs.translatePath('special://temp/')
    return os.path.join(root, 'appi-buffered-hls')


def _ensure(path):
    os.makedirs(path, exist_ok=True)


def _json_read(path):
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            value = json.load(handle)
        return value if isinstance(value, dict) else None
    except (OSError, ValueError, TypeError):
        return None


def _json_write(path, value):
    _ensure(os.path.dirname(path))
    temp = path + '.tmp'
    with open(temp, 'w', encoding='utf-8') as handle:
        json.dump(value, handle, ensure_ascii=False, separators=(',', ':'))
    os.replace(temp, path)


def _attributes(value):
    result = {}
    for match in _ATTR_RE.finditer(value or ''):
        result[match.group(1).upper()] = (match.group(2) if match.group(2) is not None else match.group(3)).strip()
    return result


def _float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _identity(value):
    return hashlib.sha256((value or '').encode('utf-8', errors='replace')).hexdigest()[:16]


def _split_kodi_url(url):
    core, marker, options = (url or '').partition('|')
    headers = {}
    if marker:
        for key, value in parse_qsl(options, keep_blank_values=True):
            headers[key] = value
    return core, headers, options if marker else ''


def _with_kodi_options(core, options):
    return '{}|{}'.format(core, options) if options else core


def _safe_status(response):
    try:
        return int(response.getcode() or 200)
    except Exception:
        return 200


def request_playback(source_url, target_seconds=DEFAULT_TARGET_SECONDS, startup_seconds=DEFAULT_STARTUP_SECONDS, timeout=CONTROL_TIMEOUT):
    root = _root_path()
    control = os.path.join(root, 'control')
    _ensure(control)
    request_id = secrets.token_hex(12)
    request_path = os.path.join(control, 'request.json')
    response_path = os.path.join(control, 'response-{}.json'.format(request_id))
    _json_write(request_path, {
        'id': request_id,
        'source_url': source_url,
        'target_seconds': max(5.0, float(target_seconds)),
        'startup_seconds': max(5.0, float(startup_seconds)),
        'created_at': time.time(),
    })
    deadline = time.monotonic() + max(1.0, float(timeout))
    while time.monotonic() < deadline:
        response = _json_read(response_path)
        if response and response.get('id') == request_id:
            try:
                os.remove(response_path)
            except OSError:
                pass
            if response.get('error'):
                raise RuntimeError(str(response['error']))
            local_url = response.get('local_url') or ''
            if local_url:
                return local_url
            raise RuntimeError('Buffered playback service returned no local URL.')
        time.sleep(0.05)
    pending = _json_read(request_path)
    if pending and pending.get('id') == request_id:
        try:
            os.remove(request_path)
        except OSError:
            pass
    raise RuntimeError('Buffered playback service did not respond. Restart Kodi and try again.')


class _FetchResult:
    def __init__(self, data, final_url, content_type, status, latency_ms, download_ms, byte_count=None):
        self.data = data
        self.byte_count = len(data) if byte_count is None else int(byte_count)
        self.final_url = final_url
        self.content_type = content_type
        self.status = status
        self.latency_ms = latency_ms
        self.download_ms = download_ms

    @property
    def throughput_mbps(self):
        seconds = max(0.001, self.download_ms / 1000.0)
        return round((self.byte_count * 8.0) / seconds / 1000000.0, 3)


def _fetch(url, timeout=REQUEST_TIMEOUT, byte_range=''):
    core, option_headers, kodi_options = _split_kodi_url(url)
    headers = {
        'User-Agent': option_headers.pop('User-Agent', _USER_AGENT),
        'Accept-Encoding': 'identity',
        'Accept': '*/*',
    }
    headers.update(option_headers)
    if byte_range:
        headers['Range'] = 'bytes={}'.format(byte_range)
    request = Request(core, headers=headers)
    started = time.monotonic()
    with urlopen(request, timeout=timeout) as response:
        latency_ms = (time.monotonic() - started) * 1000.0
        data = response.read()
        finished = time.monotonic()
        final_url = _with_kodi_options(response.geturl(), kodi_options)
        content_type = (response.headers.get('Content-Type', '') or '').split(';', 1)[0].strip().lower()
        status = _safe_status(response)
    return _FetchResult(
        data=data,
        final_url=final_url,
        content_type=content_type,
        status=status,
        latency_ms=round(latency_ms, 2),
        download_ms=round((finished - started) * 1000.0, 2),
    )


def _fetch_to_path(url, path, timeout=REQUEST_TIMEOUT, byte_range=''):
    core, option_headers, kodi_options = _split_kodi_url(url)
    headers = {
        'User-Agent': option_headers.pop('User-Agent', _USER_AGENT),
        'Accept-Encoding': 'identity',
        'Accept': '*/*',
    }
    headers.update(option_headers)
    if byte_range:
        headers['Range'] = 'bytes={}'.format(byte_range)
    request = Request(core, headers=headers)
    started = time.monotonic()
    temp = path + '.part'
    byte_count = 0
    try:
        with urlopen(request, timeout=timeout) as response:
            latency_ms = (time.monotonic() - started) * 1000.0
            with open(temp, 'wb') as handle:
                while True:
                    chunk = response.read(256 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
                    byte_count += len(chunk)
            finished = time.monotonic()
            final_url = _with_kodi_options(response.geturl(), kodi_options)
            content_type = (response.headers.get('Content-Type', '') or '').split(';', 1)[0].strip().lower()
            status = _safe_status(response)
        os.replace(temp, path)
    except Exception:
        try:
            os.remove(temp)
        except OSError:
            pass
        raise
    return _FetchResult(
        data=b'',
        final_url=final_url,
        content_type=content_type,
        status=status,
        latency_ms=round(latency_ms, 2),
        download_ms=round((finished - started) * 1000.0, 2),
        byte_count=byte_count,
    )


def _byterange(value, previous_end=-1):
    value = (value or '').strip().strip('"')
    if not value:
        return '', previous_end
    length, sep, offset = value.partition('@')
    length_i = _int(length, 0)
    if length_i <= 0:
        return '', previous_end
    start = _int(offset, 0) if sep else max(0, int(previous_end) + 1)
    end = start + length_i - 1
    return '{}-{}'.format(start, end), end


def _byterange_header(value):
    return _byterange(value)[0]


class _Resource:
    def __init__(self, resource_id, upstream_url, kind, content_type='', metadata=None, byte_range=''):
        self.id = resource_id
        self.upstream_url = upstream_url
        self.kind = kind
        self.content_type = content_type
        self.metadata = dict(metadata or {})
        self.byte_range = byte_range
        self.path = ''
        self.error = ''
        self.fetching = False
        self.condition = threading.Condition()


class _Segment:
    def __init__(self, resource, sequence, duration, index):
        self.resource = resource
        self.sequence = int(sequence)
        self.duration = max(0.0, float(duration))
        self.index = int(index)


class _Track:
    def __init__(self, session, track_id, target_seconds, startup_seconds, recovery_seconds):
        self.session = session
        self.id = track_id
        self.target_seconds = float(target_seconds)
        self.startup_seconds = min(float(startup_seconds), self.target_seconds)
        self.recovery_seconds = min(float(recovery_seconds), self.target_seconds)
        self.segments = []
        self.last_served = -1
        self.downloaded_total = 0
        self.failed = ''
        self._condition = threading.Condition()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._prefetch_loop, name='AppiHlsPrefetch', daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        with self._condition:
            self._condition.notify_all()
        if self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def replace_segments(self, segments):
        with self._condition:
            old_by_key = {
                (seg.sequence, seg.resource.upstream_url, seg.resource.byte_range): seg
                for seg in self.segments
            }
            merged = []
            for incoming in segments:
                key = (incoming.sequence, incoming.resource.upstream_url, incoming.resource.byte_range)
                old = old_by_key.get(key)
                if old and old.resource.path and os.path.isfile(old.resource.path):
                    incoming.resource.path = old.resource.path
                merged.append(incoming)
            self.segments = merged
            if self.last_served >= len(self.segments):
                self.last_served = max(-1, len(self.segments) - 1)
            self._condition.notify_all()

    def _cached(self, index):
        if index < 0 or index >= len(self.segments):
            return False
        path = self.segments[index].resource.path
        return bool(path and os.path.isfile(path))

    def _ahead(self, start_index=None):
        if start_index is None:
            start_index = self.last_served + 1
        seconds = 0.0
        count = 0
        for index in range(max(0, start_index), len(self.segments)):
            if not self._cached(index):
                break
            seconds += self.segments[index].duration
            count += 1
        return round(seconds, 3), count

    def _next_missing(self):
        start = max(0, self.last_served + 1)
        elapsed = 0.0
        for index in range(start, len(self.segments)):
            if not self._cached(index):
                return index
            elapsed += self.segments[index].duration
            if elapsed >= self.target_seconds:
                return None
        return None

    def _prefetch_loop(self):
        while not self._stop.is_set():
            with self._condition:
                index = self._next_missing()
                if index is None:
                    self._condition.wait(timeout=0.5)
                    continue
                segment = self.segments[index]
            try:
                self.session._ensure_binary(segment.resource, segment=segment, track=self)
                with self._condition:
                    self.downloaded_total += 1
                    self.failed = ''
                    self._condition.notify_all()
            except Exception as exc:
                with self._condition:
                    self.failed = '{}: {}'.format(type(exc).__name__, exc)
                    self._condition.notify_all()
                self.session._event(
                    'buffer_segment_error',
                    track_id=self.id,
                    segment_sequence=segment.sequence,
                    error_type=type(exc).__name__,
                )
                if self._stop.wait(1.0):
                    break

    def wait_startup(self, timeout=RECOVERY_TIMEOUT):
        return self._wait_for_reserve(0, self.startup_seconds, timeout)

    def _wait_for_reserve(self, index, reserve_seconds, timeout):
        deadline = time.monotonic() + max(1.0, timeout)
        with self._condition:
            if self.last_served < index - 1:
                self.last_served = index - 1
            self._condition.notify_all()
            while not self._stop.is_set():
                ahead, _ = self._ahead(index)
                remaining = sum(seg.duration for seg in self.segments[index:])
                threshold = min(reserve_seconds, remaining)
                if ahead >= threshold or (remaining <= 0 and index >= len(self.segments)):
                    return True
                if time.monotonic() >= deadline:
                    return False
                self._condition.wait(timeout=0.25)
        return False

    def serve(self, index):
        if index < 0 or index >= len(self.segments):
            raise IndexError('HLS segment index outside playlist')
        expected = self.last_served + 1
        if self.last_served >= 0 and index != expected:
            self.session._event(
                'buffer_seek_recenter',
                track_id=self.id,
                from_index=self.last_served,
                to_index=index,
            )
            with self._condition:
                self.last_served = index - 1
                self._condition.notify_all()

        ahead, count = self._ahead(index)
        remaining = sum(seg.duration for seg in self.segments[index:])
        threshold = min(self.recovery_seconds, remaining)
        if ahead < threshold:
            self.session._event(
                'buffer_depletion',
                track_id=self.id,
                buffered_seconds=ahead,
                cached_segments_ahead=count,
                requested_index=index,
            )
            recovered = self._wait_for_reserve(index, self.recovery_seconds, RECOVERY_TIMEOUT)
            new_ahead, new_count = self._ahead(index)
            self.session._event(
                'buffer_recovery' if recovered else 'buffer_recovery_timeout',
                track_id=self.id,
                buffered_seconds=new_ahead,
                cached_segments_ahead=new_count,
                requested_index=index,
            )

        if not self._cached(index):
            self.session._ensure_binary(
                self.segments[index].resource,
                segment=self.segments[index],
                track=self,
            )
        segment = self.segments[index]
        with self._condition:
            self.last_served = index
            self._condition.notify_all()
        self._cleanup_old(index)
        ahead, count = self._ahead(index + 1)
        self.session._event(
            'buffer_status',
            track_id=self.id,
            buffered_seconds=ahead,
            cached_segments_ahead=count,
            queued_segment_count=self._queued_count(index + 1),
            downloaded_segment_count=self.downloaded_total,
        )
        return segment.resource.path

    def _queued_count(self, start_index):
        remaining = self.target_seconds
        count = 0
        for seg in self.segments[start_index:]:
            if self._cached(seg.index):
                remaining -= seg.duration
                if remaining <= 0:
                    break
                continue
            count += 1
            remaining -= seg.duration
            if remaining <= 0:
                break
        return count

    def _cleanup_old(self, current_index):
        keep_from = max(0, current_index - 2)
        for segment in self.segments[:keep_from]:
            path = segment.resource.path
            if path and os.path.isfile(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
                segment.resource.path = ''


class BufferedHlsSession:
    def __init__(
        self,
        source_url,
        target_seconds=DEFAULT_TARGET_SECONDS,
        startup_seconds=DEFAULT_STARTUP_SECONDS,
        recovery_seconds=DEFAULT_RECOVERY_SECONDS,
        root=None,
    ):
        self.source_url = source_url
        self.target_seconds = max(5.0, float(target_seconds))
        self.startup_seconds = min(max(5.0, float(startup_seconds)), self.target_seconds)
        self.recovery_seconds = min(max(5.0, float(recovery_seconds)), self.target_seconds)
        self.token = secrets.token_hex(12)
        self.root = root or os.path.join(_root_path(), 'session-{}'.format(self.token))
        self.data_root = os.path.join(self.root, 'data')
        _ensure(self.data_root)
        self.resources = {}
        self.tracks = {}
        self.events = queue.Queue()
        self._resource_counter = 0
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._server = None
        self._server_thread = None
        self.last_access = time.monotonic()
        self._selected_representation = ''
        self.master = self._register(source_url, 'playlist', metadata={'root': True})

    @property
    def local_url(self):
        if not self._server:
            return ''
        return self._local_url(self.master.id, '.m3u8')

    def _local_url(self, resource_id, suffix=''):
        return 'http://127.0.0.1:{}/hls/{}/{}{}'.format(
            self._server.server_address[1], self.token, resource_id, suffix)

    def _event(self, name, **fields):
        fields['observed_at'] = round(time.time(), 3)
        self.events.put((name, fields))

    def drain_events(self):
        values = []
        while True:
            try:
                values.append(self.events.get_nowait())
            except queue.Empty:
                break
        return values

    def start(self):
        session = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'

            def log_message(self, fmt, *args):
                return

            def do_HEAD(self):
                parsed = urlparse(self.path)
                prefix = '/hls/{}/'.format(session.token)
                if not parsed.path.startswith(prefix):
                    self.send_error(404)
                    return
                resource_id = parsed.path[len(prefix):].split('.', 1)[0]
                resource = session.resources.get(resource_id)
                if not resource:
                    self.send_error(404)
                    return
                content_type = (
                    'application/vnd.apple.mpegurl'
                    if resource.kind == 'playlist'
                    else (resource.content_type or 'application/octet-stream')
                )
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()

            def do_GET(self):
                parsed = urlparse(self.path)
                prefix = '/hls/{}/'.format(session.token)
                if not parsed.path.startswith(prefix):
                    self.send_error(404)
                    return
                resource_id = parsed.path[len(prefix):].split('.', 1)[0]
                resource = session.resources.get(resource_id)
                if not resource:
                    self.send_error(404)
                    return
                try:
                    if resource.kind == 'playlist':
                        data, content_type = session.serve(resource_id)
                        self.send_response(200)
                        self.send_header(
                            'Content-Type',
                            content_type or 'application/vnd.apple.mpegurl',
                        )
                        self.send_header('Content-Length', str(len(data)))
                        self.send_header('Cache-Control', 'no-store')
                        self.end_headers()
                        self.wfile.write(data)
                        return
                    path, content_type = session.serve_file(resource_id)
                    size = os.path.getsize(path)
                    self.send_response(200)
                    self.send_header('Content-Type', content_type or 'application/octet-stream')
                    self.send_header('Content-Length', str(size))
                    self.send_header('Cache-Control', 'no-store')
                    self.end_headers()
                    with open(path, 'rb') as handle:
                        while True:
                            chunk = handle.read(256 * 1024)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    pass
                except Exception:
                    try:
                        self.send_error(502)
                    except Exception:
                        pass

        self._server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self._server.daemon_threads = True
        self._server_thread = threading.Thread(
            target=self._server.serve_forever,
            name='AppiHlsProxy',
            daemon=True,
        )
        self._server_thread.start()
        self._event(
            'buffer_proxy_started',
            target_seconds=self.target_seconds,
            startup_seconds=self.startup_seconds,
            recovery_seconds=self.recovery_seconds,
        )
        return self.local_url

    def stop(self, reason='stopped'):
        if self._stop.is_set():
            return
        self._stop.set()
        for track in list(self.tracks.values()):
            track.stop()
        if self._server:
            try:
                self._server.shutdown()
                self._server.server_close()
            except Exception:
                pass
        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=2.0)
        self._event('buffer_proxy_stopped', reason=reason)
        try:
            shutil.rmtree(self.root)
        except OSError:
            pass

    def _register(self, upstream_url, kind, content_type='', metadata=None, byte_range=''):
        with self._lock:
            self._resource_counter += 1
            resource_id = '{:06d}'.format(self._resource_counter)
            resource = _Resource(
                resource_id,
                upstream_url,
                kind,
                content_type,
                metadata,
                byte_range,
            )
            self.resources[resource_id] = resource
            return resource

    def _register_child(self, base_url, uri, kind, metadata=None, byte_range=''):
        upstream = hls.resolve_variant_url(base_url, uri)
        resource = self._register(
            upstream,
            kind,
            metadata=metadata,
            byte_range=byte_range,
        )
        suffix = '.m3u8' if kind == 'playlist' else ''
        return resource, self._local_url(resource.id, suffix)

    def serve(self, resource_id):
        self.last_access = time.monotonic()
        resource = self.resources[resource_id]
        if resource.kind != 'playlist':
            path, content_type = self.serve_file(resource_id)
            with open(path, 'rb') as handle:
                return handle.read(), content_type
        return self._serve_playlist(resource)

    def serve_file(self, resource_id):
        self.last_access = time.monotonic()
        resource = self.resources[resource_id]
        if resource.kind == 'segment':
            track = self.tracks.get(resource.metadata.get('track_id'))
            if not track:
                raise RuntimeError('segment track is unavailable')
            path = track.serve(_int(resource.metadata.get('index'), -1))
            return path, resource.content_type or 'video/mp2t'
        self._ensure_binary(resource)
        return resource.path, resource.content_type or 'application/octet-stream'

    def _serve_playlist(self, resource):
        fetched = _fetch(resource.upstream_url)
        text = fetched.data.decode('utf-8', errors='replace')
        self._event(
            'buffer_playlist_refresh',
            playlist_identity=_identity(resource.upstream_url),
            latency_ms=fetched.latency_ms,
            download_ms=fetched.download_ms,
            bytes=fetched.byte_count,
            http_status=fetched.status,
        )
        rewritten, track = self._rewrite_playlist(
            text,
            fetched.final_url or resource.upstream_url,
            resource,
        )
        if resource.metadata.get('representation'):
            rep = resource.metadata['representation']
            identity = rep.get('identity') or _identity(resource.upstream_url)
            if identity != self._selected_representation:
                self._selected_representation = identity
                self._event(
                    'buffer_representation_selected',
                    representation_identity=identity,
                    width=_int(rep.get('width')),
                    height=_int(rep.get('height')),
                    bandwidth=_int(rep.get('bandwidth')),
                    peak_bandwidth=_int(rep.get('peak_bandwidth')),
                    codecs=rep.get('codecs') or '',
                )
        if track and track.segments:
            ready = track.wait_startup()
            ahead, count = track._ahead(0)
            self._event(
                'buffer_startup_ready' if ready else 'buffer_startup_timeout',
                track_id=track.id,
                buffered_seconds=ahead,
                cached_segments_ahead=count,
                downloaded_segment_count=track.downloaded_total,
            )
            if not ready and not track._cached(0):
                raise RuntimeError('Unable to build buffered HLS startup reserve')
        return rewritten.encode('utf-8'), 'application/vnd.apple.mpegurl'

    def _rewrite_uri_attributes(self, line, base_url, default_kind='binary'):
        def replace(match):
            uri = (
                match.group('qvalue')
                if match.group('qvalue') is not None
                else match.group('uvalue')
            )
            tag = line.split(':', 1)[0].upper()
            kind = default_kind
            metadata = {}
            byte_range = ''
            attrs = _attributes(line.split(':', 1)[1] if ':' in line else '')
            if tag in {'#EXT-X-MEDIA', '#EXT-X-I-FRAME-STREAM-INF'}:
                kind = 'playlist'
                metadata['rendition_type'] = attrs.get('TYPE', '').lower()
            elif tag == '#EXT-X-KEY':
                kind = 'key'
            elif tag == '#EXT-X-MAP':
                kind = 'map'
                byte_range = _byterange_header(attrs.get('BYTERANGE'))
            resource, local = self._register_child(
                base_url,
                uri,
                kind,
                metadata=metadata,
                byte_range=byte_range,
            )
            return 'URI="{}"'.format(local)

        return _URI_RE.sub(replace, line)

    def _rewrite_playlist(self, text, base_url, playlist_resource):
        lines = text.splitlines()
        output = []
        media_sequence = 0
        current_duration = 0.0
        pending_stream = None
        pending_byterange = ''
        last_byterange_end = -1
        segments = []
        track_id = (
            playlist_resource.metadata.get('track_id')
            or 'track-{}'.format(playlist_resource.id)
        )
        is_media = any(line.startswith('#EXTINF:') for line in lines)
        track = self.tracks.get(track_id) if is_media else None
        if is_media and not track:
            track = _Track(
                self,
                track_id,
                self.target_seconds,
                self.startup_seconds,
                self.recovery_seconds,
            )
            self.tracks[track_id] = track
            playlist_resource.metadata['track_id'] = track_id

        for raw in lines:
            stripped = raw.strip()
            if stripped.startswith('#EXT-X-MEDIA-SEQUENCE:'):
                media_sequence = _int(stripped.split(':', 1)[1], 0)
                output.append(raw)
                continue
            if stripped.startswith('#EXTINF:'):
                current_duration = _float(
                    stripped.split(':', 1)[1].split(',', 1)[0],
                    0.0,
                )
                output.append(raw)
                continue
            if stripped.startswith('#EXT-X-BYTERANGE:'):
                pending_byterange, last_byterange_end = _byterange(
                    stripped.split(':', 1)[1],
                    last_byterange_end,
                )
                continue
            if stripped.startswith('#EXT-X-STREAM-INF:'):
                pending_stream = _attributes(stripped.split(':', 1)[1])
                output.append(raw)
                continue
            if stripped.startswith('#'):
                if 'URI=' in stripped.upper():
                    output.append(self._rewrite_uri_attributes(raw, base_url))
                else:
                    output.append(raw)
                continue
            if not stripped:
                output.append(raw)
                continue

            if pending_stream is not None:
                width = height = 0
                resolution = pending_stream.get('RESOLUTION') or ''
                if 'x' in resolution.lower():
                    try:
                        width, height = [
                            int(value)
                            for value in resolution.lower().split('x', 1)
                        ]
                    except (TypeError, ValueError):
                        width = height = 0
                upstream = hls.resolve_variant_url(base_url, stripped)
                rep = {
                    'identity': _identity(upstream),
                    'width': width,
                    'height': height,
                    'bandwidth': _int(
                        pending_stream.get('AVERAGE-BANDWIDTH')
                        or pending_stream.get('BANDWIDTH')
                    ),
                    'peak_bandwidth': _int(pending_stream.get('BANDWIDTH')),
                    'codecs': pending_stream.get('CODECS') or '',
                }
                resource = self._register(
                    upstream,
                    'playlist',
                    metadata={'representation': rep},
                )
                output.append(self._local_url(resource.id, '.m3u8'))
                pending_stream = None
                continue

            if is_media:
                index = len(segments)
                sequence = media_sequence + index
                upstream = hls.resolve_variant_url(base_url, stripped)
                resource = self._register(
                    upstream,
                    'segment',
                    metadata={
                        'track_id': track_id,
                        'index': index,
                        'sequence': sequence,
                    },
                    byte_range=pending_byterange,
                )
                segments.append(_Segment(resource, sequence, current_duration, index))
                output.append(self._local_url(resource.id))
                current_duration = 0.0
                pending_byterange = ''
            else:
                _, local = self._register_child(base_url, stripped, 'playlist')
                output.append(local)

        if track:
            track.replace_segments(segments)
        return '\n'.join(output) + ('\n' if text.endswith('\n') else ''), track

    def _ensure_binary(self, resource, segment=None, track=None):
        with resource.condition:
            if resource.path and os.path.isfile(resource.path):
                return resource.path
            if resource.fetching:
                deadline = time.monotonic() + RECOVERY_TIMEOUT
                while resource.fetching and time.monotonic() < deadline:
                    resource.condition.wait(timeout=0.25)
                if resource.path and os.path.isfile(resource.path):
                    return resource.path
                if resource.error:
                    raise RuntimeError(resource.error)
            resource.fetching = True
            resource.error = ''
        try:
            path = os.path.join(self.data_root, '{}.bin'.format(resource.id))
            fetched = _fetch_to_path(
                resource.upstream_url,
                path,
                byte_range=resource.byte_range,
            )
            resource.path = path
            resource.content_type = fetched.content_type or resource.content_type
            fields = {
                'resource_kind': resource.kind,
                'latency_ms': fetched.latency_ms,
                'download_ms': fetched.download_ms,
                'bytes': fetched.byte_count,
                'throughput_mbps': fetched.throughput_mbps,
                'http_status': fetched.status,
            }
            if segment is not None:
                fields.update({
                    'track_id': track.id if track else resource.metadata.get('track_id'),
                    'segment_sequence': segment.sequence,
                    'segment_duration': round(segment.duration, 3),
                })
                if track:
                    ahead, count = track._ahead(segment.index)
                    fields['buffered_seconds'] = ahead
                    fields['cached_segments_ahead'] = count
            self._event(
                'buffer_segment_download' if segment is not None else 'buffer_resource_download',
                **fields
            )
            self._enforce_disk_limit()
            return path
        except Exception as exc:
            resource.error = '{}: {}'.format(type(exc).__name__, exc)
            raise
        finally:
            with resource.condition:
                resource.fetching = False
                resource.condition.notify_all()

    def _enforce_disk_limit(self):
        total = 0
        files = []
        try:
            for name in os.listdir(self.data_root):
                path = os.path.join(self.data_root, name)
                if os.path.isfile(path):
                    stat = os.stat(path)
                    total += stat.st_size
                    files.append((stat.st_mtime, path, stat.st_size))
        except OSError:
            return
        if total <= MAX_SESSION_BYTES:
            return
        active_paths = set()
        for track in self.tracks.values():
            start = max(0, track.last_served - 2)
            for seg in track.segments[start:]:
                if seg.resource.path:
                    active_paths.add(seg.resource.path)
        for _, path, size in sorted(files):
            if total <= MAX_SESSION_BYTES or path in active_paths:
                continue
            try:
                os.remove(path)
                total -= size
            except OSError:
                pass


class BufferedHlsManager:
    def __init__(self, root=None):
        self.root = root or _root_path()
        self.control = os.path.join(self.root, 'control')
        self.active = None
        self._pending_events = []
        _ensure(self.control)
        self._cleanup_stale()

    def _cleanup_stale(self):
        try:
            names = os.listdir(self.root)
        except OSError:
            return
        for name in names:
            path = os.path.join(self.root, name)
            if name.startswith('session-') and os.path.isdir(path):
                try:
                    shutil.rmtree(path)
                except OSError:
                    pass
            elif name.startswith('response-') and name.endswith('.json'):
                try:
                    os.remove(path)
                except OSError:
                    pass

    def poll(self):
        request_path = os.path.join(self.control, 'request.json')
        request = _json_read(request_path)
        if request:
            try:
                os.remove(request_path)
            except OSError:
                pass
            request_id = request.get('id') or ''
            response_path = os.path.join(
                self.control,
                'response-{}.json'.format(request_id),
            )
            try:
                self.stop_active('replaced')
                session = BufferedHlsSession(
                    request.get('source_url') or '',
                    target_seconds=request.get('target_seconds') or DEFAULT_TARGET_SECONDS,
                    startup_seconds=request.get('startup_seconds') or DEFAULT_STARTUP_SECONDS,
                    root=os.path.join(
                        self.root,
                        'session-{}'.format(secrets.token_hex(12)),
                    ),
                )
                local_url = session.start()
                self.active = session
                _json_write(response_path, {'id': request_id, 'local_url': local_url})
            except Exception as exc:
                _json_write(
                    response_path,
                    {
                        'id': request_id,
                        'error': '{}: {}'.format(type(exc).__name__, exc),
                    },
                )
        if (
            self.active
            and time.monotonic() - self.active.last_access > STALE_SESSION_SECONDS
        ):
            self.stop_active('idle-timeout')

    def flush_diagnostics(self, diagnostic_event):
        pending = self._pending_events
        self._pending_events = []
        if self.active:
            pending.extend(self.active.drain_events())
        for name, fields in pending:
            diagnostic_event(name, **fields)

    def stop_active(self, reason='stopped'):
        session = self.active
        if not session:
            return []
        session.stop(reason)
        events = session.drain_events()
        self._pending_events.extend(events)
        self.active = None
        return events

    def shutdown(self, diagnostic_event=None):
        self.stop_active('service-shutdown')
        if diagnostic_event:
            self.flush_diagnostics(diagnostic_event)
