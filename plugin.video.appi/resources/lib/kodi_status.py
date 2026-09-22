import json

import xbmc


def details(path):
    """Read Kodi's canonical play count and resume bookmark for a plugin URL."""
    if not path:
        return {'available': False, 'playcount': 0, 'resume': 0.0, 'total': 0.0}
    request = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'Files.GetFileDetails',
        'params': {
            'file': path,
            'media': 'video',
            'properties': ['playcount', 'resume'],
        },
    }
    try:
        response = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
        value = (response.get('result') or {}).get('filedetails') or {}
        resume = value.get('resume') if isinstance(value.get('resume'), dict) else {}
        return {
            'available': 'playcount' in value or bool(resume),
            'playcount': int(value.get('playcount') or 0),
            'resume': float(resume.get('position') or 0),
            'total': float(resume.get('total') or 0),
        }
    except Exception as exc:
        xbmc.log('Appi could not read Kodi playback status: {}'.format(exc), xbmc.LOGWARNING)
        return {'available': False, 'playcount': 0, 'resume': 0.0, 'total': 0.0}


def is_watched(path):
    value = details(path)
    return value['available'] and value['playcount'] > 0


def set_watched(path, watched=True):
    """Update Kodi's canonical play count for a plugin playback URL."""
    if not path:
        return False
    request = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'Files.SetFileDetails',
        'params': {
            'file': path,
            'media': 'video',
            'playcount': 1 if watched else 0,
        },
    }
    try:
        response = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
        return response.get('result') == 'OK' and not response.get('error')
    except Exception as exc:
        xbmc.log('Appi could not update Kodi playback status: {}'.format(exc), xbmc.LOGWARNING)
        return False
