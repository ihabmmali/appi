def _dedupe(items):
    result = []
    seen = set()
    for item in items or []:
        url = item.get('media_url') if isinstance(item, dict) else None
        if not url or url in seen:
            continue
        seen.add(url)
        result.append(item)
    return result


def merge_leading(old_items, leading_items, min_overlap=8):
    old_items = _dedupe(old_items)
    leading_items = _dedupe(leading_items)
    if not old_items or not leading_items:
        return None, {'reason': 'missing-cache-or-leading-window'}

    old_urls = [item.get('media_url') for item in old_items]
    new_urls = [item.get('media_url') for item in leading_items]
    positions = {url: index for index, url in enumerate(old_urls)}

    for new_index, url in enumerate(new_urls):
        old_index = positions.get(url)
        if old_index is None:
            continue
        available = min(len(new_urls) - new_index, len(old_urls) - old_index)
        required = min(max(1, int(min_overlap)), available)
        if available >= 3:
            required = max(3, required)
        matched = 0
        while matched < available and new_urls[new_index + matched] == old_urls[old_index + matched]:
            matched += 1
        if matched < required:
            continue

        merged = _dedupe(leading_items[:new_index] + old_items[old_index:])
        return merged, {
            'reason': 'overlap',
            'added': new_index,
            'dropped_from_old_head': old_index,
            'overlap': matched,
            'old_count': len(old_items),
            'merged_count': len(merged),
        }

    return None, {
        'reason': 'no-overlap',
        'old_count': len(old_items),
        'leading_count': len(leading_items),
    }
