import time

import xbmc
import xbmcaddon

from . import playback_history
from . import metadata
from . import subtitle_store

ADDON = xbmcaddon.Addon()


def _enabled(setting, default=True):
    value = ADDON.getSetting(setting)
    return default if value == '' else value.lower() == 'true'


class AppiPlayer(xbmc.Player):
    def __init__(self):
        super().__init__()
        self._search_opened_key = None

    def _subtitle_session(self):
        return subtitle_store.load_session() or {}

    def _apply_session_subtitles(self):
        session = self._subtitle_session()
        if not session:
            return
        mode = session.get('subtitle_mode') or 'global'
        key = session.get('key')

        if mode == 'search':
            if key and key != self._search_opened_key:
                self._search_opened_key = key
                try:
                    xbmc.executebuiltin('ActivateWindow(subtitlesearch)')
                except Exception as exc:
                    xbmc.log('Appi could not open subtitle search: {}'.format(exc), xbmc.LOGWARNING)
            return

        if mode == 'off':
            return
        if mode == 'global' and not _enabled('auto_saved_subtitles', True):
            return

        path = subtitle_store.last_saved_subtitle(session.get('catalog', ''), session.get('ref', ''))
        if path:
            try:
                self.setSubtitles(path)
                self.showSubtitles(True)
            except Exception as exc:
                xbmc.log('Appi could not restore saved subtitles: {}'.format(exc), xbmc.LOGWARNING)

    def _capture_progress(self):
        if not self.isPlayingVideo():
            return
        try:
            playback_history.update_progress(self.getTime(), self.getTotalTime())
        except Exception as exc:
            xbmc.log('Appi playback progress capture failed: {}'.format(exc), xbmc.LOGWARNING)

    def onAVStarted(self):
        self._apply_session_subtitles()
        self._capture_progress()

    def onAVChange(self):
        if _enabled('persist_subtitles', True):
            try:
                subtitle_store.capture_temp_changes()
            except Exception as exc:
                xbmc.log('Appi subtitle capture failed: {}'.format(exc), xbmc.LOGWARNING)
        self._capture_progress()

    def _finish(self, completed=False):
        if _enabled('persist_subtitles', True):
            try:
                subtitle_store.capture_temp_changes()
            except Exception:
                pass
        subtitle_store.clear_session()
        playback_history.finish_session(completed=completed)
        self._search_opened_key = None

    def onPlayBackStopped(self):
        self._finish(completed=False)

    def onPlayBackEnded(self):
        self._finish(completed=True)

    def onPlayBackError(self):
        self._finish(completed=False)


def run():
    monitor = xbmc.Monitor()
    player = AppiPlayer()
    next_progress_poll = 0.0
    next_metadata_poll = 0.0
    focused_value = ''
    focused_since = 0.0
    queued_focus = ''
    while not monitor.abortRequested():
        playing = player.isPlayingVideo()
        if playing and _enabled('persist_subtitles', True):
            try:
                subtitle_store.capture_temp_changes()
            except Exception as exc:
                xbmc.log('Appi subtitle polling failed: {}'.format(exc), xbmc.LOGWARNING)
        now = time.monotonic()
        if playing and now >= next_progress_poll:
            player._capture_progress()
            next_progress_poll = now + 5.0
        if not playing:
            next_progress_poll = 0.0
            try:
                value = xbmc.getInfoLabel('ListItem.Property(Appi.MetadataLookup)') or ''
            except Exception:
                value = ''
            if value != focused_value:
                focused_value = value
                focused_since = now
                queued_focus = ''
            if value and value != queued_focus and now - focused_since >= 3.0:
                payload = metadata.decode_focus(value)
                if payload:
                    metadata.queue(payload)
                queued_focus = value
        if now >= next_metadata_poll:
            # One lookup at a time avoids blocking directory navigation.
            # Playback pausing is controlled independently in metadata settings.
            try:
                metadata.process_one()
            except Exception as exc:
                xbmc.log('Appi metadata worker failed: {}'.format(exc), xbmc.LOGWARNING)
            next_metadata_poll = now + 2.0
        if monitor.waitForAbort(2.0):
            break
