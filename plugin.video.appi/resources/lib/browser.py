import threading
from urllib.parse import urlencode

import xbmc
import xbmcaddon
import xbmcgui

from . import metadata
from . import playback_history
from .catalog import item_ref, sort_movies, sort_shows


ADDON = xbmcaddon.Addon()
LIST_ID = 50
BACK_ID = 10
SORT_ID = 11
CLOSE_ID = 12
VIEWPORT_RADIUS = 12
POLL_SECONDS = 0.75
INITIAL_LIST_ITEMS = 200
LIST_ITEM_BATCH = 200
LOAD_AHEAD_ITEMS = 40

ACTION_PARENT_DIR = 9
ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92
ACTION_CONTEXT_MENU = 117


def _year_label(value, year):
    value = value or ''
    if not year:
        return value
    suffix = ' ({})'.format(year)
    return value if suffix in value else value + suffix


def _episode_label(item, data=None):
    if data and data.get('episode_title'):
        season = item.get('season')
        episode = item.get('episode')
        if season is not None and episode is not None:
            return 'S{:02d}E{:02d} - {}'.format(
                int(season), int(episode), data['episode_title']
            )
        return data['episode_title']
    return item.get('display_title') or item.get('show_title') or 'Episode'


def _entry_label(entry, data=None):
    if entry.get('label_override'):
        return entry['label_override']
    item = entry['item']
    kind = entry.get('kind')
    if kind == 'season':
        return 'Season {}'.format(item.get('season'))
    if kind == 'episode':
        base = _episode_label(item, data)
    elif kind == 'tvshow':
        base = item.get('group_title') or item.get('show_title') or 'TV Show'
    else:
        base = item.get('title') or item.get('display_title') or 'Movie'
    label = _year_label(base, item.get('year'))
    suffix = entry.get('label_suffix') or ''
    return label + suffix


def _payload(entry):
    if entry.get('kind') == 'season':
        return None
    media_type = entry.get('kind')
    return metadata.lookup_payload(entry['item'], media_type=media_type)


def _set_base_info(list_item, entry):
    item = entry['item']
    kind = entry.get('kind')
    try:
        tag = list_item.getVideoInfoTag()
    except Exception:
        return
    try:
        tag.setMediaType(kind if kind in {'movie', 'episode', 'season', 'tvshow'} else 'video')
    except Exception:
        pass
    try:
        tag.setTitle(_entry_label(entry))
    except Exception:
        pass
    if item.get('show_title'):
        try:
            tag.setTvShowTitle(item['show_title'])
        except Exception:
            pass
    if item.get('year'):
        try:
            tag.setYear(int(item['year']))
        except Exception:
            pass
    for name in ('season', 'episode'):
        if item.get(name) is None:
            continue
        setter = getattr(tag, 'set' + name.title(), None)
        if setter:
            try:
                setter(int(item[name]))
            except Exception:
                pass
    if item.get('tvg_id'):
        try:
            tag.setUniqueID(item['tvg_id'], 'imdb', True)
        except Exception:
            pass


def _apply_metadata(list_item, entry, data):
    if not data:
        return
    poster = data.get('poster') or ''
    if poster:
        try:
            list_item.setArt({'poster': poster, 'thumb': poster})
        except Exception:
            pass
    try:
        tag = list_item.getVideoInfoTag()
    except Exception:
        return
    if data.get('plot'):
        try:
            tag.setPlot(data['plot'])
        except Exception:
            pass
    if data.get('episode_title') and entry.get('kind') == 'episode':
        try:
            tag.setTitle(data['episode_title'])
            list_item.setLabel(_entry_label(entry, data))
        except Exception:
            pass
    rating = data.get('imdb_rating')
    if rating is not None:
        try:
            tag.setRating(float(rating), int(data.get('imdb_votes') or 0), 'imdb', True)
        except Exception:
            pass
    actors = []
    for order, person in enumerate(data.get('cast') or []):
        try:
            actors.append(xbmc.Actor(
                person.get('name') or '', person.get('role') or '', order,
                person.get('thumbnail') or '',
            ))
        except Exception:
            continue
    if actors:
        try:
            tag.setCast(actors)
        except Exception:
            pass
    directors = [name for name in (data.get('directors') or []) if name]
    if directors:
        try:
            tag.setDirectors(directors)
        except Exception:
            pass


def _plugin_url(base_url, action, **params):
    query = {'action': action}
    query.update({key: value for key, value in params.items() if value is not None})
    return '{}?{}'.format(base_url, urlencode(query))


class AppiBrowser(xbmcgui.WindowXML):
    def configure(self, entries, title, base_url):
        self.entries = list(entries)
        self.title = title
        self.base_url = base_url
        self.stack = []
        self.list_control = None
        self.list_items = []
        self._stop = threading.Event()
        self._worker = None
        self._last_position = -1
        self._applied = {}

    def onInit(self):
        self.list_control = self.getControl(LIST_ID)
        try:
            self.getControl(1).setLabel(self.title)
        except Exception:
            pass
        self._rebuild(0)
        self.setFocusId(LIST_ID)
        self._worker = threading.Thread(
            target=self._metadata_loop, name='AppiViewportMetadata', daemon=True
        )
        self._worker.start()

    def _make_list_item(self, entry):
        # WindowXML owns these items and updates them live, so offscreen must
        # remain False to enable Kodi's GUI locking for subsequent mutations.
        list_item = xbmcgui.ListItem(label=_entry_label(entry), offscreen=False)
        _set_base_info(list_item, entry)
        payload = _payload(entry)
        if payload:
            list_item.setProperty('Appi.MetadataKey', metadata.cache_key(payload))
        list_item.setProperty('Appi.Kind', entry.get('kind') or '')
        return list_item

    def _update_count(self):
        try:
            self.getControl(2).setLabel(
                'Loaded {:,} of {:,}'.format(len(self.list_items), len(self.entries))
            )
        except Exception:
            pass

    def _append_until(self, target):
        if self.list_control is None:
            return
        start = len(self.list_items)
        end = min(len(self.entries), max(start, int(target)))
        if end <= start:
            return
        new_items = [self._make_list_item(entry) for entry in self.entries[start:end]]
        self.list_items.extend(new_items)
        self.list_control.addItems(new_items)
        self._update_count()

    def _load_ahead(self, position):
        loaded = len(self.list_items)
        if loaded >= len(self.entries):
            return
        if int(position or 0) >= loaded - LOAD_AHEAD_ITEMS:
            self._append_until(loaded + LIST_ITEM_BATCH)

    def _rebuild(self, selected=0):
        if self.list_control is None:
            return
        self.list_control.reset()
        self.list_items = []
        if self.entries:
            target = max(INITIAL_LIST_ITEMS, int(selected) + VIEWPORT_RADIUS + 1)
            self._append_until(target)
            self.list_control.selectItem(max(0, min(int(selected), len(self.list_items) - 1)))
        else:
            self._update_count()
        self._last_position = -1
        self._applied = {}
        self._queue_viewport(self.list_control.getSelectedPosition())

    def _viewport_indexes(self, position):
        if not self.entries:
            return []
        position = max(0, int(position if position is not None else 0))
        start = max(0, position - VIEWPORT_RADIUS)
        end = min(len(self.list_items), position + VIEWPORT_RADIUS + 1)
        return list(range(start, end))

    def _queue_viewport(self, position):
        payloads = [
            _payload(self.entries[index])
            for index in self._viewport_indexes(position)
        ]
        metadata.queue_many([value for value in payloads if value], priority=100)

    def _refresh_viewport(self, position):
        indexes = self._viewport_indexes(position)
        payload_pairs = [
            (index, _payload(self.entries[index])) for index in indexes
        ]
        cached = metadata.get_many([
            payload for _, payload in payload_pairs if payload
        ])
        for index, payload in payload_pairs:
            if not payload:
                continue
            key = metadata.cache_key(payload)
            data = cached.get(key)
            if data is None or self._applied.get(key) == data:
                continue
            try:
                _apply_metadata(self.list_items[index], self.entries[index], data)
                self._applied[key] = data
            except (IndexError, RuntimeError):
                return

    def _metadata_loop(self):
        while not self._stop.wait(POLL_SECONDS):
            if self.list_control is None:
                continue
            try:
                position = self.list_control.getSelectedPosition()
                self._load_ahead(position)
                if position != self._last_position:
                    self._last_position = position
                    self._queue_viewport(position)
                self._refresh_viewport(position)
            except Exception as exc:
                if not self._stop.is_set():
                    xbmc.log('Appi live metadata update failed: {}'.format(exc), xbmc.LOGWARNING)

    def _selected(self):
        if not self.list_control:
            return None, -1
        position = self.list_control.getSelectedPosition()
        if position < 0 or position >= len(self.entries):
            return None, -1
        return self.entries[position], position

    def _push(self, entries, title):
        position = self.list_control.getSelectedPosition() if self.list_control else 0
        self.stack.append((self.entries, self.title, position))
        self.entries = list(entries)
        self.title = title
        try:
            self.getControl(1).setLabel(title)
        except Exception:
            pass
        self._rebuild(0)

    def _back(self):
        if not self.stack:
            self.close()
            return
        self.entries, self.title, position = self.stack.pop()
        try:
            self.getControl(1).setLabel(self.title)
        except Exception:
            pass
        self._rebuild(position)

    def _open_show(self, entry):
        from . import app
        show = entry['item']
        entries = []
        if entry.get('recent'):
            recent = next((
                value for value in playback_history.recent_shows(limit=100)
                if value.get('show_key') == show.get('show_key')
            ), None)
            episodes = sorted(app._load_show_episodes(show.get('show_key') or ''), key=lambda item: (
                item.get('season') if item.get('season') is not None else 999999,
                item.get('episode') if item.get('episode') is not None else 999999,
                (item.get('display_title') or '').casefold(),
            ))
            if recent:
                recent_index = next((
                    index for index, item in enumerate(episodes)
                    if item_ref(item) == recent.get('ref')
                ), None)
                continuation = None
                resume = False
                if recent_index is not None:
                    if recent.get('completed') and recent_index + 1 < len(episodes):
                        continuation = episodes[recent_index + 1]
                    else:
                        continuation = episodes[recent_index]
                        resume = playback_history.resume_point(
                            'tv', item_ref(continuation)
                        ) is not None
                if continuation:
                    season = int(continuation.get('season') or 0)
                    episode = int(continuation.get('episode') or 0)
                    entries.append({
                        'scope': 'tv', 'kind': 'episode', 'catalog': 'tv',
                        'show_key': show.get('show_key') or '', 'item': continuation,
                        'recent': resume,
                        'label_override': '{}: S{:02d}E{:02d} - {}'.format(
                            'Resume' if resume else 'Continue', season, episode,
                            continuation.get('display_title') or 'Episode',
                        ),
                    })
        for season in show.get('seasons') or []:
            entries.append({
                'scope': 'tv', 'kind': 'season', 'show_key': show['show_key'],
                'item': {
                    'season': int(season), 'show_title': show.get('show_title') or '',
                    'year': show.get('year'), 'tvg_id': show.get('tvg_id') or '',
                },
            })
        self._push(entries, _year_label(
            show.get('show_title') or show.get('group_title') or 'TV Show', show.get('year')
        ))

    def _open_season(self, entry):
        from . import app
        season = entry['item'].get('season')
        key = entry.get('show_key') or ''
        episodes = [
            item for item in app._load_show_episodes(key)
            if item.get('season') == season
        ]
        episodes.sort(key=lambda item: (
            item.get('episode') if item.get('episode') is not None else 999999,
            (item.get('display_title') or '').casefold(),
        ))
        entries = [
            {'scope': 'tv', 'kind': 'episode', 'catalog': 'tv', 'show_key': key, 'item': item}
            for item in episodes
        ]
        title = '{} - Season {}'.format(
            entry['item'].get('show_title') or 'TV Show', season
        )
        self._push(entries, title)

    def _play(self, entry, resume=False):
        item = entry['item']
        catalog = 'movies' if entry.get('kind') == 'movie' else 'tv'
        resume = bool(resume or entry.get('recent'))
        url = _plugin_url(
            self.base_url, 'play_ref', catalog=catalog, ref=item_ref(item),
            show_key=entry.get('show_key'), resume='1' if resume else None,
        )
        xbmc.executebuiltin('PlayMedia({})'.format(url))

    def _activate(self):
        entry, _ = self._selected()
        if not entry:
            return
        kind = entry.get('kind')
        if kind == 'tvshow':
            self._open_show(entry)
        elif kind == 'season':
            self._open_season(entry)
        else:
            self._play(entry)

    def _sort(self):
        if not self.entries or self.entries[0].get('kind') in {'season', 'episode'}:
            xbmcgui.Dialog().notification('Appi', 'This list has a fixed episode order')
            return
        labels = [
            'Title A-Z', 'Title Z-A', 'Year - newest first',
            'Year - oldest first', 'Recently added', 'Oldest provider entry first',
        ]
        choice = xbmcgui.Dialog().select('Sort order', labels)
        if choice < 0:
            return
        current, _ = self._selected()
        current_identity = id(current) if current else None
        if choice in {4, 5}:
            ordered_items = sorted(
                [entry['item'] for entry in self.entries],
                key=lambda item: int(item.get('source_index') or 0),
                reverse=(choice == 5),
            )
        elif all(entry.get('kind') == 'movie' for entry in self.entries):
            ordered_items = sort_movies([entry['item'] for entry in self.entries], choice)
        elif all(entry.get('kind') == 'tvshow' for entry in self.entries):
            ordered_items = sort_shows([entry['item'] for entry in self.entries], choice)
        else:
            items = [entry['item'] for entry in self.entries]
            title_key = lambda item: (
                item.get('title') or item.get('show_title') or item.get('display_title') or ''
            ).casefold()
            if choice == 1:
                ordered_items = sorted(items, key=title_key, reverse=True)
            elif choice == 2:
                ordered_items = sorted(
                    items, key=lambda item: (-(item.get('year') or 0), title_key(item))
                )
            elif choice == 3:
                ordered_items = sorted(
                    items, key=lambda item: ((item.get('year') or 9999), title_key(item))
                )
            else:
                ordered_items = sorted(items, key=title_key)
        by_item = {id(entry['item']): entry for entry in self.entries}
        self.entries = [by_item[id(item)] for item in ordered_items]
        selected = next(
            (index for index, entry in enumerate(self.entries) if id(entry) == current_identity), 0
        )
        self._rebuild(selected)

    def _remove_recent(self, entry, position):
        kind = entry.get('kind')
        if kind == 'movie':
            playback_history.remove('movies', item_ref(entry['item']))
        elif kind == 'tvshow':
            playback_history.remove_show(entry.get('show_key') or entry['item'].get('show_key') or '')
        elif kind == 'episode':
            playback_history.remove('tv', item_ref(entry['item']))
        else:
            return
        self.entries.pop(position)
        self._rebuild(min(position, max(0, len(self.entries) - 1)))
        xbmcgui.Dialog().notification('Appi', 'Removed from Recently Played')

    def _context(self):
        entry, position = self._selected()
        if not entry:
            return
        kind = entry.get('kind')
        if kind in {'season'}:
            return
        choices = []
        actions = []
        if kind in {'movie', 'episode'}:
            choices.append('Play')
            actions.append(lambda: self._play(entry))
            choices.append('Download for offline viewing')
            actions.append(lambda: self._download(entry))
            choices.append('Playback options...')
            actions.append(lambda: self._playback_options(entry))
        choices.append('Fetch / refresh metadata')
        actions.append(lambda: self._refresh_metadata(entry))
        if entry.get('recent'):
            choices.append('Remove from Recently Played')
            actions.append(lambda: self._remove_recent(entry, position))
        choice = xbmcgui.Dialog().select(_entry_label(entry), choices)
        if 0 <= choice < len(actions):
            actions[choice]()

    def _download(self, entry):
        from . import downloads
        if downloads.queue_item(
                'movies' if entry.get('kind') == 'movie' else 'tv',
                entry['item'], entry.get('show_key') or ''):
            xbmcgui.Dialog().notification('Appi', 'Download queued')
        else:
            xbmcgui.Dialog().notification(
                'Appi', 'Download could not be queued', xbmcgui.NOTIFICATION_ERROR
            )

    def _playback_options(self, entry):
        item = entry['item']
        target = 'movie' if entry.get('kind') == 'movie' else 'episode'
        url = _plugin_url(
            self.base_url, 'configure_playback', target=target,
            catalog='movies' if target == 'movie' else 'tv', ref=item_ref(item),
            show_key=entry.get('show_key'),
        )
        xbmc.executebuiltin('RunPlugin({})'.format(url))

    def _refresh_metadata(self, entry):
        payload = _payload(entry)
        if payload and metadata.queue(payload, force=True, priority=200):
            self._applied.pop(metadata.cache_key(payload), None)
            xbmcgui.Dialog().notification('Appi', 'Metadata refresh queued')

    def onClick(self, control_id):
        if control_id == LIST_ID:
            self._activate()
        elif control_id == BACK_ID:
            self._back()
        elif control_id == SORT_ID:
            self._sort()
        elif control_id == CLOSE_ID:
            self.close()

    def onAction(self, action):
        action_id = action.getId()
        if action_id in {ACTION_PARENT_DIR, ACTION_PREVIOUS_MENU, ACTION_NAV_BACK}:
            self._back()
        elif action_id == ACTION_CONTEXT_MENU:
            self._context()
        elif self.list_control is not None:
            # Grow the list before the focused row reaches its current end. The
            # user gets continuous scrolling without constructing 20,000 Kodi
            # ListItems when the window first opens.
            self._load_ahead(self.list_control.getSelectedPosition())

    def close(self):
        self._stop.set()
        super().close()


def movie_entries(items, recent=False, label_suffix=''):
    return [
        {
            'scope': 'movies', 'kind': 'movie', 'catalog': 'movies',
            'item': item, 'recent': bool(recent), 'label_suffix': label_suffix,
        }
        for item in items
    ]


def show_entries(items, recent=False, label_suffix=''):
    return [
        {
            'scope': 'tv', 'kind': 'tvshow', 'catalog': 'tv',
            'show_key': item.get('show_key') or '', 'item': item,
            'recent': bool(recent), 'label_suffix': label_suffix,
        }
        for item in items
    ]


def episode_entries(items, show_key='', recent=False):
    return [
        {
            'scope': 'tv', 'kind': 'episode', 'catalog': 'tv',
            'show_key': show_key or '', 'item': item, 'recent': bool(recent),
        }
        for item in items
    ]


def mixed_entries(items):
    result = []
    for scope, item in items:
        if scope == 'movies':
            result.extend(movie_entries([item], label_suffix=' [Movie]'))
        else:
            result.extend(show_entries([item], label_suffix=' [TV Show]'))
    return result


def open_browser(entries, title, base_url):
    if not entries:
        xbmcgui.Dialog().notification('Appi', 'No items found')
        return
    window = AppiBrowser(
        'AppiBrowser.xml', ADDON.getAddonInfo('path'), 'Default', '1080i', False
    )
    window.configure(entries, title, base_url)
    window.doModal()
    del window
