import hashlib
import json
import os
import time
import zipfile
from urllib.parse import urlparse

import xbmc
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon()
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
ROOT = os.path.join(PROFILE, 'diagnostics')
ACTIVE = os.path.join(ROOT, 'active.json')
MAX_EVENTS = 1800
MAX_SESSIONS = 5
STALL_SECONDS = 4.0
PRESTALL_SECONDS = 30.0
_last_position = None
_last_advance = None
_stall_started = None
_last_representation = None


def enabled():
    value = ADDON.getSetting('diagnostics_enabled')
    return value.lower() == 'true' if value else False


def _ensure():
    os.makedirs(ROOT, exist_ok=True)


def _read(path):
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            value = json.load(handle)
        return value if isinstance(value, dict) else None
    except (OSError, ValueError, TypeError):
        return None


def _write(path, payload):
    _ensure()
    temp = path + '.tmp'
    with open(temp, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, ensure_ascii=False, separators=(',', ':'))
    os.replace(temp, path)


def _platform():
    checks = [
        ('android', 'System.Platform.Android'),
        ('windows', 'System.Platform.Windows'),
        ('linux', 'System.Platform.Linux'),
        ('osx', 'System.Platform.OSX'),
        ('ios', 'System.Platform.IOS'),
    ]
    for name, condition in checks:
        try:
            if xbmc.getCondVisibility(condition):
                return name
        except Exception:
            pass
    return 'unknown'


def _stream_identity(url):
    parsed = urlparse((url or '').split('|', 1)[0])
    full = (url or '').encode('utf-8', errors='replace')
    path = (parsed.path or '').encode('utf-8', errors='replace')
    extension = os.path.splitext(parsed.path or '')[1].lower()
    return {
        'scheme': parsed.scheme or '',
        'host': parsed.hostname or '',
        'extension': extension,
        'path_sha256': hashlib.sha256(path).hexdigest()[:16],
        'url_sha256': hashlib.sha256(full).hexdigest()[:16],
    }


def _info_label(name):
    try:
        return xbmc.getInfoLabel(name) or ''
    except Exception:
        return ''


def _number(value):
    if value in (None, ''):
        return None
    text = str(value).strip().replace(',', '')
    token = ''
    seen_dot = False
    for char in text:
        if char.isdigit() or (char == '.' and not seen_dot):
            token += char
            seen_dot = seen_dot or char == '.'
        elif token:
            break
    try:
        return float(token) if token else None
    except ValueError:
        return None


def _cache_snapshot():
    labels = {
        'level_percent': 'Player.CacheLevel',
        'bytes': 'Player.CacheBytes',
        'time_seconds': 'Player.CacheTime',
        'time_remaining_seconds': 'Player.CacheTimeRemaining',
        'progress_percent': 'Player.ProgressCache',
    }
    result = {}
    sources = {}
    for key, label in labels.items():
        raw = _info_label(label)
        if raw:
            result[key] = {'raw': raw, 'numeric': _number(raw)}
            sources[key] = 'Kodi InfoLabel {}'.format(label)
    return result, sources


def _representation_snapshot():
    resolution = _info_label('VideoPlayer.VideoResolution')
    bitrate = _info_label('VideoPlayer.VideoBitrate')
    return {
        'resolution': resolution,
        'bitrate': bitrate,
        'bitrate_numeric': _number(bitrate),
    }


def _append(payload, name, fields=None):
    payload.setdefault('events', []).append({
        'at': time.time(),
        'event': str(name),
        'fields': dict(fields or {}),
    })
    payload['events'] = payload['events'][-MAX_EVENTS:]


def prepare_playback(catalog, ref, media_url, stream_kind, engine, options=None):
    if not enabled():
        return None
    _ensure()
    now = time.time()
    session_id = hashlib.sha1('{}|{}|{}|{}'.format(now, catalog, ref, media_url).encode('utf-8')).hexdigest()[:16]
    options = dict(options or {})
    buffered_proxy = bool(options.get('buffered_proxy'))
    payload = {
        'schema': 2,
        'session_id': session_id,
        'started_at': now,
        'finished_at': None,
        'result': 'prepared',
        'app_version': ADDON.getAddonInfo('version') or '',
        'kodi_version': _info_label('System.BuildVersion'),
        'platform': _platform(),
        'media': {
            'catalog': catalog,
            'ref_sha256': hashlib.sha256((ref or '').encode('utf-8')).hexdigest()[:16],
            'stream_kind': stream_kind or 'unknown',
            'engine': engine or 'unknown',
            'stream': _stream_identity(media_url),
        },
        'options': options,
        'availability': {
            'player_position_seconds': True,
            'player_total_seconds': True,
            'video_resolution_info_label': True,
            'video_bitrate_info_label': True,
            'audio_language_info_label': True,
            'subtitle_language_info_label': True,
            'cache_read_ahead_info_labels': 'runtime-dependent',
            'per_segment_http_timing': buffered_proxy,
            'playlist_refresh_history': buffered_proxy,
            'proxy_buffer_depth': buffered_proxy,
            'inputstream_buffer_level': False,
            'representation_bitrate_history': 'derived-from-info-labels',
            'raw_authenticated_url': False,
            'cookies_or_credentials': False,
            'subtitle_contents': False,
        },
        'observation_sources': {
            'player_position_seconds': 'xbmc.Player.getTime',
            'player_total_seconds': 'xbmc.Player.getTotalTime',
            'video_resolution': 'Kodi InfoLabel VideoPlayer.VideoResolution',
            'video_bitrate': 'Kodi InfoLabel VideoPlayer.VideoBitrate',
            'cache_read_ahead': 'Kodi Player.Cache* InfoLabels when exposed',
            'per_segment_http_timing': (
                'Appi Buffered Look Ahead proxy request/download measurements'
                if buffered_proxy
                else 'not exposed by supported Kodi Python player API'
            ),
            'playlist_refresh_history': (
                'Appi Buffered Look Ahead proxy playlist requests'
                if buffered_proxy
                else 'not exposed by supported Kodi Python player API'
            ),
            'proxy_buffer_depth': (
                'Appi Buffered Look Ahead disk queue'
                if buffered_proxy
                else 'not applicable'
            ),
            'inputstream_exact_buffer_queue': 'not exposed by supported Kodi Python player API',
            'representation_history': 'derived from sampled Kodi resolution/bitrate InfoLabels',
        },
        'limitations': [
            'Kodi/InputStream Adaptive do not expose reliable per-segment HTTP request timing to the supported add-on Python player API.',
            'Player.Cache* InfoLabels are sampled when present; an empty label is recorded as unavailable rather than treated as zero.',
            'Representation changes are observed from Kodi video resolution/bitrate labels and may not expose every internal ABR decision.',
            'Configured cache capacity is not treated as evidence that playable media was actually buffered.',
        ],
        'events': [],
    }
    _append(payload, 'prepared', {
        'engine': engine or 'unknown',
        'hls_mode': options.get('hls_mode'),
        'manual_variant_identity': options.get('manual_variant_identity'),
        'manual_variant_width': options.get('manual_variant_width'),
        'manual_variant_height': options.get('manual_variant_height'),
        'manual_variant_bandwidth': options.get('manual_variant_bandwidth'),
        'manual_variant_peak_bandwidth': options.get('manual_variant_peak_bandwidth'),
        'manual_variant_codecs': options.get('manual_variant_codecs'),
        'buffered_proxy': buffered_proxy,
        'buffer_target_seconds': options.get('buffer_target_seconds'),
        'buffer_startup_seconds': options.get('buffer_startup_seconds'),
    })
    _write(ACTIVE, payload)
    return session_id


def event(name, **fields):
    if not enabled():
        return
    payload = _read(ACTIVE)
    if not payload:
        return
    safe = {}
    for key, value in fields.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[str(key)] = value
    _append(payload, name, safe)
    _write(ACTIVE, payload)


def player_started(player=None):
    global _last_position, _last_advance, _stall_started, _last_representation
    if not enabled():
        return
    _last_position = None
    _last_advance = time.monotonic()
    _stall_started = None
    _last_representation = None
    cache_state, cache_sources = _cache_snapshot()
    representation = _representation_snapshot()
    _last_representation = representation
    event(
        'av_started',
        resolution=representation.get('resolution'),
        bitrate=representation.get('bitrate'),
        audio_language=_info_label('VideoPlayer.AudioLanguage'),
        subtitle_language=_info_label('VideoPlayer.SubtitlesLanguage'),
        cache_json=json.dumps(cache_state, sort_keys=True),
        cache_sources_json=json.dumps(cache_sources, sort_keys=True),
    )


def sample(player):
    global _last_position, _last_advance, _stall_started, _last_representation
    if not enabled():
        return
    payload = _read(ACTIVE)
    if not payload:
        return
    try:
        position = float(player.getTime())
    except Exception:
        position = -1.0
    try:
        total = float(player.getTotalTime())
    except Exception:
        total = -1.0
    now = time.monotonic()
    representation = _representation_snapshot()
    cache_state, cache_sources = _cache_snapshot()

    if _last_representation is not None and representation != _last_representation:
        _append(payload, 'representation_change', {
            'from_resolution': _last_representation.get('resolution'),
            'from_bitrate': _last_representation.get('bitrate'),
            'to_resolution': representation.get('resolution'),
            'to_bitrate': representation.get('bitrate'),
            'observation': 'Kodi VideoPlayer InfoLabels',
        })
    _last_representation = representation

    advanced = False
    if position >= 0:
        if _last_position is None or position > _last_position + 0.2:
            advanced = True
            if _stall_started is not None:
                _append(payload, 'stall_end', {
                    'position': round(position, 3),
                    'duration': round(now - _stall_started, 3),
                    'resolution': representation.get('resolution'),
                    'bitrate': representation.get('bitrate'),
                    'cache_json': json.dumps(cache_state, sort_keys=True),
                })
                _stall_started = None
            _last_advance = now
        elif _last_advance is not None and now - _last_advance >= STALL_SECONDS and _stall_started is None:
            _stall_started = now
            _append(payload, 'stall_start', {
                'position': round(position, 3),
                'stalled_for_before_detection': round(now - _last_advance, 3),
                'resolution': representation.get('resolution'),
                'bitrate': representation.get('bitrate'),
                'cache_json': json.dumps(cache_state, sort_keys=True),
            })
        _last_position = position

    _append(payload, 'sample', {
        'position': round(position, 3),
        'total': round(total, 3),
        'advanced': advanced,
        'resolution': representation.get('resolution'),
        'bitrate': representation.get('bitrate'),
        'cache_json': json.dumps(cache_state, sort_keys=True),
        'cache_sources_json': json.dumps(cache_sources, sort_keys=True),
        'audio_language': _info_label('VideoPlayer.AudioLanguage'),
        'subtitle_language': _info_label('VideoPlayer.SubtitlesLanguage'),
    })
    _write(ACTIVE, payload)


def _recent_samples(payload, before_at, seconds=PRESTALL_SECONDS):
    start = float(before_at or 0) - float(seconds)
    return [
        item for item in payload.get('events', [])
        if item.get('event') == 'sample' and start <= float(item.get('at') or 0) <= float(before_at or 0)
    ]


def _analysis(payload):
    stalls = [item for item in payload.get('events', []) if item.get('event') == 'stall_start']
    transitions = [item for item in payload.get('events', []) if item.get('event') == 'representation_change']
    cache_seen = False
    cache_near_empty_before_stall = False
    for stall in stalls:
        for sample_event in _recent_samples(payload, stall.get('at')):
            raw = (sample_event.get('fields') or {}).get('cache_json') or '{}'
            try:
                cache = json.loads(raw)
            except (ValueError, TypeError):
                cache = {}
            if cache:
                cache_seen = True
            for key in ('level_percent', 'progress_percent'):
                numeric = ((cache.get(key) or {}).get('numeric'))
                if numeric is not None and numeric <= 5:
                    cache_near_empty_before_stall = True

    classifications = []
    if transitions:
        classifications.append({
            'category': 'abr_transition_behavior',
            'support': 'observed',
            'reason': '{} resolution/bitrate transition(s) were observed through Kodi InfoLabels.'.format(len(transitions)),
        })
    if stalls and cache_near_empty_before_stall:
        classifications.append({
            'category': 'shallow_or_empty_read_ahead',
            'support': 'suggestive',
            'reason': 'A Kodi cache/progress label was at or below 5 percent within the pre-stall sampling window.',
        })
    elif stalls and cache_seen:
        classifications.append({
            'category': 'buffer_state_observed',
            'support': 'observed',
            'reason': 'Kodi cache/read-ahead labels were available around at least one stall; inspect the timeline for exact values.',
        })
    if stalls:
        classifications.append({
            'category': 'server_or_segment_delay',
            'support': 'insufficient_evidence',
            'reason': 'Stalls were observed, but per-segment HTTP timings are not exposed by the supported Kodi Python player API.',
        })
        classifications.append({
            'category': 'sustained_insufficient_throughput',
            'support': 'insufficient_evidence',
            'reason': 'Playback bitrate labels are observable, but direct segment byte/time measurements are unavailable.',
        })
    if not classifications:
        classifications.append({
            'category': 'insufficient_evidence',
            'support': 'insufficient_evidence',
            'reason': 'No stall or representation-transition evidence was captured in this session.',
        })
    return {
        'stall_count': len(stalls),
        'representation_change_count': len(transitions),
        'cache_labels_observed': cache_seen,
        'classifications': classifications,
    }


def finish(result='stopped'):
    global _last_position, _last_advance, _stall_started, _last_representation
    if not enabled():
        return None
    payload = _read(ACTIVE)
    if not payload:
        return None
    now = time.time()
    if _stall_started is not None:
        _append(payload, 'stall_end', {
            'duration': round(max(0.0, time.monotonic() - _stall_started), 3),
            'reason': 'playback_session_finished',
        })
    payload['finished_at'] = now
    payload['result'] = result
    _append(payload, result, {})
    payload['analysis'] = _analysis(payload)
    session_id = payload.get('session_id') or str(int(payload['finished_at']))
    destination = os.path.join(ROOT, 'session-{}.json'.format(session_id))
    _write(destination, payload)
    try:
        os.remove(ACTIVE)
    except FileNotFoundError:
        pass
    sessions = sorted(
        [path for path in (os.path.join(ROOT, name) for name in os.listdir(ROOT)) if os.path.basename(path).startswith('session-') and path.endswith('.json')],
        key=lambda path: os.path.getmtime(path),
        reverse=True,
    )
    for path in sessions[MAX_SESSIONS:]:
        try:
            os.remove(path)
        except OSError:
            pass
    _last_position = None
    _last_advance = None
    _stall_started = None
    _last_representation = None
    return destination


def _latest_session():
    candidates = []
    if os.path.isfile(ACTIVE):
        candidates.append(ACTIVE)
    if os.path.isdir(ROOT):
        candidates.extend(
            os.path.join(ROOT, name)
            for name in os.listdir(ROOT)
            if name.startswith('session-') and name.endswith('.json')
        )
    candidates = [path for path in candidates if os.path.isfile(path)]
    return max(candidates, key=os.path.getmtime) if candidates else None


def export_latest(destination_root):
    source = _latest_session()
    if not source:
        raise RuntimeError('No diagnostic session is available to export.')
    destination_root = (destination_root or '').strip()
    if not destination_root:
        raise RuntimeError('Choose a diagnostic export folder in Appi settings first.')
    payload = _read(source)
    if not payload:
        raise RuntimeError('The latest diagnostic session could not be read.')
    _ensure()
    stamp = time.strftime('%Y%m%d-%H%M%S', time.localtime(payload.get('started_at') or time.time()))
    filename = 'appi-diagnostics-{}-{}.zip'.format(stamp, payload.get('session_id') or 'session')
    local_zip = os.path.join(ROOT, filename)
    readme = (
        'Appi playback diagnostics schema 2\n\n'
        'This bundle intentionally excludes credentials, cookies, query strings, full URLs, subtitle contents and unrelated Kodi history.\n'
        'The timeline records player progress, stalls, resolution/bitrate transitions and Kodi cache/read-ahead InfoLabels when the installed build exposes them.\n'
        'Per-segment HTTP timings and exact InputStream Adaptive queue/representation internals are explicitly marked unavailable when Kodi does not expose them through the supported Python player API.\n'
        'Configured cache capacity is never treated as proof that playable media was actually buffered.\n'
    )
    with zipfile.ZipFile(local_zip, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('summary.json', json.dumps(payload, ensure_ascii=False, indent=2))
        archive.writestr('README.txt', readme)
    target = destination_root.rstrip('/\\') + '/' + filename
    try:
        if not xbmcvfs.exists(destination_root):
            xbmcvfs.mkdirs(destination_root)
        if not xbmcvfs.copy(local_zip, target):
            raise OSError('Kodi VFS copy returned false')
    finally:
        try:
            os.remove(local_zip)
        except OSError:
            pass
    return target


def status():
    sessions = []
    if os.path.isdir(ROOT):
        sessions = [
            name for name in os.listdir(ROOT)
            if name.startswith('session-') and name.endswith('.json')
        ]
    return {'enabled': enabled(), 'sessions': len(sessions), 'active': os.path.isfile(ACTIVE)}
