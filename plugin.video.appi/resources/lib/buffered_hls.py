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
DEFAULT_STARTUP_SECONDS = 12.0
DEFAULT_RECOVERY_SECONDS = 6.0
REQUEST_TIMEOUT = 10.0
RECOVERY_TIMEOUT = 20.0
CONTROL_TIMEOUT = 65.0
STALE_SESSION_SECONDS = 90.0
MAX_SESSION_BYTES = 384 * 1024 * 1024
DEFAULT_BUFFER_MB = 128
STARTUP_TIMEOUT = 45.0
_USER_AGENT = 'Kodi Appi Buffered/0.7.19'
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


class PlaybackCancelled(Exception):
    pass


def buffer_size_mb(value):
    return min(1024, max(32, _int(value, DEFAULT_BUFFER_MB)))


def request_playback(source_url, target_seconds=DEFAULT_TARGET_SECONDS,
                     startup_seconds=DEFAULT_STARTUP_SECONDS, timeout=CONTROL_TIMEOUT,
                     buffer_mb=DEFAULT_BUFFER_MB, quality='highest'):
    # Unique mailboxes prevent a cancelled/late reply being used by a retry.
    import xbmc
    import xbmcgui
    control = os.path.join(_root_path(), 'control')
    _ensure(control)
    request_id = secrets.token_hex(12)
    request_path = os.path.join(control, 'request-' + request_id + '.json')
    response_path = os.path.join(control, 'response-' + request_id + '.json')
    cancel_path = os.path.join(control, 'cancel-' + request_id + '.json')
    dialog = xbmcgui.DialogProgress()
    dialog.create('Appi — Buffered Look Ahead', 'Preparing stream…')
    monitor = xbmc.Monitor()
    success = False
    _json_write(request_path, {
        'id': request_id, 'source_url': source_url,
        'target_seconds': target_seconds, 'startup_seconds': startup_seconds,
        'buffer_mb': buffer_size_mb(buffer_mb), 'quality': quality,
        'created_at': time.time(),
    })
    deadline = time.monotonic() + timeout
    chosen = False
    try:
        while time.monotonic() < deadline:
            if dialog.iscanceled() or monitor.abortRequested():
                raise PlaybackCancelled()
            response = _json_read(response_path) or {}
            if response.get('error'):
                raise RuntimeError(response['error'])
            if response.get('choices') and not chosen:
                dialog.close()
                selection = xbmcgui.Dialog().select('Buffered Look Ahead quality', response['choices'])
                if selection < 0:
                    raise PlaybackCancelled()
                _json_write(os.path.join(control, 'choice-' + request_id + '.json'), {'index': selection})
                chosen = True
                deadline = time.monotonic() + timeout
                dialog.create('Appi — Buffered Look Ahead', 'Filling buffer…')
            if response.get('ready') and response.get('local_url'):
                dialog.update(100, 'Buffer ready — starting playback…')
                success = True
                return response['local_url']
            dialog.update(int(response.get('percent', 0)), response.get('message', 'Preparing stream…'))
            monitor.waitForAbort(0.1)
        raise RuntimeError('Stream preparation timed out. Please try again or choose a lower quality.')
    finally:
        dialog.close()
        if not success:
            _json_write(cancel_path, {'id': request_id})
        for path in (request_path, response_path):
            try:
                os.remove(path)
            except OSError:
                pass


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
        chunks = []
        size = 0
        while True:
            if time.monotonic() - started > timeout:
                raise TimeoutError('Playlist transfer timed out')
            chunk = response.read1(65536)
            if not chunk:
                break
            size += len(chunk)
            if size > 8 * 1024 * 1024:
                raise RuntimeError('Playlist exceeds safety limit')
            chunks.append(chunk)
        data = b''.join(chunks)
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


def _fetch_to_path(url, path, timeout=REQUEST_TIMEOUT, byte_range='', stop=None, max_bytes=MAX_SESSION_BYTES):
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
            if byte_range and _safe_status(response) != 206:
                raise RuntimeError('Provider did not honor the media byte range')
            expected_length = _int(response.headers.get('Content-Length'), -1)
            with open(temp, 'wb') as handle:
                while True:
                    if (stop and stop.is_set()) or time.monotonic() - started > timeout:
                        raise TimeoutError('Segment transfer cancelled or timed out')
                    chunk = response.read1(256 * 1024)
                    if not chunk:
                        break
                    byte_count += len(chunk)
                    if byte_count > max_bytes:
                        raise RuntimeError('Segment exceeds configured buffer capacity')
                    handle.write(chunk)
            if byte_count == 0 or (expected_length >= 0 and byte_count != expected_length):
                raise RuntimeError('Provider returned an empty or incomplete media segment')
            finished = time.monotonic()
            final_url = _with_kodi_options(response.geturl(), kodi_options)
            content_type = (response.headers.get('Content-Type', '') or '').split(';', 1)[0].strip().lower()
            status = _safe_status(response)
        if stop and stop.is_set():
            raise PlaybackCancelled()
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


def _remove_attribute(line, name):
    """Remove one HLS attribute without disturbing quoted commas/order."""
    if ':' not in line:
        return line
    head, body = line.split(':', 1)
    parts = []
    token = []
    quoted = False
    for char in body:
        if char == '"':
            quoted = not quoted
        if char == ',' and not quoted:
            parts.append(''.join(token))
            token = []
        else:
            token.append(char)
    parts.append(''.join(token))
    prefix = str(name).upper() + '='
    kept = [part for part in parts if not part.strip().upper().startswith(prefix)]
    return head + ':' + ','.join(kept)


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
        self.recovering = False
        self._serve_lock = threading.Lock()
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

    def ahead_bytes(self, start=None):
        start = max(0, self.last_served + 1 if start is None else start)
        total = 0
        for seg in self.segments[start:]:
            if not self._cached(seg.index):
                break
            try:
                total += os.path.getsize(seg.resource.path)
            except OSError:
                break
        return total

    def _next_missing(self):
        start = max(0, self.last_served + 1)

        # During preparation every required track gets a fair chance to reach
        # its playable startup reserve. Without this gate, a fast video track
        # can monopolize the session-wide download lock and fill most of the
        # byte budget while associated audio remains empty.
        if not self.session._startup_complete:
            ahead, _ = self._ahead(start)
            remaining = sum(seg.duration for seg in self.segments[start:])
            threshold = min(self.startup_seconds, remaining)
            if threshold <= 0 or ahead >= threshold:
                return None

        # After startup, byte capacity determines lookahead rather than a
        # fixed seconds ceiling.
        budget = self.session.max_bytes * 0.70 / max(1, len(self.session.tracks))
        total = 0
        for index in range(start, len(self.segments)):
            if total >= budget:
                return None
            if not self._cached(index):
                return index
            try:
                total += os.path.getsize(self.segments[index].resource.path)
            except OSError:
                return index
        return None

    def _prefetch_loop(self):
        while not self._stop.is_set() and not self.session._stop.is_set():
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
                    http_status=getattr(exc, 'code', None),
                )
                if self._stop.wait(0.5):
                    break

    def _reserve_state(self, index, reserve_seconds):
        ahead, count = self._ahead(index)
        remaining = sum(seg.duration for seg in self.segments[index:])
        threshold = min(reserve_seconds, remaining)
        capacity_reached = (
            index < len(self.segments)
            and self._cached(index)
            and self._next_missing() is None
        )
        ready = (
            ahead >= threshold
            or capacity_reached
            or (remaining <= 0 and index >= len(self.segments))
        )
        return ahead, count, threshold, ready

    def wait_startup(self, timeout=RECOVERY_TIMEOUT):
        return self._wait_for_reserve(0, self.startup_seconds, timeout)

    def _wait_for_reserve(self, index, reserve_seconds, timeout):
        deadline = time.monotonic() + max(1.0, timeout)
        with self._condition:
            if self.last_served < index - 1:
                self.last_served = index - 1
            self._condition.notify_all()
            while not self._stop.is_set():
                _, _, _, ready = self._reserve_state(index, reserve_seconds)
                if ready:
                    return True
                if time.monotonic() >= deadline:
                    return False
                self._condition.wait(timeout=0.25)
        return False

    def serve(self, index):
        # Serialize segment demand within a rendition; seeks cannot move its
        # cursor under another request's reserve wait.
        with self._serve_lock:
            return self._serve_segment(index)

    def _serve_segment(self, index):
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
        if not self._cached(index):
            self.recovering = True
            self.session._event(
                'buffer_depletion',
                track_id=self.id,
                buffered_seconds=ahead,
                cached_segments_ahead=count,
                requested_index=index,
            )
            recovered = self._wait_for_reserve(index, self.recovery_seconds, RECOVERY_TIMEOUT)
            self.recovering = False
            if not recovered:
                raise TimeoutError('Unable to refill the stream buffer within 20 seconds')
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
            if path and path not in self.session._pins and segment.resource.id not in self.session._serving and os.path.isfile(path):
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
        buffer_mb=DEFAULT_BUFFER_MB,
        quality='highest',
    ):
        self.source_url = source_url
        self.max_bytes = buffer_size_mb(buffer_mb) * 1024 * 1024
        self.quality = quality
        self.choices = []
        self.choice = None
        self.choice_event = threading.Event()
        self.ready = False
        self.error = ''
        self.started_playback = False
        self.created_at = time.monotonic()
        self._prepare_thread = None
        self._download_lock = threading.Lock()
        self._playlist_lock = threading.RLock()
        self._playlist_cache = {}
        self._pins = set()
        self._serving = set()
        self._registry = {}
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
        self._selected_variant_attrs = {}
        self._startup_track_ids = []
        self._startup_complete = False
        self.master = self._register(source_url, 'playlist', metadata={'root': True})

    def _required_startup_tracks(self):
        if self._startup_track_ids:
            return [
                self.tracks[track_id]
                for track_id in self._startup_track_ids
                if track_id in self.tracks
            ]
        return list(self.tracks.values())

    def status(self):
        tracks = list(self.tracks.values())
        required = self._required_startup_tracks()
        states = [track._reserve_state(0, track.startup_seconds) for track in required]
        seconds = min((state[0] for state in states), default=0)
        ratios = []
        for ahead, _, threshold, ready in states:
            if ready:
                ratios.append(1.0)
            elif threshold > 0:
                ratios.append(min(1.0, ahead / threshold))
            else:
                ratios.append(0.0)
        percent = 100 if self.ready else min(99, int(min(ratios, default=0.0) * 100))
        stalled = any(track.failed for track in required)
        message = (
            'Buffer ready — starting playback…'
            if self.ready
            else 'Buffering stalled; retrying…'
            if stalled
            else 'Filling buffer…'
            if tracks
            else 'Preparing stream…'
        )
        return {
            'ready': self.ready, 'error': self.error, 'local_url': self.local_url,
            'choices': self.choices if not self.choice_event.is_set() else [],
            'message': message,
            'percent': percent,
            'cached_ahead_bytes': sum(t.ahead_bytes() for t in tracks),
            'buffered_seconds': seconds,
            'cached_segments_ahead': sum(t._ahead()[1] for t in tracks),
            'buffer_capacity_mb': self.max_bytes // (1024 * 1024),
            'recovering': any(t.recovering for t in tracks),
            'startup_tracks': len(required),
        }

    def fail(self, message, error_type='PlaybackError'):
        if not self.error and not self._stop.is_set():
            self.error = message
            self._event('buffer_failure', error_type=error_type)

    def _prepare_associated_media(self):
        # Audio/video rendition groups are part of the playable stream.
        # Preload the selected/default member so readiness means Kodi can read
        # picture and sound immediately. Subtitle groups intentionally do not
        # gate startup.
        for rendition_type, attribute in (('audio', 'AUDIO'), ('video', 'VIDEO')):
            group_id = (self._selected_variant_attrs.get(attribute) or '').strip()
            if not group_id:
                continue
            candidates = [
                resource for resource in list(self.resources.values())
                if resource.kind == 'playlist'
                and resource.metadata.get('rendition_type') == rendition_type
                and resource.metadata.get('group_id') == group_id
            ]
            if not candidates:
                continue
            chosen = next(
                (resource for resource in candidates if resource.metadata.get('default')),
                next(
                    (resource for resource in candidates if resource.metadata.get('autoselect')),
                    candidates[0],
                ),
            )
            self.serve(chosen.id)

    def prepare(self):
        try:
            self.serve(self.master.id)
            variants = [r for r in list(self.resources.values()) if r.metadata.get('representation')]
            if variants:
                self.serve(variants[0].id)
            self._prepare_associated_media()
            if self._stop.is_set():
                return

            tracks = list(self.tracks.values())
            if not tracks or not any(t.segments for t in tracks):
                raise RuntimeError('Stream contains no playable media segments')
            self._startup_track_ids = [track.id for track in tracks]

            # One global deadline governs the complete playable reserve.
            deadline = time.monotonic() + STARTUP_TIMEOUT
            while not self._stop.is_set():
                required = self._required_startup_tracks()
                states = [
                    track._reserve_state(0, track.startup_seconds)
                    for track in required
                ]
                if states and all(state[3] for state in states):
                    break
                if time.monotonic() >= deadline:
                    failures = [
                        '{}: {}'.format(track.id, track.failed)
                        for track in required if track.failed
                    ]
                    detail = '; '.join(failures[:2])
                    raise TimeoutError(
                        'Startup reserve incomplete{}'.format(
                            ': ' + detail if detail else ''
                        )
                    )
                self._stop.wait(0.1)

            if self._stop.is_set():
                return
            self._startup_complete = True
            for track in list(self.tracks.values()):
                with track._condition:
                    track._condition.notify_all()
            self.ready = True
            self.last_access = time.monotonic()
            self._event('buffer_startup_ready', **{k: v for k, v in self.status().items()
                        if k in {'buffered_seconds', 'cached_ahead_bytes',
                                 'buffer_capacity_mb', 'startup_tracks'}})
        except PlaybackCancelled:
            return
        except Exception as exc:
            detail = str(exc).strip()
            message = 'Unable to prepare stream: {}'.format(type(exc).__name__)
            if detail:
                message += ': ' + detail
            self.fail(message + '. Try again or choose a lower quality.', type(exc).__name__)

    @property
    def local_url(self):
        if not self._server:
            return ''
        return self._local_url(self.master.id, '.m3u8')

    def _local_url(self, resource_id, suffix=''):
        if not suffix:
            resource = self.resources.get(resource_id)
            if resource:
                core = resource.upstream_url.split('|', 1)[0]
                extension = os.path.splitext(urlparse(core).path)[1].lower()
                allowed = {'.ts', '.aac', '.ac3', '.eac3', '.mp3', '.mp4', '.m4s',
                           '.m4a', '.vtt', '.webvtt', '.m3u8', '.cmfv', '.cmfa'}
                suffix = extension if extension in allowed else {
                    'playlist': '.m3u8', 'map': '.mp4', 'key': '.key',
                    'segment': resource.metadata.get('suffix', '.ts'),
                }.get(resource.kind, '.bin')
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

            def handle(self):
                self.connection.settimeout(30)
                try:
                    super().handle()
                except (BrokenPipeError, ConnectionResetError, TimeoutError):
                    pass

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
                session._serving.add(resource_id)
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
                    with session._download_lock:
                        handle = open(path, 'rb')
                        size = os.fstat(handle.fileno()).st_size
                        session._pins.add(path)
                    try:
                        start, end = 0, size - 1
                        requested = self.headers.get('Range', '')
                        if requested:
                            match = re.fullmatch(r'bytes=(\d+)-(\d*)', requested)
                            if not match or int(match.group(1)) >= size:
                                self.send_response(416)
                                self.send_header('Content-Range', 'bytes */{}'.format(size))
                                self.send_header('Content-Length', '0')
                                self.end_headers()
                                return
                            start = int(match.group(1))
                            end = min(size - 1, int(match.group(2))) if match.group(2) else size - 1
                            if end < start:
                                self.send_error(416)
                                return
                        self.send_response(206 if requested else 200)
                        self.send_header('Content-Type', content_type or 'application/octet-stream')
                        self.send_header('Content-Length', str(end - start + 1))
                        self.send_header('Accept-Ranges', 'bytes')
                        if requested:
                            self.send_header('Content-Range', 'bytes {}-{}/{}'.format(start, end, size))
                        self.send_header('Cache-Control', 'no-store')
                        self.end_headers()
                        handle.seek(start)
                        remaining = end - start + 1
                        while remaining > 0:
                            chunk = handle.read(min(256 * 1024, remaining))
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                            remaining -= len(chunk)
                    finally:
                        handle.close()
                        session._pins.discard(path)
                except (BrokenPipeError, ConnectionResetError):
                    pass
                except Exception as exc:
                    session.fail('Buffered stream failed ({}). Please retry playback.'.format(type(exc).__name__), type(exc).__name__)
                    try:
                        self.send_error(502)
                    except Exception:
                        pass
                finally:
                    session._serving.discard(resource_id)

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
        self.choice_event.set()
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
        if self._prepare_thread and self._prepare_thread.is_alive():
            self._prepare_thread.join(timeout=0.2)
        self._event('buffer_proxy_stopped', reason=reason)
        try:
            shutil.rmtree(self.root)
        except OSError:
            pass

    def _register(self, upstream_url, kind, content_type='', metadata=None, byte_range=''):
        with self._lock:
            key = (upstream_url, kind, byte_range, (metadata or {}).get('track_id'))
            if key in self._registry:
                resource = self._registry[key]
                resource.metadata.update(metadata or {})
                return resource
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
            self._registry[key] = resource
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
        with self._playlist_lock:
            return self._load_playlist(resource)

    def _load_playlist(self, resource):
        if self._stop.is_set():
            raise PlaybackCancelled()
        cached = self._playlist_cache.get(resource.id)
        if cached and (cached[2] or time.monotonic() - cached[0] < 2):
            return cached[1], 'application/vnd.apple.mpegurl'
        fetched = _fetch(resource.upstream_url)
        if self._stop.is_set():
            raise PlaybackCancelled()
        text = fetched.data.decode('utf-8-sig', errors='replace')
        if not text.lstrip().startswith('#EXTM3U'):
            raise RuntimeError('Provider did not return an HLS playlist')
        if resource is self.master:
            text = self._select_variant(text)
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
        data = rewritten.encode('utf-8')
        self._playlist_cache[resource.id] = (time.monotonic(), data,
                                             '#EXT-X-ENDLIST' in text or '#EXT-X-STREAM-INF:' in text)
        return data, 'application/vnd.apple.mpegurl'

    def _select_variant(self, text):
        lines = text.splitlines()
        variants = []
        pending = None
        for i, line in enumerate(lines):
            if line.startswith('#EXT-X-STREAM-INF:'):
                pending = (i, _attributes(line.split(':', 1)[1]))
            elif pending and line.strip() and not line.startswith('#'):
                variants.append((pending[0], i, pending[1]))
                pending = None
        if not variants:
            return text
        if self.quality == 'prompt' and len(variants) > 1:
            self.choices = [
                '{} — {}'.format(v[2].get('RESOLUTION', 'Resolution unknown'),
                  '{:.2f} Mbit/s peak'.format(_int(v[2].get('BANDWIDTH')) / 1000000)
                  if _int(v[2].get('BANDWIDTH')) > 0 else 'Bitrate unknown')
                for v in variants]
            # User time in the chooser is distinct from network timeout.
            if not self.choice_event.wait(180) or self._stop.is_set():
                raise PlaybackCancelled()
            selected = _int(self.choice, -1)
            if not 0 <= selected < len(variants):
                raise PlaybackCancelled()
        else:
            selected = max(range(len(variants)), key=lambda i: max(0, _int(variants[i][2].get('BANDWIDTH'))))
        keep = variants[selected]
        self._selected_variant_attrs = dict(keep[2])
        discarded = {n for v in variants if v != keep for n in (v[0], v[1])}
        self._event('buffer_quality_selected', quality_behavior=self.quality,
                    advertised_bandwidth=_int(keep[2].get('BANDWIDTH')),
                    resolution=keep[2].get('RESOLUTION', 'unknown'))
        return '\n'.join(line for i, line in enumerate(lines) if i not in discarded) + '\n'

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
                metadata.update({
                    'rendition_type': attrs.get('TYPE', '').lower(),
                    'group_id': attrs.get('GROUP-ID', ''),
                    'name': attrs.get('NAME', ''),
                    'language': attrs.get('LANGUAGE', ''),
                    'default': attrs.get('DEFAULT', '').upper() == 'YES',
                    'autoselect': attrs.get('AUTOSELECT', '').upper() == 'YES',
                })
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

        rewritten = _URI_RE.sub(replace, line)
        tag = line.split(':', 1)[0].upper()
        attrs = _attributes(line.split(':', 1)[1] if ':' in line else '')
        if tag == '#EXT-X-MAP' and attrs.get('BYTERANGE'):
            # The proxy resource already contains only the requested upstream
            # byte slice, so leaving BYTERANGE would apply the range twice.
            rewritten = _remove_attribute(rewritten, 'BYTERANGE')
        return rewritten

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
                        'suffix': '.m4s' if any(line.startswith('#EXT-X-MAP:') for line in lines) else '.ts',
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
        with self._download_lock:
            if self._stop.is_set():
                raise PlaybackCancelled()
            return self._download_binary(resource, segment, track)

    def _download_binary(self, resource, segment=None, track=None):
        if resource.path and os.path.isfile(resource.path):
            return resource.path
        resource.fetching = True
        resource.error = ''
        try:
            path = os.path.join(self.data_root, '{}.bin'.format(resource.id))
            segment_limit = max(1, self.max_bytes // max(4, len(self.tracks) * 4))
            self._enforce_disk_limit(limit=self.max_bytes - segment_limit)
            if self.disk_bytes() > self.max_bytes - segment_limit:
                raise RuntimeError('Buffer capacity is temporarily occupied')
            fetched = _fetch_to_path(
                resource.upstream_url,
                path,
                byte_range=resource.byte_range,
                stop=self._stop, max_bytes=segment_limit,
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
            self._enforce_disk_limit(protected=path)
            return path
        except Exception as exc:
            resource.error = '{}: {}'.format(type(exc).__name__, exc)
            raise
        finally:
            with resource.condition:
                resource.fetching = False
                resource.condition.notify_all()

    def disk_bytes(self):
        total = 0
        for resource in list(self.resources.values()):
            try:
                total += os.path.getsize(resource.path)
            except OSError:
                pass
        return total

    def _enforce_disk_limit(self, protected=None, limit=None):
        limit = self.max_bytes if limit is None else limit
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
        if total <= limit:
            return
        # Remove least useful segments first: consumed / remote seek windows.
        priorities = {}
        for track in list(self.tracks.values()):
            for seg in track.segments:
                priorities[seg.resource.path] = (abs(seg.index - (track.last_served + 1)))
        for _, path, size in sorted(files, key=lambda f: priorities.get(f[1], -1), reverse=True):
            if total <= limit:
                break
            serving_paths = {self.resources[r].path for r in list(self._serving) if r in self.resources}
            if path == protected or path in self._pins or path in serving_paths or path.endswith('.part'):
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
        self._lock = threading.RLock()
        _ensure(self.control)
        self._cleanup_stale()

    def _cleanup_stale(self):
        for name in os.listdir(self.control):
            try:
                path = os.path.join(self.control, name)
                if name == 'request.json' or time.time() - os.path.getmtime(path) > 240:
                    os.remove(path)
            except OSError:
                pass
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

    def poll(self, player_active=False):
        with self._lock:
            self._poll(player_active)

    def _poll(self, player_active=False):
        # Process only fresh requests. No folder/navigation state is consulted.
        requests = []
        for name in os.listdir(self.control):
            path = os.path.join(self.control, name)
            if name.startswith('request-') and name.endswith('.json'):
                request = _json_read(path)
                if request:
                    requests.append((request.get('created_at', 0), path, request))
        for created, path, request in sorted(requests):
            os.remove(path)
            request_id = request.get('id', '')
            if not re.fullmatch('[a-f0-9]{24}', request_id):
                continue
            cancel = os.path.join(self.control, 'cancel-' + request_id + '.json')
            if time.time() - created > CONTROL_TIMEOUT or os.path.exists(cancel):
                continue
            self.stop_active('replaced')
            session = BufferedHlsSession(
                request.get('source_url') or '',
                target_seconds=request.get('target_seconds') or DEFAULT_TARGET_SECONDS,
                startup_seconds=request.get('startup_seconds') or DEFAULT_STARTUP_SECONDS,
                buffer_mb=request.get('buffer_mb', DEFAULT_BUFFER_MB),
                quality=request.get('quality', 'highest'),
                root=os.path.join(self.root, 'session-' + secrets.token_hex(12)))
            session.request_id = request_id
            session.start()
            self.active = session
            session._prepare_thread = threading.Thread(target=session.prepare, daemon=True,
                                                       name='AppiHlsPrepare')
            session._prepare_thread.start()
        session = self.active
        if session:
            request_id = session.request_id
            cancel = os.path.join(self.control, 'cancel-' + request_id + '.json')
            choice = os.path.join(self.control, 'choice-' + request_id + '.json')
            selection = _json_read(choice)
            if selection is not None:
                session.choice = selection.get('index', -1)
                session.choice_event.set()
                os.remove(choice)
                session.created_at = time.monotonic()
            if os.path.exists(cancel):
                self.stop_active('cancelled')
            else:
                elapsed = time.monotonic() - session.created_at
                if not session.ready and elapsed > CONTROL_TIMEOUT and not (session.choices and not session.choice_event.is_set()):
                    session.fail('Stream preparation did not return a result in time. Please retry playback.', 'ControlTimeout')
                if session.ready and not session.started_playback and time.monotonic() - session.last_access > 30:
                    session.fail('Kodi did not start the prepared stream. Please retry playback.', 'PlayerStartTimeout')
                response = os.path.join(self.control, 'response-' + request_id + '.json')
                _json_write(response, session.status())
                if session.error:
                    # Startup caller displays its own error. Playback errors need
                    # visible feedback even when Kodi never calls onPlayBackError.
                    if session.ready:
                        import xbmcgui
                        xbmcgui.Dialog().notification('Appi Buffered Look Ahead', session.error, time=6000)
                    self.stop_active('error', keep_response=True)
                elif not player_active and session.started_playback and time.monotonic() - session.last_access > 10:
                    self.stop_active('player-idle')
        # Retire orphaned control files without affecting new sessions.
        for name in os.listdir(self.control):
            path = os.path.join(self.control, name)
            try:
                if time.time() - os.path.getmtime(path) > 240:
                    os.remove(path)
            except OSError:
                pass

    def playback_started(self, url):
        session = self.active
        if session and '/hls/' + session.token + '/' in (url or ''):
            session.started_playback = True
            return session.token
        return None

    def playback_finished(self, token, reason):
        # A stop/error event from the previous Kodi player must not kill a
        # replacement that has not yet reached AVStarted.
        with self._lock:
            if self.active and token == self.active.token:
                self.stop_active(reason)

    def flush_diagnostics(self, diagnostic_event):
        pending = self._pending_events
        self._pending_events = []
        if self.active:
            pending.extend(self.active.drain_events())
        for name, fields in pending:
            diagnostic_event(name, **fields)

    def stop_active(self, reason='stopped', keep_response=False):
        with self._lock:
            return self._stop_active(reason, keep_response)

    def _stop_active(self, reason, keep_response):
        session = self.active
        if not session:
            return []
        session.stop(reason)
        events = session.drain_events()
        self._pending_events.extend(events)
        self.active = None
        request_id = getattr(session, 'request_id', '')
        for prefix in ('request-', 'choice-', 'cancel-', 'response-'):
            if keep_response and prefix == 'response-':
                continue
            try:
                os.remove(os.path.join(self.control, prefix + request_id + '.json'))
            except OSError:
                pass
        return events

    def shutdown(self, diagnostic_event=None):
        self.stop_active('service-shutdown')
        if diagnostic_event:
            self.flush_diagnostics(diagnostic_event)
