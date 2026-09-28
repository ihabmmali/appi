"""Skin-independent Buffered Look Ahead status overlay."""
try:
    import xbmc
except ImportError:  # pragma: no cover
    xbmc = None
import xbmcgui


def _bytes(value):
    value = max(0, int(value or 0))
    if value < 1024 * 1024:
        return '{:.0f} KB'.format(value / 1024.0)
    return '{:.1f} MB'.format(value / 1048576.0)


def status_text(status, debug, playing):
    if not status or not playing:
        return ''
    current = _bytes(status.get('cached_ahead_bytes', 0))
    target = _bytes(
        status.get('buffer_target_bytes')
        or status.get('high_water_bytes')
        or int(status.get('buffer_capacity_mb', 0)) * 1048576
    )
    if debug:
        parts = [
            'Appi buffer: {} / {}'.format(current, target),
            '{:.1f} s ahead'.format(float(status.get('buffered_seconds') or 0)),
            str(status.get('buffer_state') or 'unknown'),
            'epoch {}'.format(status.get('epoch_id', '?')),
        ]
        selected = float(status.get('selected_bitrate_mbps') or 0)
        throughput = float(status.get('throughput_mbps') or 0)
        if selected:
            parts.append('{:.2f} Mbit/s selected'.format(selected))
        if throughput:
            parts.append('{:.2f} Mbit/s provider'.format(throughput))
        return ' | '.join(parts)
    if status.get('recovering'):
        return 'Appi buffering — {} / {}'.format(current, target)
    return ''


class BufferOverlay:
    def __init__(self):
        self.window = None
        self.label = None
        self._last_failure = ''

    def _failure(self, operation, exc):
        message = '{}: {}: {}'.format(operation, type(exc).__name__, exc)
        if message != self._last_failure:
            if xbmc is not None:
                xbmc.log(
                    'Appi buffered overlay {} failed: {}: {}'.format(
                        operation, type(exc).__name__, exc
                    ),
                    getattr(xbmc, 'LOGWARNING', 2),
                )
            self._last_failure = message

    def _create(self):
        try:
            window = xbmcgui.WindowDialog()
        except Exception as exc:
            self._failure('WindowDialog', exc)
            return False
        try:
            label = xbmcgui.ControlLabel(
                40, 45, 1180, 55, '',
                textColor='FFFFFFFF', shadowColor='FF000000'
            )
        except Exception as exc:
            self._failure('ControlLabel', exc)
            try:
                window.close()
            except Exception:
                pass
            return False
        try:
            window.addControl(label)
        except Exception as exc:
            self._failure('addControl', exc)
            try:
                window.close()
            except Exception:
                pass
            return False
        try:
            window.show()
        except Exception as exc:
            self._failure('show', exc)
            try:
                window.close()
            except Exception:
                pass
            return False
        self.window = window
        self.label = label
        return True

    def update(self, status, debug=False, playing=False):
        text = status_text(status, debug, playing)
        if not text:
            self.close()
            return
        if self.label is None and not self._create():
            return
        try:
            self.label.setLabel(text)
            self._last_failure = ''
        except Exception as exc:
            self._failure('setLabel', exc)
            self.close()

    def close(self):
        window = self.window
        self.label = None
        self.window = None
        if window is not None:
            try:
                window.close()
                self._last_failure = ''
            except Exception as exc:
                self._failure('close', exc)
