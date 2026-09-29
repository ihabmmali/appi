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
# urllib's timeout is treated as an inactivity/no-progress bound for media.
# Media transfers are no longer aborted because total wall-clock time exceeds it.
REQUEST_TIMEOUT = 15.0
RECOVERY_TIMEOUT = 20.0
CONTROL_TIMEOUT = 210.0
STALE_SESSION_SECONDS = 90.0
MAX_SESSION_BYTES = 384 * 1024 * 1024
DEFAULT_BUFFER_MB = 128
STARTUP_TIMEOUT = 180.0
HIGH_WATER_RATIO = 0.80
STARTUP_WATER_RATIO = 0.50
LOW_WATER_RATIO = 0.60
CRITICAL_WATER_RATIO = 0.15
MIN_SEEK_RESERVE_BYTES = 4 * 1024 * 1024
SEEK_RESERVE_SECONDS = 12.0
PREFETCH_LEAD_SECONDS = 24.0
_USER_AGENT = 'Kodi Appi Buffered/0.7.22'
_URI_RE = re.compile(r'URI=(?P<quoted>"(?P<qvalue>[^"]*)"|(?P<uvalue>[^,]*))', re.IGNORECASE)
_ATTR_RE = re.compile(r'([A-Z0-9-]+)=(?:"([^"]*)"|([^,]*))', re.IGNORECASE)


class RecoveryTimeout(TimeoutError):
    """A request was superseded by a newer playback epoch."""


class RecoveryExhausted(RecoveryTimeout):
    """Appi-owned recovery policy was exhausted for the active epoch."""


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


class _EpochStop:
    """Cancellation view for one buffer epoch plus the whole session."""

    def __init__(self, session, epoch):
        self.session = session
        self.epoch = int(epoch)

    def is_set(self):
        return self.session._stop.is_set() or self.epoch != self.session.epoch


def _human_bytes(value):
    value = max(0, int(value or 0))
    if value < 1024 * 1024:
        return '{:.0f} KB'.format(value / 1024.0)
    return '{:.1f} MB'.format(value / 1048576.0)


def buffer_size_mb(value):
    return min(1024, max(32, _int(value, DEFAULT_BUFFER_MB)))


_TUNING_DEFAULTS = {
    'startup_pct': 50,
    'high_water_pct': 80,
    'low_water_pct': 60,
    'critical_pct': 15,
    'media_timeout_s': 15,
    'startup_timeout_s': 180,
    'seek_reserve_s': 12,
    'min_seek_reserve_mb': 4,
    'prefetch_lead_s': 24,
    'recovery_timeout_s': 60,
    'retry_delay_ms': 500,
    'retry_attempts': 0,
    'recovery_reserve_s': 6,
    'pause_retention_min': 0,
}


def validated_tuning(values=None):
    values = dict(values or {})
    result = dict(_TUNING_DEFAULTS)
    limits = {
        'startup_pct': (1, 100), 'high_water_pct': (1, 100),
        'low_water_pct': (1, 99), 'critical_pct': (0, 98),
        'media_timeout_s': (1, 120), 'startup_timeout_s': (30, 600),
        'seek_reserve_s': (1, 120), 'min_seek_reserve_mb': (1, 256),
        'prefetch_lead_s': (0, 120), 'recovery_timeout_s': (5, 600),
        'retry_delay_ms': (100, 10000), 'retry_attempts': (0, 100),
        'recovery_reserve_s': (1, 120), 'pause_retention_min': (0, 1440),
    }
    for key, default in _TUNING_DEFAULTS.items():
        try:
            value = int(values.get(key, default))
        except (TypeError, ValueError):
            value = default
        low, high = limits[key]
        result[key] = min(high, max(low, value))
    if not (
        0 <= result['critical_pct'] < result['low_water_pct']
        < result['high_water_pct'] <= 100
        and 0 < result['startup_pct'] <= result['high_water_pct']
    ):
        for key in ('startup_pct', 'high_water_pct', 'low_water_pct', 'critical_pct'):
            result[key] = _TUNING_DEFAULTS[key]
    return result


def tuning_from_addon(addon=None):
    addon = addon or ADDON
    mapping = {
        'startup_pct': 'buffered_startup_pct',
        'high_water_pct': 'buffered_high_water_pct',
        'low_water_pct': 'buffered_low_water_pct',
        'critical_pct': 'buffered_critical_pct',
        'media_timeout_s': 'buffered_media_timeout_s',
        'startup_timeout_s': 'buffered_startup_timeout_s',
        'seek_reserve_s': 'buffered_seek_reserve_s',
        'min_seek_reserve_mb': 'buffered_min_seek_reserve_mb',
        'prefetch_lead_s': 'buffered_prefetch_lead_s',
        'recovery_timeout_s': 'buffered_recovery_timeout_s',
        'retry_delay_ms': 'buffered_retry_delay_ms',
        'retry_attempts': 'buffered_retry_attempts',
        'recovery_reserve_s': 'buffered_recovery_reserve_s',
        'pause_retention_min': 'buffered_pause_retention_min',
    }
    values = {}
    for key, setting_id in mapping.items():
        try:
            raw = addon.getSetting(setting_id)
        except Exception:
            raw = ''
        values[key] = raw if raw != '' else _TUNING_DEFAULTS[key]
    return validated_tuning(values)


def _retryable_error(exc):
    code = getattr(exc, 'code', None)
    if code is not None:
        try:
            code = int(code)
        except (TypeError, ValueError):
            code = None
        if code is not None:
            return code in {408, 429} or 500 <= code <= 599
    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return True
    text = str(exc).lower()
    return any(marker in text for marker in (
        'incomplete', 'empty response', 'temporarily occupied',
        'connection reset', 'timed out', 'timeout',
    ))


def note_handoff(local_url, stage, **fields):
    match = re.search(r'/hls/([a-f0-9]{24})/', local_url or '')
    if not match:
        return False
    control = os.path.join(_root_path(), 'control')
    _ensure(control)
    path = os.path.join(control, 'handoff-' + match.group(1) + '.json')
    payload = _json_read(path) or {'events': []}
    events = payload.get('events') if isinstance(payload.get('events'), list) else []
    event = {
        'stage': str(stage),
        'monotonic_ms': round(time.monotonic() * 1000.0, 3),
    }
    event.update(fields)
    events.append(event)
    payload['events'] = events[-20:]
    _json_write(path, payload)
    return True


def request_playback(source_url, target_seconds=DEFAULT_TARGET_SECONDS,
                     startup_seconds=DEFAULT_STARTUP_SECONDS, timeout=CONTROL_TIMEOUT,
                     buffer_mb=DEFAULT_BUFFER_MB, quality='highest', tuning=None):
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
    tuning = validated_tuning(tuning or tuning_from_addon())
    _json_write(request_path, {
        'id': request_id, 'source_url': source_url,
        'target_seconds': target_seconds, 'startup_seconds': startup_seconds,
        'buffer_mb': buffer_size_mb(buffer_mb), 'quality': quality,
        'tuning': tuning,
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
                dialog.update(100, 'Buffer ready — starting Kodi playback…')
                note_handoff(response['local_url'], 'plugin_ready_observed')
                success = True
                return response['local_url']
            dialog.update(int(response.get('percent', 0)), response.get('message', 'Preparing stream…'))
            monitor.waitForAbort(0.1)
        raise RuntimeError('Stream preparation timed out before the configured playable reservoir was ready. Please retry playback.')
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
        # The socket timeout is deliberately an inactivity timeout. A transfer
        # that keeps yielding bytes may take longer than this in total.
        with urlopen(request, timeout=timeout) as response:
            latency_ms = (time.monotonic() - started) * 1000.0
            if byte_range and _safe_status(response) != 206:
                raise RuntimeError('Provider did not honor the media byte range')
            expected_length = _int(response.headers.get('Content-Length'), -1)
            with open(temp, 'wb') as handle:
                while True:
                    if stop and stop.is_set():
                        raise PlaybackCancelled()
                    try:
                        chunk = response.read1(256 * 1024)
                    except TimeoutError as exc:
                        raise TimeoutError(
                            'Segment transfer made no progress for {:.0f} seconds'.format(timeout)
                        ) from exc
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
        self.last_requested = -1
        self.epoch = session.epoch
        self.epoch_start_index = 0
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
            if self.last_requested >= len(self.segments):
                self.last_requested = self.last_served
            self.epoch_start_index = min(self.epoch_start_index, max(0, len(self.segments) - 1))
            self._condition.notify_all()

    def _cached(self, index):
        if index < 0 or index >= len(self.segments):
            return False
        path = self.segments[index].resource.path
        return bool(path and os.path.isfile(path))

    def cursor_index(self):
        return max(0, self.epoch_start_index, self.last_served + 1)

    def _ahead(self, start_index=None):
        if start_index is None:
            start_index = self.cursor_index()
        seconds = 0.0
        count = 0
        for index in range(max(0, start_index), len(self.segments)):
            if not self._cached(index):
                break
            seconds += self.segments[index].duration
            count += 1
        return round(seconds, 3), count

    def ahead_bytes(self, start=None):
        start = max(0, self.cursor_index() if start is None else start)
        total = 0
        for seg in self.segments[start:]:
            if not self._cached(seg.index):
                break
            try:
                total += os.path.getsize(seg.resource.path)
            except OSError:
                break
        return total

    def bytes_for_seconds(self, start, seconds):
        remaining = max(0.0, float(seconds))
        total = 0
        elapsed = 0.0
        for seg in self.segments[max(0, int(start)):]:
            if not self._cached(seg.index):
                break
            if elapsed >= remaining and remaining > 0:
                break
            try:
                total += os.path.getsize(seg.resource.path)
            except OSError:
                break
            elapsed += seg.duration
        return total

    def all_cached_from(self, start=None):
        start = self.cursor_index() if start is None else max(0, int(start))
        return start >= len(self.segments) or all(
            self._cached(index) for index in range(start, len(self.segments))
        )

    def timeline_offset(self, index):
        index = max(0, min(int(index), len(self.segments)))
        return sum(segment.duration for segment in self.segments[:index])

    def index_for_offset(self, offset):
        if not self.segments:
            return 0
        target = max(0.0, float(offset))
        elapsed = 0.0
        for segment in self.segments:
            end = elapsed + segment.duration
            if target < end:
                return segment.index
            elapsed = end
        return self.segments[-1].index

    def recenter(self, index, epoch=None):
        index = max(0, min(int(index), max(0, len(self.segments) - 1)))
        with self._condition:
            previous = self.last_served
            self.last_served = index - 1
            self.last_requested = index - 1
            self.epoch_start_index = index
            if epoch is not None:
                self.epoch = int(epoch)
            self.failed = ''
            self._condition.notify_all()
        return previous

    def _next_missing(self):
        if self.session._stop.is_set():
            return None
        if self.epoch != self.session.epoch:
            return None
        start = self.cursor_index()
        if start >= len(self.segments):
            return None
        if self.session._pause_track(self):
            return None
        for index in range(start, len(self.segments)):
            if not self._cached(index):
                return index
        return None

    def _prefetch_loop(self):
        while not self._stop.is_set() and not self.session._stop.is_set():
            with self._condition:
                index = self._next_missing()
                if index is None:
                    self._condition.wait(timeout=0.25)
                    continue
                segment = self.segments[index]
                epoch = self.session.epoch
            try:
                self.session._ensure_binary(
                    segment.resource, segment=segment, track=self, epoch=epoch
                )
                if epoch != self.session.epoch:
                    continue
                with self._condition:
                    self.downloaded_total += 1
                    self.failed = ''
                    self._condition.notify_all()
                self.session._notify_tracks()
            except PlaybackCancelled:
                # Epoch replacement/session shutdown is normal cancellation,
                # not a provider failure.
                continue
            except Exception as exc:
                if epoch != self.session.epoch:
                    continue
                with self._condition:
                    self.failed = '{}: {}'.format(type(exc).__name__, exc)
                    self._condition.notify_all()
                self.session._event(
                    'buffer_segment_error',
                    epoch_id=epoch,
                    track_id=self.id,
                    segment_sequence=segment.sequence,
                    error_type=type(exc).__name__,
                    http_status=getattr(exc, 'code', None),
                )
                if self._stop.wait(self.session.retry_delay):
                    break

    def _reserve_state(self, index, reserve_seconds):
        ahead, count = self._ahead(index)
        remaining = sum(seg.duration for seg in self.segments[index:])
        threshold = min(reserve_seconds, remaining)
        ready = (
            ahead >= threshold
            or self.all_cached_from(index)
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
            if self.last_requested < index - 1:
                self.last_requested = index - 1
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
        return self._serve_segment(index)

    def _serve_segment(self, index):
        if index < 0 or index >= len(self.segments):
            raise IndexError('HLS segment index outside playlist')

        with self._serve_lock:
            expected = self.last_requested + 1
            is_seek = index != expected
            if is_seek:
                reason = 'cold-resume' if self.last_served < 0 and index > 0 else 'seek'
                epoch = self.session._coordinate_seek(self, index, reason=reason)
            else:
                epoch = self.session.epoch
                self.last_requested = index

        ahead, count = self._ahead(index)
        needs_reserve = is_seek or not self._cached(index)
        if needs_reserve:
            self.recovering = True
            self.session._event(
                'buffer_depletion',
                epoch_id=epoch,
                track_id=self.id,
                buffered_seconds=ahead,
                cached_segments_ahead=count,
                requested_index=index,
                random_access=is_seek,
            )
            try:
                self.session.recover_segment(self, index, epoch, random_access=is_seek)
                self.failed = ''
            finally:
                self.recovering = False

        if epoch != self.session.epoch:
            raise RecoveryTimeout('Playback request belongs to a stale buffer epoch')
        if not self._cached(index):
            self.session._ensure_binary(
                self.segments[index].resource,
                segment=self.segments[index],
                track=self,
                epoch=epoch,
            )
        segment = self.segments[index]
        with self._serve_lock:
            if epoch != self.session.epoch:
                raise RecoveryTimeout('Playback request belongs to a stale buffer epoch')
            self.last_served = max(self.last_served, index)
            self.last_requested = max(self.last_requested, index)
        with self._condition:
            self._condition.notify_all()
        self._cleanup_old(index)
        self.session._notify_tracks()
        reserve_bytes, reserve_seconds, reserve_count = self.session._playable_reserve()
        self.session._event(
            'buffer_status',
            epoch_id=epoch,
            track_id=self.id,
            buffered_seconds=reserve_seconds,
            cached_ahead_bytes=reserve_bytes,
            cached_segments_ahead=reserve_count,
            queued_segment_count=self._queued_count(index + 1),
            downloaded_segment_count=self.downloaded_total,
            buffer_state=self.session.buffer_state(reserve_bytes),
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
        tuning=None,
    ):
        self.source_url = source_url
        supplied_tuning = dict(tuning or {})
        self.tuning = validated_tuning(supplied_tuning)
        self.max_bytes = buffer_size_mb(buffer_mb) * 1024 * 1024
        self.high_water_bytes = max(1, int(self.max_bytes * self.tuning['high_water_pct'] / 100.0))
        self.startup_target_bytes = max(1, int(self.max_bytes * self.tuning['startup_pct'] / 100.0))
        self.low_water_bytes = max(1, int(self.max_bytes * self.tuning['low_water_pct'] / 100.0))
        self.critical_water_bytes = max(1, int(self.max_bytes * self.tuning['critical_pct'] / 100.0))
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
        self._reserved_bytes = 0
        self._playlist_lock = threading.RLock()
        self._playlist_cache = {}
        self._pins = set()
        self._serving = set()
        self._registry = {}
        self.target_seconds = max(5.0, float(target_seconds))
        self.startup_seconds = min(max(5.0, float(startup_seconds)), self.target_seconds)
        self.recovery_seconds = min(
            max(1.0, float(self.tuning['recovery_reserve_s'])), self.target_seconds
        )
        self.media_timeout = float(
            self.tuning['media_timeout_s']
            if 'media_timeout_s' in supplied_tuning else REQUEST_TIMEOUT
        )
        self.startup_timeout = float(
            self.tuning['startup_timeout_s']
            if 'startup_timeout_s' in supplied_tuning else STARTUP_TIMEOUT
        )
        self.seek_reserve_seconds = float(
            self.tuning['seek_reserve_s']
            if 'seek_reserve_s' in supplied_tuning else SEEK_RESERVE_SECONDS
        )
        self.min_seek_reserve_bytes = int(
            self.tuning['min_seek_reserve_mb']
            if 'min_seek_reserve_mb' in supplied_tuning
            else max(1, MIN_SEEK_RESERVE_BYTES // (1024 * 1024))
        ) * 1024 * 1024
        self.prefetch_lead_seconds = float(
            self.tuning['prefetch_lead_s']
            if 'prefetch_lead_s' in supplied_tuning else PREFETCH_LEAD_SECONDS
        )
        self.recovery_timeout = float(self.tuning['recovery_timeout_s'])
        self.retry_delay = float(self.tuning['retry_delay_ms']) / 1000.0
        self.retry_attempts = int(self.tuning['retry_attempts'])
        self.recovery_reserve_seconds = float(self.tuning['recovery_reserve_s'])
        self.pause_retention_seconds = float(self.tuning['pause_retention_min']) * 60.0
        self.token = secrets.token_hex(12)
        self.root = root or os.path.join(_root_path(), 'session-{}'.format(self.token))
        self.data_root = os.path.join(self.root, 'data')
        _ensure(self.data_root)
        self.resources = {}
        self.tracks = {}
        self.events = queue.Queue()
        self._resource_counter = 0
        self._lock = threading.RLock()
        self._epoch_lock = threading.RLock()
        self._metrics_lock = threading.Lock()
        self._stop = threading.Event()
        self._server = None
        self._server_thread = None
        self.last_access = time.monotonic()
        self._selected_representation = ''
        self._selected_variant_attrs = {}
        self._startup_track_ids = []
        self._startup_complete = False
        self.epoch = 1
        self.epoch_reason = 'startup'
        self.epoch_target_seconds = 0.0
        self.epoch_target_bytes = self.startup_target_bytes
        self._epoch_preparing = True
        self._stale_ignored = 0
        self._refill_active = True
        self._throughput_samples = []
        self._last_status_bytes = 0
        self._last_status_at = time.monotonic()
        self._recovery_started_at = 0.0
        self._recovery_attempt = 0
        self._recovery_last_error = ''
        self._telemetry = []
        self._last_telemetry_at = 0.0
        self._transfer_history = []
        self._handoff_marks = set()
        self._player_state = 'preparing'
        self._paused_since = 0.0
        self.master = self._register(source_url, 'playlist', metadata={'root': True})

    def _required_startup_tracks(self):
        if self._startup_track_ids:
            return [
                self.tracks[track_id]
                for track_id in self._startup_track_ids
                if track_id in self.tracks
            ]
        return list(self.tracks.values())

    def _notify_tracks(self):
        for track in list(self.tracks.values()):
            with track._condition:
                track._condition.notify_all()

    def _selected_bitrate_bps(self):
        return max(
            0,
            _int(
                self._selected_variant_attrs.get('AVERAGE-BANDWIDTH')
                or self._selected_variant_attrs.get('BANDWIDTH')
            ),
        )

    def seek_reserve_bytes(self):
        bitrate = self._selected_bitrate_bps() or 4000000
        estimated = int((bitrate / 8.0) * self.seek_reserve_seconds * 1.15)
        return min(
            self.startup_target_bytes,
            max(self.min_seek_reserve_bytes, min(self.low_water_bytes, estimated)),
        )

    def recovery_reserve_bytes(self):
        bitrate = self._selected_bitrate_bps() or 4000000
        estimated = int((bitrate / 8.0) * self.recovery_reserve_seconds * 1.15)
        return min(self.low_water_bytes, max(1024 * 1024, estimated))

    def _playable_reserve(self):
        required = [track for track in self._required_startup_tracks() if track.segments]
        if not required:
            return 0, 0.0, 0
        starts = {track.id: track.cursor_index() for track in required}
        ahead = {track.id: track._ahead(starts[track.id]) for track in required}
        seconds = min((value[0] for value in ahead.values()), default=0.0)
        count = sum(value[1] for value in ahead.values())
        total = 0
        for track in required:
            total += track.bytes_for_seconds(starts[track.id], seconds)
        return int(total), round(seconds, 3), count

    def _all_required_cached(self):
        required = [track for track in self._required_startup_tracks() if track.segments]
        return bool(required) and all(track.all_cached_from() for track in required)

    def _record_transfer(self, fetched):
        with self._metrics_lock:
            self._throughput_samples.append(
                (max(0, fetched.byte_count), max(1.0, fetched.download_ms))
            )
            self._throughput_samples = self._throughput_samples[-12:]

    def measured_throughput_mbps(self):
        with self._metrics_lock:
            samples = list(self._throughput_samples)
        if not samples:
            return 0.0
        bytes_total = sum(value[0] for value in samples)
        ms_total = sum(value[1] for value in samples)
        return round((bytes_total * 8.0) / max(0.001, ms_total / 1000.0) / 1000000.0, 3)

    def buffer_state(self, reserve_bytes=None):
        reserve_bytes = self._playable_reserve()[0] if reserve_bytes is None else int(reserve_bytes)
        if reserve_bytes <= self.critical_water_bytes and self.started_playback:
            return 'critical'
        if self._epoch_preparing:
            return 'filling'
        if reserve_bytes >= self.high_water_bytes:
            return 'full'
        if self._refill_active:
            return 'filling'
        return 'draining'

    def _update_refill_state(self):
        reserve_bytes, _, _ = self._playable_reserve()
        if self._epoch_preparing or not self._startup_complete:
            self._refill_active = True
            return True
        if self._all_required_cached():
            self._refill_active = False
            return False
        if self._refill_active and reserve_bytes >= self.high_water_bytes:
            self._refill_active = False
        elif not self._refill_active and reserve_bytes <= self.low_water_bytes:
            self._refill_active = True
        return self._refill_active

    def _pause_track(self, track):
        required = [value for value in self._required_startup_tracks() if value.segments]
        if track not in required:
            return track._ahead()[0] >= track.target_seconds
        if not self._update_refill_state():
            return True
        ahead = {value.id: value._ahead(value.cursor_index())[0] for value in required}
        minimum = min(ahead.values(), default=0.0)
        return ahead.get(track.id, 0.0) > minimum + self.prefetch_lead_seconds

    def recover_segment(self, track, index, epoch, random_access=False):
        target_bytes = (
            self.epoch_target_bytes if random_access else self.recovery_reserve_bytes()
        )
        deadline = time.monotonic() + self.recovery_timeout
        self._recovery_started_at = time.monotonic()
        self._recovery_attempt = 0
        self._recovery_last_error = ''
        start_bytes, _, _ = self._playable_reserve()
        self._event(
            'buffer_recovery_started',
            epoch_id=epoch,
            track_id=track.id,
            requested_index=index,
            target_bytes=target_bytes,
            random_access=random_access,
        )
        segment = track.segments[index]
        while not self._stop.is_set():
            if epoch != self.epoch:
                raise RecoveryTimeout('Playback target was superseded by a newer seek')
            if track._cached(index):
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            if self.retry_attempts and self._recovery_attempt >= self.retry_attempts:
                break
            self._recovery_attempt += 1
            try:
                self._ensure_binary(
                    segment.resource, segment=segment, track=track, epoch=epoch
                )
                self._recovery_last_error = ''
            except PlaybackCancelled:
                if epoch != self.epoch:
                    raise RecoveryTimeout('Playback target was superseded by a newer seek')
                raise
            except Exception as exc:
                self._recovery_last_error = '{}: {}'.format(type(exc).__name__, exc)
                retryable = _retryable_error(exc)
                self._event(
                    'buffer_recovery_retry',
                    epoch_id=epoch,
                    track_id=track.id,
                    requested_index=index,
                    attempt=self._recovery_attempt,
                    retryable=retryable,
                    error_type=type(exc).__name__,
                    http_status=getattr(exc, 'code', None),
                    elapsed_s=round(time.monotonic() - self._recovery_started_at, 3),
                )
                if not retryable:
                    self._failure_snapshot('non_retryable_recovery', self._recovery_last_error)
                    raise RecoveryExhausted(
                        'Non-retryable provider/local failure: {}'.format(self._recovery_last_error)
                    )
                wait_for = min(self.retry_delay, max(0.0, deadline - time.monotonic()))
                if wait_for and self._stop.wait(wait_for):
                    raise PlaybackCancelled()
                continue
        if epoch != self.epoch:
            raise RecoveryTimeout('Playback target was superseded by a newer seek')
        if not track._cached(index):
            self._failure_snapshot('recovery_exhausted', self._recovery_last_error)
            raise RecoveryExhausted(
                'Recovery exhausted after {} attempt(s): {}'.format(
                    self._recovery_attempt, self._recovery_last_error or 'provider did not deliver target segment'
                )
            )
        remaining = max(0.0, deadline - time.monotonic())
        recovered = remaining > 0 and self._wait_reservoir(epoch, target_bytes, remaining)
        if epoch != self.epoch:
            raise RecoveryTimeout('Playback target was superseded by a newer seek')
        new_bytes, new_seconds, _ = self._playable_reserve()
        if not recovered:
            self._event(
                'buffer_recovery_timeout',
                epoch_id=epoch,
                track_id=track.id,
                buffered_seconds=new_seconds,
                cached_ahead_bytes=new_bytes,
                requested_index=index,
                random_access=random_access,
                attempt=self._recovery_attempt,
            )
            self._failure_snapshot('recovery_timeout', self._recovery_last_error)
            raise RecoveryExhausted(
                'Unable to rebuild recovery reserve: {} buffered toward {} target'.format(
                    _human_bytes(new_bytes), _human_bytes(target_bytes)
                )
            )
        self._event(
            'buffer_recovery',
            epoch_id=epoch,
            track_id=track.id,
            buffered_seconds=new_seconds,
            cached_ahead_bytes=new_bytes,
            requested_index=index,
            random_access=random_access,
            attempt=self._recovery_attempt,
            recovered_from_bytes=start_bytes,
        )
        self._recovery_started_at = 0.0
        self._recovery_attempt = 0
        self._recovery_last_error = ''
        return True

    def _coordinate_seek(self, source_track, source_index, reason='seek'):
        """Create a fresh authoritative buffer epoch at the requested timeline."""
        with self._epoch_lock:
            target_seconds = source_track.timeline_offset(source_index)
            stale_inflight = sum(1 for resource in self.resources.values() if resource.fetching)
            self.epoch += 1
            epoch = self.epoch
            self.epoch_reason = reason
            self.epoch_target_seconds = round(target_seconds, 3)
            self.epoch_target_bytes = self.seek_reserve_bytes()
            self._epoch_preparing = True
            self._refill_active = True
            self._stale_ignored += stale_inflight
            for track in list(self.tracks.values()):
                if not track.segments:
                    continue
                target_index = (
                    source_index
                    if track is source_track
                    else track.index_for_offset(target_seconds)
                )
                previous = track.recenter(target_index, epoch=epoch)
                track.recovering = True
                self._event(
                    'buffer_seek_recenter',
                    epoch_id=epoch,
                    track_id=track.id,
                    source_track_id=source_track.id,
                    from_index=previous,
                    to_index=target_index,
                    requested_index=source_index,
                    timeline_seconds=round(target_seconds, 3),
                    reason=reason,
                )
            source_track.last_requested = source_index
            self._event(
                'buffer_epoch_started',
                epoch_id=epoch,
                reason=reason,
                requested_target_seconds=round(target_seconds, 3),
                target_segment=source_index,
                stale_jobs_cancelled_or_ignored=stale_inflight,
                target_bytes=self.epoch_target_bytes,
            )
            self._notify_tracks()
            return epoch

    def _wait_reservoir(self, epoch, target_bytes, timeout):
        deadline = time.monotonic() + max(1.0, timeout)
        target_bytes = max(1, int(target_bytes))
        while not self._stop.is_set():
            if epoch != self.epoch:
                return False
            reserve_bytes, reserve_seconds, _ = self._playable_reserve()
            first_segments_ready = all(
                track.cursor_index() >= len(track.segments)
                or track._cached(track.cursor_index())
                for track in self._required_startup_tracks()
                if track.segments
            )
            if first_segments_ready and (
                reserve_bytes >= target_bytes or self._all_required_cached()
            ):
                if epoch == self.epoch:
                    self._epoch_preparing = False
                    for track in self._required_startup_tracks():
                        track.recovering = False
                    self._event(
                        'buffer_epoch_ready',
                        epoch_id=epoch,
                        buffered_seconds=reserve_seconds,
                        cached_ahead_bytes=reserve_bytes,
                        target_bytes=target_bytes,
                    )
                    self._notify_tracks()
                return True
            if time.monotonic() >= deadline:
                return False
            self._stop.wait(0.1)
        return False

    def _track_metrics(self):
        values = []
        missing = []
        for track in self._required_startup_tracks():
            if not track.segments:
                continue
            index = track.cursor_index()
            ahead_seconds, ahead_count = track._ahead(index)
            ahead_bytes = track.bytes_for_seconds(index, ahead_seconds)
            next_state = 'end'
            next_sequence = None
            later_cached = False
            if index < len(track.segments):
                segment = track.segments[index]
                resource = segment.resource
                next_sequence = segment.sequence
                if track._cached(index):
                    next_state = 'cached'
                elif resource.fetching:
                    next_state = 'fetching'
                elif resource.error or track.failed:
                    next_state = 'failed'
                else:
                    next_state = 'absent'
                later_cached = any(
                    track._cached(i)
                    for i in range(index + 1, min(len(track.segments), index + 9))
                )
                if next_state != 'cached':
                    missing.append(track.id)
            values.append({
                'track_id': track.id,
                'cursor_index': index,
                'contiguous_bytes': ahead_bytes,
                'contiguous_seconds': ahead_seconds,
                'contiguous_segments': ahead_count,
                'next_sequence': next_sequence,
                'next_state': next_state,
                'later_cached': later_cached,
                'failed': bool(track.failed),
            })
        return values, missing

    def _record_telemetry(self, reserve_bytes, reserve_seconds, state,
                          selected_mbps, throughput_mbps, track_metrics, force=False):
        now = time.monotonic()
        cadence = 0.25 if state == 'critical' or self._recovery_started_at else 1.0
        if not force and now - self._last_telemetry_at < cadence:
            return
        self._last_telemetry_at = now
        self._telemetry.append({
            'monotonic': round(now, 3),
            'observed_at': round(time.time(), 3),
            'epoch_id': self.epoch,
            'epoch_reason': self.epoch_reason,
            'capacity_bytes': self.max_bytes,
            'startup_bytes': self.startup_target_bytes,
            'high_water_bytes': self.high_water_bytes,
            'low_water_bytes': self.low_water_bytes,
            'critical_water_bytes': self.critical_water_bytes,
            'playable_bytes': int(reserve_bytes),
            'playable_seconds': round(float(reserve_seconds), 3),
            'total_cached_bytes': self.disk_bytes(),
            'selected_bitrate_mbps': selected_mbps,
            'throughput_mbps': throughput_mbps,
            'buffer_state': state,
            'tracks': track_metrics,
            'recovery_attempt': self._recovery_attempt,
            'recovery_elapsed_s': (
                round(now - self._recovery_started_at, 3)
                if self._recovery_started_at else 0.0
            ),
            'player_state': self._player_state,
        })
        cutoff = now - 65.0
        self._telemetry = [
            item for item in self._telemetry[-300:]
            if item.get('monotonic', now) >= cutoff
        ]

    def _classify_failure(self, trigger):
        if not self._telemetry:
            return 'unknown'
        sample = self._telemetry[-1]
        tracks = sample.get('tracks') or []
        if trigger in {'player-idle', 'pause-retention-expired', 'session_lifecycle'}:
            return 'session_lifecycle_termination'
        positives = [t for t in tracks if t.get('contiguous_bytes', 0) > 0]
        empty = [t for t in tracks if t.get('contiguous_bytes', 0) <= 0]
        if len(tracks) > 1 and positives and empty:
            return 'required_track_starvation'
        if any(t.get('next_state') != 'cached' and t.get('later_cached') for t in tracks):
            return 'next_segment_hole'
        if trigger in {'recovery_timeout', 'recovery_exhausted'} and len(self._telemetry) > 1:
            start = self._telemetry[0].get('playable_bytes', 0)
            end = sample.get('playable_bytes', 0)
            if end > start:
                return 'recovery_timeout_with_progress'
        selected = float(sample.get('selected_bitrate_mbps') or 0)
        throughput = float(sample.get('throughput_mbps') or 0)
        if selected and throughput and throughput < selected * 0.95:
            return 'sustained_throughput_deficit'
        if sample.get('playable_bytes', 0) <= 64 * 1024:
            return 'reservoir_exhausted'
        return 'unknown'

    def _failure_snapshot(self, trigger, reason=''):
        try:
            self.status()
        except Exception:
            pass
        classification = self._classify_failure(trigger)
        self._event(
            'buffer_failure_snapshot',
            trigger=trigger,
            reason=reason,
            classification=classification,
            timeline=list(self._telemetry),
            recent_transfers=list(self._transfer_history[-24:]),
        )
        return classification

    def status(self):
        tracks = list(self.tracks.values())
        reserve_bytes, seconds, count = self._playable_reserve()
        target_bytes = self.epoch_target_bytes if self._epoch_preparing else self.high_water_bytes
        ratio = min(1.0, reserve_bytes / float(max(1, target_bytes)))
        percent = 100 if self.ready and not self._epoch_preparing else min(99, int(ratio * 100))
        stalled = any(track.failed for track in self._required_startup_tracks())
        target_text = _human_bytes(target_bytes)
        current_text = _human_bytes(reserve_bytes)
        capacity_text = _human_bytes(self.max_bytes)
        if self.ready and not self._epoch_preparing:
            message = 'Buffer ready — starting Kodi playback…'
        elif stalled:
            message = 'Buffering stalled; retrying — {} / {}'.format(current_text, target_text)
        elif self.epoch_reason == 'startup':
            message = 'Filling buffer — {} / {} startup target — capacity {}'.format(
                current_text, target_text, capacity_text
            )
        else:
            message = 'Filling buffer — {} / {}'.format(current_text, target_text)
        now = time.monotonic()
        delta = reserve_bytes - self._last_status_bytes
        trend = 'filling' if delta > 64 * 1024 else 'draining' if delta < -64 * 1024 else 'steady'
        self._last_status_bytes = reserve_bytes
        self._last_status_at = now
        selected_bps = self._selected_bitrate_bps()
        selected_mbps = round(selected_bps / 1000000.0, 3) if selected_bps else 0.0
        throughput_mbps = self.measured_throughput_mbps()
        state = self.buffer_state(reserve_bytes)
        throughput_limited = bool(
            self.started_playback and state == 'critical'
            and selected_mbps > 0 and throughput_mbps > 0
            and throughput_mbps < selected_mbps * 0.95
        )
        limitation_message = ''
        if throughput_limited:
            limitation_message = (
                'Provider {:.2f} Mbit/s is below selected {:.2f} Mbit/s while reserve is critical'
                .format(throughput_mbps, selected_mbps)
            )
            message = 'Buffer critical — {}'.format(limitation_message)
        track_metrics, missing_tracks = self._track_metrics()
        total_cached = self.disk_bytes()
        self._record_telemetry(
            reserve_bytes, seconds, state, selected_mbps, throughput_mbps, track_metrics
        )
        return {
            'ready': self.ready, 'error': self.error, 'local_url': self.local_url,
            'choices': self.choices if not self.choice_event.is_set() else [],
            'message': message, 'percent': percent,
            'cached_ahead_bytes': reserve_bytes, 'buffer_target_bytes': target_bytes,
            'high_water_bytes': self.high_water_bytes,
            'low_water_bytes': self.low_water_bytes,
            'critical_water_bytes': self.critical_water_bytes,
            'buffered_seconds': seconds, 'cached_segments_ahead': count,
            'buffer_capacity_mb': self.max_bytes // (1024 * 1024),
            'total_cached_bytes': total_cached,
            'required_track_reserve': track_metrics,
            'missing_next_tracks': missing_tracks,
            'recovering': self._epoch_preparing or any(t.recovering for t in tracks)
                          or bool(self._recovery_started_at),
            'recovery_attempt': self._recovery_attempt,
            'recovery_elapsed_s': (
                round(now - self._recovery_started_at, 3)
                if self._recovery_started_at else 0.0
            ),
            'recovery_last_error': self._recovery_last_error,
            'startup_tracks': len(self._required_startup_tracks()),
            'buffer_state': state, 'buffer_trend': trend,
            'selected_bitrate_mbps': selected_mbps,
            'throughput_mbps': throughput_mbps,
            'throughput_limited': throughput_limited,
            'limitation_message': limitation_message,
            'epoch_id': self.epoch, 'epoch_reason': self.epoch_reason,
            'epoch_target_seconds': self.epoch_target_seconds,
            'stale_jobs_cancelled_or_ignored': self._stale_ignored,
            'player_state': self._player_state,
        }

    def fail(self, message, error_type='PlaybackError'):
        if not self.error and not self._stop.is_set():
            if self.started_playback:
                self._failure_snapshot('session_failure', message)
            self.error = message
            self._event('buffer_failure', error_type=error_type, epoch_id=self.epoch)

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

    def _preload_startup_dependencies(self):
        dependencies = [
            resource for resource in list(self.resources.values())
            if resource.kind in {'key', 'map'}
        ]
        for resource in dependencies:
            self._ensure_binary(resource, epoch=self.epoch)
        if dependencies:
            self._event(
                'buffer_startup_dependencies_preloaded',
                count=len(dependencies),
                kinds=sorted({resource.kind for resource in dependencies}),
            )

    def prepare(self):
        try:
            self.serve(self.master.id)
            variants = [r for r in list(self.resources.values()) if r.metadata.get('representation')]
            if variants:
                self.serve(variants[0].id)
            self._prepare_associated_media()
            self._preload_startup_dependencies()
            if self._stop.is_set():
                return

            tracks = list(self.tracks.values())
            if not tracks or not any(t.segments for t in tracks):
                raise RuntimeError('Stream contains no playable media segments')
            self._startup_track_ids = [track.id for track in tracks if track.segments]
            for track in self._required_startup_tracks():
                track.epoch = self.epoch
                track.epoch_start_index = 0
                track.last_requested = max(track.last_requested, -1)

            # Startup is capacity-driven. A short VOD may become ready when all
            # remaining media is cached even if it cannot fill the configured
            # byte target.
            self.epoch_reason = 'startup'
            self.epoch_target_seconds = 0.0
            self.epoch_target_bytes = self.startup_target_bytes
            self._epoch_preparing = True
            self._refill_active = True
            self._notify_tracks()
            if not self._wait_reservoir(
                self.epoch, self.startup_target_bytes, self.startup_timeout
            ):
                reserve_bytes, reserve_seconds, _ = self._playable_reserve()
                failures = [
                    '{}: {}'.format(track.id, track.failed)
                    for track in self._required_startup_tracks() if track.failed
                ]
                detail = '; '.join(failures[:2])
                raise TimeoutError(
                    'Startup reservoir incomplete: {} buffered ({:.1f}s) toward {} target{}'.format(
                        _human_bytes(reserve_bytes),
                        reserve_seconds,
                        _human_bytes(self.startup_target_bytes),
                        ': ' + detail if detail else '',
                    )
                )

            if self._stop.is_set():
                return
            self._startup_complete = True
            self._epoch_preparing = False
            self._mark_handoff('reservoir_ready')
            self.ready = True
            self.last_access = time.monotonic()
            self._notify_tracks()
            self._event('buffer_startup_ready', **{k: v for k, v in self.status().items()
                        if k in {'buffered_seconds', 'cached_ahead_bytes',
                                 'buffer_target_bytes', 'high_water_bytes',
                                 'buffer_capacity_mb', 'startup_tracks',
                                 'throughput_mbps', 'selected_bitrate_mbps',
                                 'buffer_state', 'epoch_id'}})
        except PlaybackCancelled:
            return
        except Exception as exc:
            detail = str(exc).strip()
            message = 'Unable to prepare stream: {}'.format(type(exc).__name__)
            if detail:
                message += ': ' + detail
            self.fail(message + '. Please retry playback.', type(exc).__name__)

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

    def _mark_handoff(self, stage, **fields):
        if stage in self._handoff_marks:
            return False
        self._handoff_marks.add(stage)
        fields.update({
            'stage': stage,
            'monotonic_ms': round(time.monotonic() * 1000.0, 3),
        })
        self._event('buffer_handoff', **fields)
        return True

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
                        session._mark_handoff(
                            'first_master_playlist_request'
                            if resource is session.master
                            else 'first_media_playlist_request',
                            resource_kind=resource.kind,
                        )
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
                    if resource.kind in {'key', 'map'}:
                        session._mark_handoff('first_key_or_map_request', resource_kind=resource.kind)
                    elif resource.kind == 'segment':
                        session._mark_handoff('first_media_segment_request', resource_kind=resource.kind)
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
                            if resource.kind == 'segment':
                                session._mark_handoff('first_media_bytes_served', resource_kind=resource.kind)
                            remaining -= len(chunk)
                    finally:
                        handle.close()
                        session._pins.discard(path)
                except (BrokenPipeError, ConnectionResetError):
                    pass
                except RecoveryExhausted as exc:
                    session._event(
                        'buffer_recovery_exhausted',
                        error_type=type(exc).__name__,
                        reason=str(exc),
                    )
                    session.fail(
                        'Buffered recovery exhausted: {}'.format(exc),
                        type(exc).__name__,
                    )
                    try:
                        self.send_error(504, 'Buffered recovery exhausted')
                    except Exception:
                        pass
                except RecoveryTimeout as exc:
                    # Only superseded/stale epoch requests use a retryable 503;
                    # ordinary depletion is recovered internally by Appi.
                    session._event('buffer_request_superseded', error_type=type(exc).__name__)
                    try:
                        self.send_error(503, 'Playback target superseded')
                    except Exception:
                        pass
                except Exception as exc:
                    session.fail(
                        'Buffered stream failed ({}). Please retry playback.'.format(
                            type(exc).__name__
                        ),
                        type(exc).__name__,
                    )
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
            high_water_bytes=self.high_water_bytes,
            low_water_bytes=self.low_water_bytes,
            critical_water_bytes=self.critical_water_bytes,
            startup_target_bytes=self.startup_target_bytes,
            epoch_id=self.epoch,
        )
        return self.local_url

    def stop(self, reason='stopped'):
        if self._stop.is_set():
            return
        if self.started_playback and reason not in {
            'stopped', 'ended', 'replaced', 'cancelled', 'service-shutdown'
        }:
            self._failure_snapshot(reason, reason)
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

    def _ensure_binary(self, resource, segment=None, track=None, epoch=None):
        # Coordinate duplicate requests per resource, not across the whole
        # session. Epoch-bound callers abandon obsolete work deterministically.
        epoch = self.epoch if epoch is None else int(epoch)
        with resource.condition:
            while resource.fetching and not self._stop.is_set():
                if epoch != self.epoch:
                    raise PlaybackCancelled()
                resource.condition.wait(timeout=0.1)
                if resource.path and os.path.isfile(resource.path):
                    return resource.path
            if self._stop.is_set() or epoch != self.epoch:
                raise PlaybackCancelled()
            if resource.path and os.path.isfile(resource.path):
                return resource.path
            resource.fetching = True
            resource.error = ''

        try:
            return self._download_binary(resource, segment, track, epoch=epoch)
        except PlaybackCancelled:
            raise
        except Exception as exc:
            resource.error = '{}: {}'.format(type(exc).__name__, exc)
            raise
        finally:
            with resource.condition:
                resource.fetching = False
                resource.condition.notify_all()

    def _download_binary(self, resource, segment=None, track=None, epoch=None):
        if resource.path and os.path.isfile(resource.path):
            return resource.path
        epoch = self.epoch if epoch is None else int(epoch)
        if epoch != self.epoch:
            raise PlaybackCancelled()
        path = os.path.join(self.data_root, '{}.bin'.format(resource.id))
        # This is only a per-transfer admission ceiling, not a per-track
        # reservoir allocation. Video and audio share the session dynamically.
        segment_limit = min(
            max(8 * 1024 * 1024, self.max_bytes // 4),
            32 * 1024 * 1024,
        )
        # Reserve a small admission allowance rather than the whole per-file
        # safety ceiling. Reserving the worst possible segment size prevented
        # the playable reservoir from ever reaching high-water on 32/64 MB
        # configurations even when real segments were much smaller.
        reservation_bytes = min(
            4 * 1024 * 1024,
            max(2 * 1024 * 1024, self.max_bytes // 16),
        )

        with self._download_lock:
            self._enforce_disk_limit(limit=max(0, self.max_bytes - reservation_bytes))
            if self.disk_bytes() + self._reserved_bytes > self.max_bytes - reservation_bytes:
                raise RuntimeError('Buffer capacity is temporarily occupied')
            self._reserved_bytes += reservation_bytes
        try:
            fetched = _fetch_to_path(
                resource.upstream_url,
                path,
                timeout=self.media_timeout,
                byte_range=resource.byte_range,
                stop=_EpochStop(self, epoch),
                max_bytes=segment_limit,
            )
        except Exception:
            with self._download_lock:
                self._reserved_bytes = max(0, self._reserved_bytes - reservation_bytes)
            raise

        with self._download_lock:
            self._reserved_bytes = max(0, self._reserved_bytes - reservation_bytes)
            if epoch != self.epoch:
                try:
                    os.remove(path)
                except OSError:
                    pass
                self._stale_ignored += 1
                self._event(
                    'buffer_stale_download_ignored',
                    stale_epoch_id=epoch,
                    active_epoch_id=self.epoch,
                    resource_kind=resource.kind,
                )
                raise PlaybackCancelled()
            resource.path = path
            resource.content_type = fetched.content_type or resource.content_type
            self._enforce_disk_limit(protected=path)

        self._record_transfer(fetched)
        fields = {
            'epoch_id': epoch,
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
                reserve_bytes, reserve_seconds, reserve_count = self._playable_reserve()
                fields['buffered_seconds'] = reserve_seconds
                fields['cached_ahead_bytes'] = reserve_bytes
                fields['cached_segments_ahead'] = reserve_count
                fields['buffer_state'] = self.buffer_state(reserve_bytes)
        transfer = dict(fields)
        transfer['monotonic'] = round(time.monotonic(), 3)
        self._transfer_history.append(transfer)
        self._transfer_history = self._transfer_history[-24:]
        self._event(
            'buffer_segment_download' if segment is not None else 'buffer_resource_download',
            **fields
        )
        self._notify_tracks()
        return path

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

    def poll(self, player_active=False, player_state=None):
        with self._lock:
            self._poll(player_active, player_state)

    def _poll(self, player_active=False, player_state=None):
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
                tuning=request.get('tuning') or {},
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
                state = player_state or ('playing' if player_active else 'unknown')
                if state != session._player_state:
                    session._event(
                        'buffer_player_state',
                        previous=session._player_state,
                        current=state,
                        epoch_id=session.epoch,
                    )
                    session._player_state = state
                if state == 'paused':
                    if not session._paused_since:
                        session._paused_since = time.monotonic()
                        session._event('buffer_pause_started', epoch_id=session.epoch)
                    elif (
                        session.pause_retention_seconds > 0
                        and time.monotonic() - session._paused_since
                        >= session.pause_retention_seconds
                    ):
                        session._failure_snapshot('pause-retention-expired', 'configured pause retention elapsed')
                        self.stop_active('pause-retention-expired')
                        session = self.active
                        if not session:
                            return
                elif session._paused_since:
                    session._event(
                        'buffer_pause_ended',
                        epoch_id=session.epoch,
                        paused_s=round(time.monotonic() - session._paused_since, 3),
                    )
                    session._paused_since = 0.0

                handoff = os.path.join(self.control, 'handoff-' + session.token + '.json')
                handoff_data = _json_read(handoff) or {}
                for marker in handoff_data.get('events') or []:
                    if isinstance(marker, dict):
                        session._event('buffer_handoff', **marker)
                if handoff_data:
                    try:
                        os.remove(handoff)
                    except OSError:
                        pass

                response = os.path.join(self.control, 'response-' + request_id + '.json')
                _json_write(response, session.status())
                if session.error:
                    # Startup caller displays its own error. Playback errors need
                    # visible feedback even when Kodi never calls onPlayBackError.
                    if session.ready:
                        import xbmcgui
                        xbmcgui.Dialog().notification('Appi Buffered Look Ahead', session.error, time=6000)
                    self.stop_active('error', keep_response=True)
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
            session._player_state = 'playing'
            session._mark_handoff('on_av_started')
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
        try:
            os.remove(os.path.join(self.control, 'handoff-' + session.token + '.json'))
        except OSError:
            pass
        return events

    def shutdown(self, diagnostic_event=None):
        self.stop_active('service-shutdown')
        if diagnostic_event:
            self.flush_diagnostics(diagnostic_event)
