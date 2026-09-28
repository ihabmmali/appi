import json
import time
from urllib.parse import urlencode

import xbmc
import xbmcaddon

from . import buffered_hls
from .buffered_ui import BufferOverlay
from . import diagnostics
from . import languages
from . import playback_history
from . import metadata
from . import refresh_state
from . import subtitle_store

ADDON = xbmcaddon.Addon()


def _enabled(setting, default=True):
    value = ADDON.getSetting(setting)
    return default if value == '' else value.lower() == 'true'


def _integer(setting, default):
    try:
        value = ADDON.getSetting(setting)
        return int(value) if value != '' else int(default)
    except (TypeError, ValueError):
        return int(default)


class AppiPlayer(xbmc.Player):
    def __init__(self, buffered_manager=None):
        super().__init__()
        self._search_opened_key = None
        self._buffered_manager = buffered_manager
        self._buffered_token = None
        self._language_deadline = 0.0
        self._audio_language_done = True
        self._subtitle_language_done = True
        self._audio_stream_snapshot = ()
        self._audio_stream_snapshot_at = 0.0

    def _subtitle_session(self):
        return subtitle_store.load_session() or {}

    def _apply_session_subtitles(self):
        session = self._subtitle_session()
        if not session:
            return False
        mode = session.get('subtitle_mode') or 'global'
        key = session.get('key')

        if mode == 'search':
            if key and key != self._search_opened_key:
                self._search_opened_key = key
                try:
                    xbmc.executebuiltin('ActivateWindow(subtitlesearch)')
                except Exception as exc:
                    xbmc.log('Appi could not open subtitle search: {}'.format(exc), xbmc.LOGWARNING)
            return True

        if mode == 'off':
            return True
        if mode == 'global' and not _enabled('auto_saved_subtitles', True):
            return False

        path = subtitle_store.last_saved_subtitle(session.get('catalog', ''), session.get('ref', ''))
        if path:
            try:
                self.setSubtitles(path)
                self.showSubtitles(True)
                return True
            except Exception as exc:
                xbmc.log('Appi could not restore saved subtitles: {}'.format(exc), xbmc.LOGWARNING)
        return False

    def _begin_preferred_languages(self):
        self._language_deadline = time.monotonic() + 12.0
        self._audio_language_done = False
        self._subtitle_language_done = False
        self._audio_stream_snapshot = ()
        self._audio_stream_snapshot_at = 0.0

    def _current_audio_stream(self):
        """Best-effort current Kodi audio state without mutating playback."""
        execute = getattr(xbmc, 'executeJSONRPC', None)
        if not execute:
            return {}
        try:
            active = json.loads(execute(json.dumps({
                'jsonrpc': '2.0',
                'id': 1,
                'method': 'Player.GetActivePlayers',
            }))).get('result') or []
            player = next((value for value in active if value.get('type') == 'video'), None)
            if not player:
                return {}
            result = json.loads(execute(json.dumps({
                'jsonrpc': '2.0',
                'id': 1,
                'method': 'Player.GetProperties',
                'params': {
                    'playerid': player.get('playerid'),
                    'properties': ['currentaudiostream'],
                },
            }))).get('result') or {}
            current = result.get('currentaudiostream') or {}
            return current if isinstance(current, dict) else {}
        except Exception as exc:
            xbmc.log(
                'Appi audio-language current-stream query failed: {}'.format(exc),
                xbmc.LOGWARNING,
            )
            return {}

    def _apply_preferred_languages(self):
        audio = languages.preference(ADDON, 'audio')
        if not self._audio_language_done:
            if not audio:
                # No preference is deliberately inert: do not touch Kodi/ISA's
                # working default audio stream.
                self._audio_language_done = True
                self._audio_stream_snapshot = ()
            else:
                try:
                    streams = tuple(self.getAvailableAudioStreams() or [])
                    now = time.monotonic()
                    if streams:
                        if streams != self._audio_stream_snapshot:
                            # InputStream Adaptive can expose a provisional
                            # stream list during AV start. Never act on an index
                            # until the exact list has remained stable across a
                            # service poll boundary.
                            self._audio_stream_snapshot = streams
                            self._audio_stream_snapshot_at = now
                        elif now - self._audio_stream_snapshot_at >= 0.75:
                            index = languages.match_index(audio, streams)
                            current = self._current_audio_stream()
                            current_label = (
                                current.get('language')
                                or current.get('name')
                                or ''
                            )
                            current_index = current.get('index')
                            if index is None:
                                # A stable list with no match must leave the
                                # currently audible stream untouched.
                                self._audio_language_done = True
                                xbmc.log(
                                    'Appi audio preference has no match; '
                                    'leaving current stream unchanged',
                                    getattr(xbmc, 'LOGDEBUG', 0),
                                )
                            elif (
                                languages.normalize(current_label) == languages.normalize(audio)
                                or current_index == index
                            ):
                                # Avoid a redundant setAudioStream() call. This
                                # is especially important for ISA, where forcing
                                # the already-selected rendition during startup
                                # can disrupt decoder/rendition handoff.
                                self._audio_language_done = True
                                xbmc.log(
                                    'Appi audio preference already selected '
                                    '(index={}); no stream switch'.format(current_index),
                                    getattr(xbmc, 'LOGDEBUG', 0),
                                )
                            else:
                                # Re-read immediately before using the index so
                                # a changing ISA list can never turn a formerly
                                # valid match into a stale setAudioStream call.
                                confirmed = tuple(self.getAvailableAudioStreams() or [])
                                if confirmed != streams:
                                    self._audio_stream_snapshot = confirmed
                                    self._audio_stream_snapshot_at = now
                                elif 0 <= index < len(confirmed):
                                    xbmc.log(
                                        'Appi audio preference switching stable '
                                        'stream list: available={} current_index={} '
                                        'target_index={}'.format(
                                            list(confirmed), current_index, index
                                        ),
                                        getattr(xbmc, 'LOGDEBUG', 0),
                                    )
                                    self.setAudioStream(index)
                                    self._audio_language_done = True
                except Exception as exc:
                    self._audio_language_done = False
                    xbmc.log('Appi audio-language selection failed: {}'.format(exc), xbmc.LOGWARNING)

        session = self._subtitle_session()
        mode = session.get('subtitle_mode') or 'global'
        subtitle = languages.preference(ADDON, 'subtitle')
        if not self._subtitle_language_done:
            if not subtitle or mode != 'global':
                self._subtitle_language_done = True
            else:
                try:
                    streams = self.getAvailableSubtitleStreams() or []
                    if streams:
                        index = languages.match_index(subtitle, streams)
                        self._subtitle_language_done = True
                        if index is not None:
                            self.setSubtitleStream(index)
                            self.showSubtitles(True)
                except Exception as exc:
                    self._subtitle_language_done = False
                    xbmc.log('Appi subtitle-language selection failed: {}'.format(exc), xbmc.LOGWARNING)

    def apply_pending_languages(self):
        if self._audio_language_done and self._subtitle_language_done:
            return
        if time.monotonic() > self._language_deadline:
            self._audio_language_done = True
            self._subtitle_language_done = True
            return
        self._apply_preferred_languages()

    def onAVStarted(self):
        if self._buffered_manager:
            self._buffered_token = self._buffered_manager.playback_started(self.getPlayingFile())
        self._begin_preferred_languages()
        self._apply_preferred_languages()
        diagnostics.player_started(self)
        if self._apply_session_subtitles():
            self._subtitle_language_done = True

    def onAVChange(self):
        self.apply_pending_languages()
        if _enabled('persist_subtitles', True):
            try:
                subtitle_store.capture_temp_changes()
            except Exception as exc:
                xbmc.log('Appi subtitle capture failed: {}'.format(exc), xbmc.LOGWARNING)

    def _finish(self, result='stopped'):
        if _enabled('persist_subtitles', True):
            try:
                subtitle_store.capture_temp_changes(finalize=True)
            except Exception:
                pass
        subtitle_store.clear_session()
        if self._buffered_manager:
            self._buffered_manager.playback_finished(self._buffered_token, result)
            self._buffered_token = None
            self._buffered_manager.flush_diagnostics(diagnostics.event)
        diagnostics.finish(result)
        session = playback_history.finish_session()
        self._search_opened_key = None
        self._language_deadline = 0.0
        self._audio_language_done = True
        self._subtitle_language_done = True
        self._audio_stream_snapshot = ()
        self._audio_stream_snapshot_at = 0.0
        return session

    def onPlayBackStopped(self):
        self._finish('stopped')

    def onPlayBackEnded(self):
        session = self._finish('ended') or {}
        if session.get('catalog') != 'tv' or not session.get('show_key'):
            return
        if not _enabled('auto_next_episode', False):
            return
        query = urlencode({
            'action': 'play_next',
            'show_key': session['show_key'],
            'after_ref': session.get('ref') or '',
            'completed': '1',
        })
        xbmc.executebuiltin(
            'PlayMedia(plugin://plugin.video.appi/?{})'.format(query)
        )

    def onPlayBackError(self):
        self._finish('error')


def run():
    monitor = xbmc.Monitor()
    buffered_manager = buffered_hls.BufferedHlsManager()
    player = AppiPlayer(buffered_manager)
    overlay = BufferOverlay()
    languages.migrate_preferences(ADDON)
    next_metadata_poll = 0.0
    next_diagnostic_sample = 0.0
    next_auto_refresh_check = 0.0
    startup_refresh_pending = _enabled('auto_refresh_on_startup', False)
    focused_value = ''
    focused_since = 0.0
    queued_focus = ''
    while not monitor.abortRequested():
        playing = player.isPlayingVideo()
        try:
            buffered_manager.poll(player_active=playing)
            buffered_manager.flush_diagnostics(diagnostics.event)
            session = buffered_manager.active
            status = session.status() if session else None
            if status and playing:
                status['recovering'] = status['recovering'] or xbmc.getCondVisibility('Player.Caching')
            overlay.update(status if session and session.ready else None,
                           _enabled('buffered_debug_overlay', False), playing)
            if session and playing:
                diagnostics.event('buffer_status', **{k: v for k, v in status.items()
                                  if k in {'cached_ahead_bytes', 'buffer_target_bytes',
                                           'high_water_bytes', 'low_water_bytes',
                                           'critical_water_bytes', 'buffered_seconds',
                                           'cached_segments_ahead', 'buffer_capacity_mb',
                                           'buffer_state', 'buffer_trend',
                                           'selected_bitrate_mbps', 'throughput_mbps',
                                           'throughput_limited', 'limitation_message',
                                           'epoch_id', 'epoch_reason',
                                           'epoch_target_seconds',
                                           'stale_jobs_cancelled_or_ignored'}})
        except Exception as exc:
            xbmc.log('Appi buffered HLS service failed: {}'.format(exc), xbmc.LOGWARNING)
        if playing:
            player.apply_pending_languages()
        if playing and _enabled('persist_subtitles', True):
            try:
                subtitle_store.capture_temp_changes()
            except Exception as exc:
                xbmc.log('Appi subtitle polling failed: {}'.format(exc), xbmc.LOGWARNING)
        now = time.monotonic()
        if playing and diagnostics.enabled() and now >= next_diagnostic_sample:
            try:
                diagnostics.sample(player)
            except Exception as exc:
                xbmc.log('Appi diagnostic sample failed: {}'.format(exc), xbmc.LOGWARNING)
            next_diagnostic_sample = now + 2.0

        if not playing:
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

        if not playing and _enabled('auto_refresh_enabled', False) and now >= next_auto_refresh_check:
            state = refresh_state.load()
            failures = max(0, int(state.get('failures') or 0))
            interval = max(1, _integer('auto_refresh_interval_hours', 6)) * 3600
            retry_delay = interval if failures == 0 else min(
                interval, 900 * (2 ** min(failures - 1, 4))
            )
            last_attempt = float(state.get('last_attempt') or 0)
            due = time.time() - last_attempt >= retry_delay
            if startup_refresh_pending or due:
                try:
                    xbmc.executebuiltin('RunPlugin(plugin://plugin.video.appi/?action=auto_refresh)')
                except Exception as exc:
                    xbmc.log('Appi automatic refresh launch failed: {}'.format(exc), xbmc.LOGWARNING)
                startup_refresh_pending = False
            next_auto_refresh_check = now + 60.0

        if now >= next_metadata_poll:
            try:
                metadata.process_one()
            except Exception as exc:
                xbmc.log('Appi metadata worker failed: {}'.format(exc), xbmc.LOGWARNING)
            next_metadata_poll = now + 2.0
        if monitor.waitForAbort(0.25 if buffered_manager.active else 1.0):
            break
    overlay.close()
    buffered_manager.shutdown(diagnostics.event)
