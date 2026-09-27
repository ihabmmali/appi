from . import cache

CACHE_NAME = 'search_history'
LIMIT = 20
MAX_TERM_LENGTH = 200


def _clean_term(value):
    if not isinstance(value, str):
        return ''
    return value.strip()[:MAX_TERM_LENGTH]


def entries():
    payload = cache.load_object(CACHE_NAME) or {}
    raw = payload.get('items') if isinstance(payload, dict) else []
    if not isinstance(raw, list):
        return []
    result = []
    seen = set()
    for value in raw:
        term = _clean_term(value)
        folded = term.casefold()
        if not term or folded in seen:
            continue
        seen.add(folded)
        result.append(term)
        if len(result) >= LIMIT:
            break
    return result


def add(term):
    term = _clean_term(term)
    if not term:
        return entries()
    folded = term.casefold()
    values = [value for value in entries() if value.casefold() != folded]
    values.insert(0, term)
    values = values[:LIMIT]
    cache.save_object(CACHE_NAME, {'items': values})
    return values


def delete(term):
    folded = _clean_term(term).casefold()
    values = [value for value in entries() if value.casefold() != folded]
    cache.save_object(CACHE_NAME, {'items': values})
    return values


def clear():
    cache.save_object(CACHE_NAME, {'items': []})
