import json
import os
import time

import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon()
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
LOCK_PATH = os.path.join(PROFILE, 'catalog_refresh.lock')
STATE_PATH = os.path.join(PROFILE, 'catalog_refresh_state.json')
STALE_LOCK_SECONDS = 2 * 60 * 60


def _ensure_profile():
    os.makedirs(PROFILE, exist_ok=True)


def acquire():
    _ensure_profile()
    try:
        if os.path.exists(LOCK_PATH) and time.time() - os.path.getmtime(LOCK_PATH) > STALE_LOCK_SECONDS:
            os.remove(LOCK_PATH)
    except OSError:
        pass
    try:
        descriptor = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    with os.fdopen(descriptor, 'w', encoding='ascii') as handle:
        handle.write(str(time.time()))
    return True


def release():
    try:
        os.remove(LOCK_PATH)
    except FileNotFoundError:
        pass


def load():
    try:
        with open(STATE_PATH, 'r', encoding='utf-8') as handle:
            value = json.load(handle)
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def record(success):
    _ensure_profile()
    value = load()
    value['last_attempt'] = time.time()
    if success:
        value['last_success'] = value['last_attempt']
        value['failures'] = 0
    else:
        value['failures'] = int(value.get('failures') or 0) + 1
    temp = STATE_PATH + '.tmp'
    with open(temp, 'w', encoding='utf-8') as handle:
        json.dump(value, handle, separators=(',', ':'))
    os.replace(temp, STATE_PATH)
    return value
