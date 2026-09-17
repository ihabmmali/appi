import json

import xbmc

CACHE_SETTINGS = {
    'buffer_mode': 'filecache.buffermode',
    'memory_mb': 'filecache.memorysize',
    'read_factor': 'filecache.readfactor',
}


def _rpc(method, params):
    request = {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}
    response = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
    if 'error' in response:
        raise RuntimeError(response['error'].get('message') or str(response['error']))
    return response.get('result')


def _get(setting_id):
    result = _rpc('Settings.GetSettingValue', {'setting': setting_id})
    return result.get('value') if isinstance(result, dict) else None


def _set(setting_id, value):
    return _rpc('Settings.SetSettingValue', {'setting': setting_id, 'value': value})


def apply_mp4_cache(memory_mb=64, read_factor=4):
    desired = {
        CACHE_SETTINGS['buffer_mode']: 2,
        CACHE_SETTINGS['memory_mb']: max(0, int(memory_mb)),
        CACHE_SETTINGS['read_factor']: max(100, int(read_factor) * 100),
    }
    changed = []
    for setting_id, value in desired.items():
        try:
            if _get(setting_id) != value:
                _set(setting_id, value)
                changed.append(setting_id)
        except Exception as exc:
            xbmc.log('Appi could not set Kodi cache setting {}: {}'.format(setting_id, exc), xbmc.LOGWARNING)
    return changed
