"""Lightweight, non-modal buffer text on Kodi's fullscreen video window."""
import xbmcgui


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

    def update(self, status, debug=False, playing=False):
        text = status_text(status, debug, playing)
        if not text:
            self.close()
            return
        if self.label is None:
            self.window = xbmcgui.Window(12005)
            self.label = xbmcgui.ControlLabel(30, 30, 1100, 45, '', textColor='FFFFFFFF')
            self.window.addControl(self.label)
        self.label.setLabel(text)

    def close(self):
        if self.label is not None:
            self.window.removeControl(self.label)
            self.label = None
            self.window = None
