"""Generate portable FFmpeg download jobs for execution outside Kodi.

Appi deliberately does not download media. It writes a small POSIX shell
script to a Kodi-accessible folder and leaves transfer/remux work to a media
server watcher that has FFmpeg installed.
"""

import hashlib
import os
import re
import time
import unicodedata

import xbmcaddon
import xbmcvfs

from . import metadata
from .catalog import item_ref


ADDON = xbmcaddon.Addon()
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))


def _safe_name(value, fallback):
    value = unicodedata.normalize('NFKC', str(value or '')).strip()
    value = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', value)
    value = re.sub(r'\s+', ' ', value).strip(' .')
    return value[:160].rstrip(' .') or fallback


def _vfs_join(root, name):
    root = str(root or '').rstrip('/\\')
    if not root:
        return name
    separator = '/' if '://' in root or root.startswith('special://') else os.sep
    return root + separator + name


def script_folder():
    configured = (ADDON.getSetting('download_folder') or '').strip()
    return configured or _vfs_join(PROFILE, 'download-scripts')


def _ensure_script_folder():
    folder = script_folder()
    if not xbmcvfs.exists(folder) and not xbmcvfs.mkdirs(folder):
        raise RuntimeError('Kodi could not create the download-script folder')
    return folder


def _shell_quote(value):
    """Quote one arbitrary value as a POSIX shell word."""
    return "'{}'".format(str(value).replace("'", "'\"'\"'"))


def _output_name(catalog, item, enriched=None):
    if catalog == 'movies':
        title = _safe_name(item.get('title') or item.get('display_title'), 'Movie')
        if item.get('year'):
            title = '{} ({})'.format(title, item['year'])
        return '{}.mp4'.format(title)

    show = _safe_name(item.get('show_title') or item.get('group_title'), 'TV Show')
    season = int(item.get('season') or 0)
    episode = int(item.get('episode') or 0)
    episode_title = (
        (enriched or {}).get('episode_title') or item.get('display_title') or 'Episode'
    )
    episode_title = _safe_name(episode_title, 'Episode')
    filename = '{} - S{:02d}E{:02d} - {}'.format(show, season, episode, episode_title)
    return '{}.mp4'.format(filename)


def _script_text(media_url, filename):
    partial_name = filename[:-4] + '.part.mp4'
    return '''#!/bin/sh
set -eu

FFMPEG="${{FFMPEG:-ffmpeg}}"
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
output="$script_dir"/{output}
partial="$script_dir"/{partial}

"$FFMPEG" -hide_banner -nostdin -y \\
  -i {url} \\
  -sn -dn -c copy -f mp4 "$partial"
mv -f -- "$partial" "$output"
'''.format(
        url=_shell_quote(media_url),
        output=_shell_quote(filename),
        partial=_shell_quote(partial_name),
    )


def _script_name(catalog, item):
    if catalog == 'movies':
        label = item.get('title') or item.get('display_title') or 'Movie'
    else:
        label = '{} S{:02d}E{:02d}'.format(
            item.get('show_title') or 'TV Show',
            int(item.get('season') or 0), int(item.get('episode') or 0),
        )
    identity = '{}|{}|{}'.format(catalog, item_ref(item), item.get('media_url') or '')
    suffix = hashlib.sha1(identity.encode('utf-8')).hexdigest()[:10]
    return '{}--{}.sh'.format(_safe_name(label, 'download'), suffix)


def generate(catalog, item, show_key=''):
    """Write one complete script through Kodi VFS and return its final path."""
    del show_key  # Retained in the API because TV callers already supply it.
    if catalog not in {'movies', 'tv'} or not item.get('media_url'):
        raise ValueError('Invalid download-script target')
    folder = _ensure_script_folder()
    payload = metadata.lookup_payload(item)
    filename = _output_name(catalog, item, metadata.get(payload) or {})
    final_path = _vfs_join(folder, _script_name(catalog, item))
    if xbmcvfs.exists(final_path):
        return {'created': False, 'path': final_path, 'filename': filename}

    temporary = final_path + '.tmp-{}'.format(int(time.time() * 1000))
    handle = None
    try:
        handle = xbmcvfs.File(temporary, 'w')
        written = handle.write(_script_text(item['media_url'], filename))
        handle.close()
        handle = None
        if written is False:
            raise OSError('Kodi could not write the complete download script')
        if not xbmcvfs.rename(temporary, final_path):
            raise OSError('Kodi could not finalize the download script')
    except Exception:
        if handle is not None:
            try:
                handle.close()
            except Exception:
                pass
        try:
            xbmcvfs.delete(temporary)
        except Exception:
            pass
        raise
    return {'created': True, 'path': final_path, 'filename': filename}


def status():
    folder = script_folder()
    count = 0
    error = ''
    try:
        if xbmcvfs.exists(folder):
            _directories, files = xbmcvfs.listdir(folder)
            count = sum(1 for name in files if name.lower().endswith('.sh'))
    except Exception as exc:
        error = '{}: {}'.format(type(exc).__name__, exc)
    return {
        'folder': folder,
        'scripts': count,
        'error': error,
    }
