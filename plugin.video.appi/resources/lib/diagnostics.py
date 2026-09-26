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
MAX_EVENTS = 1000
MAX_SESSIONS = 5
_STALL_SECONDS = 4.0
_last_position = None
_last_advance = None


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
    parsed = urlparse(url or '')
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


def prepare_playback(catalog, ref, media_url, stream_kind, engine, options=None):
    if not enabled():
        return None
    _ensure()
    now = time.time()
    session_id = hashlib.sha1('{}|{}|{}|{}'.format(now, catalog, ref, media_url).encode('utf-8')).hexdigest()[:16]
    payload = {
        'schema': 1,
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
        'options': dict(options or {}),
        'availability': {
            'player_position_seconds': True,
            'player_total_seconds': True,
            'video_resolution_info_label': True,
            'video_bitrate_info_label': True,
            'audio_language_info_label': True,
            'subtitle_language_info_label': True,
            'per_segment_http_timing': False,
            'inputstream_buffer_level': False,
            'representation_bitrate_history': False,
            'raw_authenticated_url': False,
            'cookies_or_credentials': False,
            'subtitle_contents': False,
        },
        'events': [],
    }
    _write(ACTIVE, payload)
    event('prepared')
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
    payload.setdefault('events', []).append({
        'at': time.time(),
        'event': str(name),
        'fields': safe,
    })
    payload['events'] = payload['events'][-MAX_EVENTS:]
    _write(ACTIVE, payload)


def player_started(player=None):
    global _last_position, _last_advance
    if not enabled():
        return
    _last_position = None
    _last_advance = time.monotonic()
    event(
        'av_started',
        resolution=_info_label('VideoPlayer.VideoResolution'),
        bitrate=_info_label('VideoPlayer.VideoBitrate'),
        audio_language=_info_label('VideoPlayer.AudioLanguage'),
        subtitle_language=_info_label('VideoPlayer.SubtitlesLanguage'),
    )


def sample(player):
    global _last_position, _last_advance
    if not enabled() or not _read(ACTIVE):
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
    if position >= 0:
        if _last_position is None or position > _last_position + 0.2:
            _last_advance = now
        elif _last_advance is not None and now - _last_advance >= _STALL_SECONDS:
            event(
                'possible_stall',
                position=round(position, 3),
                stalled_for=round(now - _last_advance, 3),
                resolution=_info_label('VideoPlayer.VideoResolution'),
                bitrate=_info_label('VideoPlayer.VideoBitrate'),
            )
            _last_advance = now
        _last_position = position
    event(
        'sample',
        position=round(position, 3),
        total=round(total, 3),
        resolution=_info_label('VideoPlayer.VideoResolution'),
        bitrate=_info_label('VideoPlayer.VideoBitrate'),
        audio_language=_info_label('VideoPlayer.AudioLanguage'),
        subtitle_language=_info_label('VideoPlayer.SubtitlesLanguage'),
    )


def finish(result='stopped'):
    global _last_position, _last_advance
    if not enabled():
        return None
    payload = _read(ACTIVE)
    if not payload:
        return None
    payload['finished_at'] = time.time()
    payload['result'] = result
    payload.setdefault('events', []).append({
        'at': payload['finished_at'],
        'event': result,
        'fields': {},
    })
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
        'Appi playback diagnostics\n\n'
        'This bundle intentionally excludes credentials, cookies, query strings, full URLs, subtitle contents and unrelated Kodi history.\n'
        'Kodi Python exposes playback events/position and selected InfoLabels, but not reliable per-segment HTTP timings, raw inputstream buffer level or representation bitrate history.\n'
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
