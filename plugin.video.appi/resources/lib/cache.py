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


def load(name):
    path = _path(name)
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            payload = json.load(handle)
        if isinstance(payload, dict) and isinstance(payload.get('items'), list):
            return payload
    except (OSError, ValueError, TypeError):
        return None
    return None


def save(name, items):
    path = _path(name)
    temp_path = path + '.tmp'
    payload = {
        'fetched_at': datetime.now(timezone.utc).isoformat(),
        'items': items,
    }
    with open(temp_path, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, ensure_ascii=False, separators=(',', ':'))
    os.replace(temp_path, path)


def remove(name):
    path = _path(name)
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
