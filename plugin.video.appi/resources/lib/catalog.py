import hashlib
import math


def show_key(item):
    return '{}\x1f{}\x1f{}'.format(item.get('tvg_id') or '', item.get('show_title') or '', item.get('year') or '')


def show_cache_name(key):
    return 'tv_show_{}'.format(hashlib.sha1(key.encode('utf-8')).hexdigest())


def item_ref(item):
    kind = item.get('kind') or ''
    tvg_id = item.get('tvg_id') or ''
    if kind == 'movie' and tvg_id:
        return 'm:{}'.format(tvg_id)
    if kind == 'episode' and tvg_id:
        return 'e:{}:{}:{}'.format(tvg_id, item.get('season'), item.get('episode'))
    return 'u:{}'.format(hashlib.sha1((item.get('media_url') or '').encode('utf-8')).hexdigest())


def build_tv_groups(episodes):
    groups = {}
    for episode in episodes:
        groups.setdefault(show_key(episode), []).append(episode)
    summaries = []
    for source_index, (key, items) in enumerate(groups.items()):
        first = items[0]
        seasons = sorted({item.get('season') for item in items if item.get('season') is not None})
        summaries.append({
            'show_key': key,
            'cache_name': show_cache_name(key),
            'show_title': first.get('show_title') or first.get('group_title') or 'TV Show',
            'group_title': first.get('group_title') or first.get('show_title') or 'TV Show',
            'year': first.get('year'),
            'tvg_id': first.get('tvg_id') or '',
            'seasons': seasons,
            'episode_count': len(items),
            # Preserve first appearance in the provider feed for the
            # "Recently added (M3U order)" browsing mode.
            'source_index': source_index,
        })
    return summaries, groups


def sort_movies(items, mode=0):
    items = list(items)
    title_key = lambda item: (item.get('title') or item.get('display_title') or '').casefold()
    if mode == 1:
        return sorted(items, key=title_key, reverse=True)
    if mode == 2:
        return sorted(items, key=lambda item: (-(item.get('year') or 0), title_key(item)))
    if mode == 3:
        return sorted(items, key=lambda item: ((item.get('year') or 9999), title_key(item)))
    if mode == 4:
        # parse_m3u() and dedupe() preserve source order.
        return items
    if mode == 5:
        return list(reversed(items))
    return sorted(items, key=title_key)


def sort_shows(items, mode=0):
    items = list(items)
    title_key = lambda item: (item.get('show_title') or item.get('group_title') or '').casefold()
    if mode == 1:
        return sorted(items, key=title_key, reverse=True)
    if mode == 2:
        return sorted(items, key=lambda item: (-(item.get('year') or 0), title_key(item)))
    if mode == 3:
        return sorted(items, key=lambda item: ((item.get('year') or 9999), title_key(item)))
    if mode == 4:
        # The indexed show list is written in first-appearance order from the
        # provider feed, including indexes created by 0.5.x.
        return items
    if mode == 5:
        return list(reversed(items))
    return sorted(items, key=title_key)


def paginate(items, page=1, page_size=100):
    items = list(items)
    try:
        page = int(page)
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = int(page_size)
    except (TypeError, ValueError):
        page_size = 100
    page_size = min(500, max(25, page_size))
    total = len(items)
    pages = max(1, int(math.ceil(float(total) / float(page_size))))
    page = min(pages, max(1, page))
    start = (page - 1) * page_size
    return items[start:start + page_size], page, pages, total
