import xbmc
import xbmcaddon

from . import subtitle_store

ADDON = xbmcaddon.Addon()


def _enabled(setting, default=True):
    value = ADDON.getSetting(setting)
    return default if value == '' else value.lower() == 'true'


class AppiPlayer(xbmc.Player):
    def _apply_saved(self):
        if not _enabled('persist_subtitles', True) or not _enabled('auto_saved_subtitles', True):
            return
        session = subtitle_store.load_session()
        if not session:
            return
        path = subtitle_store.last_saved_subtitle(session.get('catalog', ''), session.get('ref', ''))
        if path:
            try:
                self.setSubtitles(path)
                self.showSubtitles(True)
            except Exception as exc:
                xbmc.log('Appi could not restore saved subtitles: {}'.format(exc), xbmc.LOGWARNING)

    def onAVStarted(self):
        self._apply_saved()

    def onAVChange(self):
        if _enabled('persist_subtitles', True):
            try:
                subtitle_store.capture_temp_changes()
            except Exception as exc:
                xbmc.log('Appi subtitle capture failed: {}'.format(exc), xbmc.LOGWARNING)

    def _finish(self):
        if _enabled('persist_subtitles', True):
            try:
                subtitle_store.capture_temp_changes()
            except Exception:
                pass
        subtitle_store.clear_session()

    def onPlayBackStopped(self):
        self._finish()

    def onPlayBackEnded(self):
        self._finish()

    def onPlayBackError(self):
        self._finish()


def run():
    monitor = xbmc.Monitor()
    player = AppiPlayer()
    while not monitor.abortRequested():
        if player.isPlayingVideo() and _enabled('persist_subtitles', True):
            try:
                subtitle_store.capture_temp_changes()
            except Exception as exc:
                xbmc.log('Appi subtitle polling failed: {}'.format(exc), xbmc.LOGWARNING)
        if monitor.waitForAbort(2.0):
            break
