import hashlib
import json
import os
import shutil
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
    temp = path + '.tmp'
    with open(temp, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, ensure_ascii=False, separators=(',', ':'))
    os.replace(temp, path)


def _read_json(path, default):
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            return json.load(handle)
    except (OSError, ValueError, TypeError):
        return default


def media_key(catalog, ref):
    return hashlib.sha1('{}|{}'.format(catalog, ref).encode('utf-8')).hexdigest()


def _snapshot_temp():
    result = {}
    if not TEMP or not os.path.isdir(TEMP):
        return result
    for root, dirs, files in os.walk(TEMP):
        relative = os.path.relpath(root, TEMP)
        depth = 0 if relative == '.' else relative.count(os.sep) + 1
        if depth >= 2:
            dirs[:] = []
        for name in files:
            if os.path.splitext(name)[1].lower() not in SUB_EXTENSIONS:
                continue
            path = os.path.join(root, name)
            try:
                stat = os.stat(path)
            except OSError:
                continue
            result[path] = [int(stat.st_mtime_ns), int(stat.st_size)]
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


def prepare_session(catalog, ref):
    _ensure_dirs()
    _atomic_json(SESSION_PATH, {
        'catalog': catalog,
        'ref': ref,
        'key': media_key(catalog, ref),
        'started_at': time.time(),
        'baseline': _snapshot_temp(),
        'pending': {},
    })
    return saved_subtitles(catalog, ref)


def load_session():
    value = _read_json(SESSION_PATH, None)
    return value if isinstance(value, dict) else None


def clear_session():
    try:
        os.remove(SESSION_PATH)
    except FileNotFoundError:
        pass


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


def capture_temp_changes():
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
        previous = pending.get(path)
        if previous != fingerprint:
            pending[path] = fingerprint
            continue
        if fingerprint[1] <= 0:
            continue
        key = session.get('key') or media_key(session.get('catalog', ''), session.get('ref', ''))
        folder = os.path.join(SUB_ROOT, key)
        os.makedirs(folder, exist_ok=True)
        destination = _unique_destination(folder, path)
        if not os.path.exists(destination):
            try:
                shutil.copy2(path, destination)
            except OSError:
                continue
        copied.append(destination)
        baseline[path] = fingerprint
        pending.pop(path, None)
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
    return copied
