try:
    import xbmc
except ImportError:  # pragma: no cover - exercised through Kodi/mocks
    xbmc = None

_ALIASES = {
    'en': 'en', 'eng': 'en', 'english': 'en',
    'fr': 'fr', 'fra': 'fr', 'fre': 'fr', 'french': 'fr',
    'es': 'es', 'spa': 'es', 'spanish': 'es',
    'de': 'de', 'deu': 'de', 'ger': 'de', 'german': 'de',
    'it': 'it', 'ita': 'it', 'italian': 'it',
    'pt': 'pt', 'por': 'pt', 'portuguese': 'pt',
    'ar': 'ar', 'ara': 'ar', 'arabic': 'ar',
    'nl': 'nl', 'nld': 'nl', 'dut': 'nl', 'dutch': 'nl',
    'sv': 'sv', 'swe': 'sv', 'swedish': 'sv',
    'no': 'no', 'nor': 'no', 'norwegian': 'no',
    'da': 'da', 'dan': 'da', 'danish': 'da',
    'fi': 'fi', 'fin': 'fi', 'finnish': 'fi',
    'pl': 'pl', 'pol': 'pl', 'polish': 'pl',
    'ja': 'ja', 'jpn': 'ja', 'japanese': 'ja',
    'ko': 'ko', 'kor': 'ko', 'korean': 'ko',
    'zh': 'zh', 'zho': 'zh', 'chi': 'zh', 'chinese': 'zh',
}


def normalize(value):
    value = (value or '').strip()
    if not value:
        return ''
    if xbmc is not None and hasattr(xbmc, 'convertLanguage'):
        try:
            converted = xbmc.convertLanguage(value, getattr(xbmc, 'ISO_639_1', 0))
            if converted:
                return converted.casefold().split('-', 1)[0]
        except Exception:
            pass
    lowered = value.casefold().replace('_', '-')
    primary = lowered.split('-', 1)[0].strip()
    if primary in _ALIASES:
        return _ALIASES[primary]
    if lowered in _ALIASES:
        return _ALIASES[lowered]
    for token in lowered.replace('/', ' ').replace('(', ' ').replace(')', ' ').replace('[', ' ').replace(']', ' ').split():
        token = token.strip(' ,.;:')
        if token in _ALIASES:
            return _ALIASES[token]
    return primary if len(primary) == 2 and primary.isalpha() else ''


def match_index(preferred, streams):
    target = normalize(preferred)
    if not target:
        return None
    for index, label in enumerate(streams or []):
        if normalize(label) == target:
            return index
    return None
