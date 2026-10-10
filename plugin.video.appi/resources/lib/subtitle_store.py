import hashlib
import json
import os
import shutil
import tempfile
import time

import xbmcaddon
import xbmcvfs


ADDON = xbmcaddon.Addon()
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
TEMP = xbmcvfs.translatePath('special://temp/')
SUB_ROOT = os.path.join(PROFILE, 'saved_subtitles')
INDEX_PATH = os.path.join(SUB_ROOT, 'index.json')
SESSION_PATH = os.path.join(SUB_ROOT, 'session.json')
SUB_EXTENSIONS = {'.srt', '.ass', '.ssa', '.sub', '.vtt', '.smi'}


def _ensure_dirs():
    os.makedirs(SUB_ROOT, exist_ok=True)


def _atomic_json(path, payload):
    _ensure_dirs()
    # Separate plugin and service processes may write concurrently. A shared
    # `.tmp` filename can make one process rename the other's temp file.
    descriptor, temporary = tempfile.mkstemp(prefix='.appi-sub-', dir=os.path.dirname(path))
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as handle:
            json.dump(payload, handle, ensure_ascii=False, separators=(',', ':'))
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)


def _read_json(path, default):
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            value = json.load(handle)
        return value
    except (OSError, ValueError, TypeError):
        return default


def media_key(catalog, ref):
    return hashlib.sha1('{}|{}'.format(catalog, ref).encode('utf-8')).hexdigest()


_ROOTS_CACHE = (0.0, [])


def _subtitle_roots():
    """Scan the normal temp area and Kodi's configured local subtitle folder.

    Player.getSubtitles() reports a language, not a filename. A provider's
    custom download folder is therefore discovered from Kodi settings.
    Network paths are deliberately not walked with os.walk.
    """
    global _ROOTS_CACHE
    now = time.monotonic()
    if now - _ROOTS_CACHE[0] < 30.0:
        return list(_ROOTS_CACHE[1])
    roots = [TEMP]
    try:
        import xbmc
        request = {
            'jsonrpc': '2.0', 'id': 1, 'method': 'Settings.GetSettingValue',
            'params': {'setting': 'subtitles.storagemode'},
        }
        mode = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
        if mode.get('result', {}).get('value') == 1:
            request['params']['setting'] = 'subtitles.custompath'
            reply = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
            chosen = reply.get('result', {}).get('value') or ''
            if chosen and '://' not in chosen.replace('special://', ''):
                folder = xbmcvfs.translatePath(chosen)
                if folder and os.path.isdir(folder):
                    roots.append(folder)
    except (AttributeError, TypeError, ValueError, OSError):
        pass
    roots = list(dict.fromkeys(roots))
    _ROOTS_CACHE = (now, roots)
    return list(roots)


def _diagnostic(event, session, **fields):
    """Bounded filename-free lifecycle evidence; never log subtitle contents."""
    try:
        import xbmc
        payload = {'media_key': session.get('key', ''), 'event': event}
        payload.update(fields)
        xbmc.log('Appi subtitle persistence ' + json.dumps(payload, sort_keys=True),
                 getattr(xbmc, 'LOGINFO', 1))
    except Exception:
        pass


def _snapshot_temp():
    result = {}
    # A two-level scan missed provider cache folders. Keep a bounded walk
    # rather than recursing through the entire Kodi add-on/user-data tree.
    for root_directory in _subtitle_roots():
        if not root_directory or not os.path.isdir(root_directory):
            continue
        checked = 0
        for root, dirs, files in os.walk(root_directory):
            relative = os.path.relpath(root, root_directory)
            depth = 0 if relative == '.' else relative.count(os.sep) + 1
            dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(root, d))]
            if depth >= 4:
                dirs[:] = []
            for name in files:
                if checked >= 2000:
                    dirs[:] = []
                    break
                checked += 1
                if os.path.splitext(name)[1].lower() not in SUB_EXTENSIONS:
                    continue
                path = os.path.join(root, name)
                # Never recapture Appi's own persistence folder.
                if os.path.commonpath([os.path.abspath(SUB_ROOT), os.path.abspath(path)]) == os.path.abspath(SUB_ROOT):
                    continue
                try:
                    stat = os.stat(path)
                except OSError:
                    continue
                result[path] = [int(stat.st_mtime_ns), int(stat.st_size)]
            if checked >= 2000:
                break
    return result


def _index():
    value = _read_json(INDEX_PATH, {})
    return value if isinstance(value, dict) else {}


def saved_subtitles(catalog, ref):
    entry = _index().get(media_key(catalog, ref), {})
    files = entry.get('files') if isinstance(entry, dict) else []
    return [path for path in (files or []) if os.path.isfile(path)]


def last_saved_subtitle(catalog, ref):
    entry = _index().get(media_key(catalog, ref), {})
    path = entry.get('last') if isinstance(entry, dict) else None
    return path if path and os.path.isfile(path) else None


def prepare_session(catalog, ref, subtitle_mode='global'):
    _ensure_dirs()
    payload = {
        'catalog': catalog,
        'ref': ref,
        'key': media_key(catalog, ref),
        'started_at': time.time(),
        'baseline': _snapshot_temp(),
        'pending': {},
        'subtitle_mode': subtitle_mode if subtitle_mode in {'global', 'saved', 'off', 'search'} else 'global',
    }
    _atomic_json(SESSION_PATH, payload)
    _diagnostic('session-start', payload, baseline_count=len(payload['baseline']))
    return saved_subtitles(catalog, ref)


def load_session():
    value = _read_json(SESSION_PATH, None)
    return value if isinstance(value, dict) else None


def clear_session():
    try:
        os.remove(SESSION_PATH)
    except FileNotFoundError:
        pass


def clear_all():
    shutil.rmtree(SUB_ROOT, ignore_errors=True)


def _unique_destination(folder, source):
    base = os.path.basename(source)
    stem, ext = os.path.splitext(base)
    destination = os.path.join(folder, base)
    counter = 2
    while os.path.exists(destination):
        try:
            if os.path.getsize(destination) == os.path.getsize(source):
                with open(destination, 'rb') as existing, open(source, 'rb') as incoming:
                    if hashlib.sha1(existing.read()).digest() == hashlib.sha1(incoming.read()).digest():
                        return destination
        except OSError:
            pass
        destination = os.path.join(folder, '{}-{}{}'.format(stem, counter, ext))
        counter += 1
    return destination


def capture_temp_changes(finalize=False):
    session = load_session()
    if not session:
        return []

    baseline = session.get('baseline') or {}
    pending = session.get('pending') or {}
    current = _snapshot_temp()
    copied = []

    for path, fingerprint in current.items():
        if baseline.get(path) == fingerprint:
            pending.pop(path, None)
            continue

        # Wait for one unchanged polling interval before copying so subtitle
        # add-ons have time to finish writing/extracting the file.
        previous = pending.get(path)
        if previous != fingerprint and not finalize:
            pending[path] = fingerprint
            _diagnostic('file-observed', session, source_id=hashlib.sha1(path.encode('utf-8')).hexdigest()[:12],
                        bytes=fingerprint[1])
            continue

        if fingerprint[1] <= 0:
            continue
        key = session.get('key') or media_key(session.get('catalog', ''), session.get('ref', ''))
        folder = os.path.join(SUB_ROOT, key)
        os.makedirs(folder, exist_ok=True)
        destination = _unique_destination(folder, path)
        if not os.path.exists(destination):
            temporary = destination + '.partial'
            try:
                shutil.copy2(path, temporary)
                os.replace(temporary, destination)
            except OSError as exc:
                _diagnostic('copy-failed', session, error=type(exc).__name__)
                try:
                    os.remove(temporary)
                except OSError:
                    pass
                continue
        copied.append(destination)
        _diagnostic('file-captured', session, bytes=fingerprint[1],
                    final_pass=bool(finalize))
        baseline[path] = fingerprint
        pending.pop(path, None)

    # Keep the original baseline for changed/new files until they have been
    # copied. Advancing baseline to every current fingerprint here would make a
    # newly noticed file look unchanged on the next poll before it is saved.
    for path in list(pending):
        if path not in current:
            pending.pop(path, None)
    session['baseline'] = baseline
    session['pending'] = pending
    _atomic_json(SESSION_PATH, session)

    if copied:
        index = _index()
        key = session['key']
        entry = index.get(key, {}) if isinstance(index.get(key), dict) else {}
        existing = [path for path in entry.get('files', []) if os.path.isfile(path)]
        for path in copied:
            if path not in existing:
                existing.append(path)
        entry['files'] = existing
        entry['last'] = copied[-1]
        entry['updated_at'] = time.time()
        index[key] = entry
        _atomic_json(INDEX_PATH, index)
        _diagnostic('index-updated', session, count=len(existing),
                    last_exists=os.path.isfile(entry['last']))
    elif finalize:
        _diagnostic('final-pass-no-new-files', session, observed_count=len(current),
                    pending_count=len(pending))
    return copied
