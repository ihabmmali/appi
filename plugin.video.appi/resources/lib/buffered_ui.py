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
    # buffered_debug_overlay is the authoritative master gate.
    if not status or not playing or not debug:
        return ''
    current = _bytes(status.get('cached_ahead_bytes', 0))
    target = _bytes(status.get('buffer_target_bytes') or status.get('high_water_bytes')
                    or int(status.get('buffer_capacity_mb', 0)) * 1048576)
    total_cached = int(status.get('total_cached_bytes') or 0)
    line1 = 'Appi buffer: {} / {}'.format(current, target)
    if total_cached:
        line1 += ' | {} total'.format(_bytes(total_cached))

    line2 = '{:.1f} s ahead | {} | epoch {} ({})'.format(
        float(status.get('buffered_seconds') or 0),
        str(status.get('buffer_state') or 'unknown'),
        status.get('epoch_id', '?'),
        status.get('epoch_reason') or 'play',
    )

    selected = float(status.get('selected_bitrate_mbps') or 0)
    throughput = float(status.get('throughput_mbps') or 0)
    transport = []
    if selected:
        transport.append('{:.2f} Mbit/s selected'.format(selected))
    if throughput:
        transport.append('{:.2f} Mbit/s provider'.format(throughput))
    workers = int(status.get('active_fetch_count') or 0)
    limit = int(status.get('prefetch_concurrency') or 0)
    if limit:
        transport.append('{} active fetch / {} per-track limit'.format(workers, limit))
    line3 = ' | '.join(transport) if transport else 'Transport: waiting for samples'

    recovery = []
    if status.get('recovering'):
        recovery.append('recovering')
    attempt = int(status.get('recovery_attempt') or 0)
    if attempt:
        recovery.append('retry {}'.format(attempt))
    missing = status.get('missing_next_tracks') or []
    if missing:
        recovery.append('next missing: {}'.format(','.join(str(v) for v in missing)))
    if status.get('throughput_limited') and status.get('limitation_message'):
        recovery.append(str(status.get('limitation_message')))
    line4 = ' | '.join(recovery) if recovery else 'Recovery: idle'
    return '\n'.join((line1, line2, line3, line4))


class _FallbackMultiline:
    def __init__(self, labels):
        self.labels = list(labels)

    def set_text(self, value):
        lines = (value or '').splitlines()
        for index, label in enumerate(self.labels):
            label.setLabel(lines[index] if index < len(lines) else '')


class BufferOverlay:
    CONTROL_ID = 100

    def __init__(self):
        self.window = None
        self.label = None
        self._last_failure = ''
        self._renderer = ''
        self._last_mode = None

    def _failure(self, operation, exc):
        message = '{}: {}: {}'.format(operation, type(exc).__name__, exc)
        if message != self._last_failure:
            if xbmc is not None:
                xbmc.log('Appi buffered overlay {} failed: {}: {}'.format(
                    operation, type(exc).__name__, exc),
                    getattr(xbmc, 'LOGWARNING', 2))
            self._last_failure = message

    def _transition(self, mode, enabled, reason='update'):
        if mode == self._last_mode:
            return
        if xbmc is not None:
            xbmc.log(
                'Appi buffered overlay transition: mode={} enabled={} renderer={} '
                'window_exists={} reason={}'.format(
                    mode, bool(enabled), self._renderer or 'none',
                    bool(self.window), reason,
                ),
                getattr(xbmc, 'LOGINFO', 1),
            )
        self._last_mode = mode

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
                        self._apply(self.pending_text)
                except Exception:
                    self.appi_label = None

            def _apply(self, value):
                if self.appi_label is None:
                    return
                setter = getattr(self.appi_label, 'setText', None)
                if setter is not None:
                    setter(value)
                else:
                    self.appi_label.setLabel(value)

            def set_text(self, value):
                self.pending_text = value
                self._apply(value)

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
            textbox_type = getattr(xbmcgui, 'ControlTextBox', None)
            if textbox_type is not None:
                control = textbox_type(40, 45, 1180, 180)
                window.addControl(control)

                class TextBoxAdapter:
                    def set_text(self, value):
                        control.setText(value)

                label = TextBoxAdapter()
            else:
                labels = []
                for row in range(4):
                    control = xbmcgui.ControlLabel(
                        40, 45 + row * 34, 1180, 32, '',
                        textColor='FFFFFFFF', shadowColor='FF000000')
                    window.addControl(control)
                    labels.append(control)
                label = _FallbackMultiline(labels)
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
            reason = 'disabled' if not debug else 'inactive'
            self._transition('disabled' if not debug else 'hidden', debug, reason)
            self.close(reason=reason)
            return
        self._transition('detailed', debug)
        if self.label is None and not self._create():
            return
        try:
            self.label.set_text(text)
            self._last_failure = ''
        except Exception as exc:
            self._failure('set_text', exc)
            self.close(reason='renderer-error')

    def close(self, reason='closed'):
        window = self.window
        had_window = window is not None
        self.label = None
        self.window = None
        previous_renderer = self._renderer
        self._renderer = ''
        if window is not None:
            try:
                window.close()
                self._last_failure = ''
            except Exception as exc:
                self._failure('close', exc)
        if had_window and xbmc is not None:
            xbmc.log(
                'Appi buffered overlay closed: renderer={} reason={}'.format(
                    previous_renderer or 'unknown', reason),
                getattr(xbmc, 'LOGINFO', 1),
            )
