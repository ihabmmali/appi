"""Lightweight, non-modal buffer text on Kodi's fullscreen video window."""
import xbmc
import xbmcgui


WINDOW_FULLSCREEN_VIDEO = 12005


def status_text(status, debug, playing):
    if not status:
        return ''
    if debug and playing:
        return 'Appi buffer: {:.1f} MB / {} MB | {:.1f} s ahead{}'.format(
            status['cached_ahead_bytes'] / 1048576.0,
            status['buffer_capacity_mb'], status['buffered_seconds'],
            ' | Buffering…' if status.get('recovering') else '')
    if status.get('recovering'):
        return 'Appi — Buffering…'
    return ''


class BufferOverlay:
    def __init__(self):
        self.window = None
        self.label = None
        self._last_failure = ''

    def _failure(self, operation, exc):
        message = '{}: {}: {}'.format(operation, type(exc).__name__, exc)
        if message != self._last_failure:
            xbmc.log(
                'Appi buffered overlay {} failed: {}: {}'.format(
                    operation, type(exc).__name__, exc
                ),
                xbmc.LOGWARNING,
            )
            self._last_failure = message

    def update(self, status, debug=False, playing=False):
        text = status_text(status, debug, playing)
        if not text:
            self.close()
            return
        if self.label is None:
            try:
                window = xbmcgui.Window(WINDOW_FULLSCREEN_VIDEO)
            except Exception as exc:
                self._failure('Window({})'.format(WINDOW_FULLSCREEN_VIDEO), exc)
                return
            try:
                label = xbmcgui.ControlLabel(
                    30, 30, 1100, 45, '', textColor='FFFFFFFF'
                )
            except Exception as exc:
                self._failure('ControlLabel', exc)
                return
            try:
                window.addControl(label)
            except Exception as exc:
                self._failure('addControl', exc)
                return
            self.window = window
            self.label = label
        try:
            self.label.setLabel(text)
            self._last_failure = ''
        except Exception as exc:
            self._failure('setLabel', exc)
            self.close()

    def close(self):
        window, label = self.window, self.label
        self.label = None
        self.window = None
        if label is not None and window is not None:
            try:
                window.removeControl(label)
                self._last_failure = ''
            except Exception as exc:
                self._failure('removeControl', exc)
