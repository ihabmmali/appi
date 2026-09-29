"""Skin-independent Buffered Look Ahead status overlay."""
try:
    import xbmc
except ImportError:  # pragma: no cover
    xbmc = None
try:
    import xbmcaddon
except ImportError:  # pragma: no cover
    xbmcaddon = None
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
    target = _bytes(status.get('buffer_target_bytes') or status.get('high_water_bytes')
                    or int(status.get('buffer_capacity_mb', 0)) * 1048576)
    if debug:
        parts = [
            'Appi buffer: {} / {}'.format(current, target),
            '{:.1f} s ahead'.format(float(status.get('buffered_seconds') or 0)),
            str(status.get('buffer_state') or 'unknown'),
            'epoch {} ({})'.format(status.get('epoch_id', '?'), status.get('epoch_reason') or 'play'),
        ]
        total_cached = int(status.get('total_cached_bytes') or 0)
        if total_cached:
            parts.append('{} cached total'.format(_bytes(total_cached)))
        missing = status.get('missing_next_tracks') or []
        if missing:
            parts.append('next missing: {}'.format(','.join(str(v) for v in missing)))
        attempt = int(status.get('recovery_attempt') or 0)
        if attempt:
            parts.append('retry {}'.format(attempt))
        selected = float(status.get('selected_bitrate_mbps') or 0)
        throughput = float(status.get('throughput_mbps') or 0)
        if selected:
            parts.append('{:.2f} Mbit/s selected'.format(selected))
        if throughput:
            parts.append('{:.2f} Mbit/s provider'.format(throughput))
        return ' | '.join(parts)
    if status.get('recovering'):
        text = 'Appi buffering — {} / {}'.format(current, target)
        attempt = int(status.get('recovery_attempt') or 0)
        if attempt:
            text += ' | retry {}'.format(attempt)
        if status.get('throughput_limited') and status.get('limitation_message'):
            text += ' | ' + str(status.get('limitation_message'))
        return text
    return ''


class BufferOverlay:
    CONTROL_ID = 100

    def __init__(self):
        self.window = None
        self.label = None
        self._last_failure = ''
        self._renderer = ''

    def _failure(self, operation, exc):
        message = '{}: {}: {}'.format(operation, type(exc).__name__, exc)
        if message != self._last_failure:
            if xbmc is not None:
                xbmc.log('Appi buffered overlay {} failed: {}: {}'.format(
                    operation, type(exc).__name__, exc),
                    getattr(xbmc, 'LOGWARNING', 2))
            self._last_failure = message

    def _create_xml(self):
        base = getattr(xbmcgui, 'WindowXMLDialog', None)
        if base is None:
            return False
        addon_path = ''
        if xbmcaddon is not None:
            try:
                addon_path = xbmcaddon.Addon().getAddonInfo('path') or ''
            except Exception:
                addon_path = ''
        if not addon_path:
            return False

        class OverlayDialog(base):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.appi_label = None
                self.pending_text = ''

            def onInit(self):
                try:
                    self.appi_label = self.getControl(BufferOverlay.CONTROL_ID)
                    if self.pending_text:
                        self.appi_label.setLabel(self.pending_text)
                except Exception:
                    self.appi_label = None

            def set_text(self, value):
                self.pending_text = value
                if self.appi_label is not None:
                    self.appi_label.setLabel(value)

        window = None
        try:
            window = OverlayDialog('AppiBufferOverlay.xml', addon_path, 'Default', '1080i')
            window.show()
            self.window = window
            self.label = window
            self._renderer = 'WindowXMLDialog'
            if xbmc is not None:
                xbmc.log('Appi buffered overlay renderer active: WindowXMLDialog',
                         getattr(xbmc, 'LOGINFO', 1))
            return True
        except Exception as exc:
            self._failure('WindowXMLDialog', exc)
            try:
                if window is not None:
                    window.close()
            except Exception:
                pass
            return False

    def _create_fallback(self):
        window = None
        try:
            window = xbmcgui.WindowDialog()
            label = xbmcgui.ControlLabel(
                40, 45, 1180, 55, '',
                textColor='FFFFFFFF', shadowColor='FF000000')
            window.addControl(label)
            window.show()
            self.window = window
            self.label = label
            self._renderer = 'WindowDialog-fallback'
            if xbmc is not None:
                xbmc.log('Appi buffered overlay using WindowDialog compatibility fallback',
                         getattr(xbmc, 'LOGWARNING', 2))
            return True
        except Exception as exc:
            self._failure('WindowDialog-fallback', exc)
            try:
                if window is not None:
                    window.close()
            except Exception:
                pass
            return False

    def _create(self):
        return self._create_xml() or self._create_fallback()

    def update(self, status, debug=False, playing=False):
        text = status_text(status, debug, playing)
        if not text:
            self.close()
            return
        if self.label is None and not self._create():
            return
        try:
            if self._renderer == 'WindowXMLDialog':
                self.label.set_text(text)
            else:
                self.label.setLabel(text)
            self._last_failure = ''
        except Exception as exc:
            self._failure('setLabel', exc)
            self.close()

    def close(self):
        window = self.window
        self.label = None
        self.window = None
        self._renderer = ''
        if window is not None:
            try:
                window.close()
                self._last_failure = ''
            except Exception as exc:
                self._failure('close', exc)
