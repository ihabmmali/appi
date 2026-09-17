import json
import os
from datetime import datetime, timezone

import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon()
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))


def _ensure_profile():
    if not xbmcvfs.exists(PROFILE):
        xbmcvfs.mkdirs(PROFILE)


def _path(name):
    _ensure_profile()
    return os.path.join(PROFILE, '{}.json'.format(name))


def _read(name):
    path = _path(name)
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            return json.load(handle)
    except (OSError, ValueError, TypeError):
        return None


def _write(name, payload):
    path = _path(name)
    temp_path = path + '.tmp'
    with open(temp_path, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, ensure_ascii=False, separators=(',', ':'))
    os.replace(temp_path, path)


def load(name):
    payload = _read(name)
    if isinstance(payload, dict) and isinstance(payload.get('items'), list):
        return payload
    return None


def save(name, items):
    _write(name, {'fetched_at': datetime.now(timezone.utc).isoformat(), 'items': items})


def load_object(name):
    payload = _read(name)
    return payload if isinstance(payload, dict) else None


def save_object(name, value):
    _write(name, value if isinstance(value, dict) else {})


def remove(name):
    try:
        os.remove(_path(name))
    except FileNotFoundError:
        pass


def remove_prefix(prefix, keep=None):
    _ensure_profile()
    keep = set(keep or [])
    try:
        names = os.listdir(PROFILE)
    except OSError:
        return
    for filename in names:
        if not filename.startswith(prefix) or not filename.endswith('.json'):
            continue
        cache_name = filename[:-5]
        if cache_name in keep:
            continue
        try:
            os.remove(os.path.join(PROFILE, filename))
        except OSError:
            pass
