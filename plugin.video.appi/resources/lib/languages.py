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

_ALIASES.update({'el': 'el', 'gre': 'el', 'ell': 'el', 'greek': 'el', 'he': 'he', 'heb': 'he', 'hebrew': 'he', 'hi': 'hi', 'hin': 'hi', 'hindi': 'hi', 'fa': 'fa', 'per': 'fa', 'fas': 'fa', 'persian': 'fa', 'ro': 'ro', 'rum': 'ro', 'ron': 'ro', 'romanian': 'ro', 'ru': 'ru', 'rus': 'ru', 'russian': 'ru', 'ta': 'ta', 'tam': 'ta', 'tamil': 'ta', 'te': 'te', 'tel': 'te', 'telugu': 'te', 'th': 'th', 'tha': 'th', 'thai': 'th', 'tr': 'tr', 'tur': 'tr', 'turkish': 'tr', 'uk': 'uk', 'ukr': 'uk', 'ukrainian': 'uk', 'ur': 'ur', 'urd': 'ur', 'urdu': 'ur', 'vi': 'vi', 'vie': 'vi', 'vietnamese': 'vi'})


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


COMMON_CODES = ('', 'en', 'ar', 'zh', 'da', 'nl', 'fi', 'fr', 'de', 'el', 'he', 'hi', 'it', 'ja', 'ko', 'no', 'fa', 'pl', 'pt', 'ro', 'ru', 'es', 'sv', 'ta', 'te', 'th', 'tr', 'uk', 'ur', 'vi')


def migrate_preferences(addon):
    if addon.getSetting('language_choices_migrated') == 'true':
        return
    for kind in ('audio', 'subtitle'):
        key = 'preferred_' + kind + '_language'
        current = addon.getSetting(key + '_choice')
        value = normalize(current or addon.getSetting(key))
        addon.setSetting(key + '_choice', value if value in COMMON_CODES else '')
    addon.setSetting('language_choices_migrated', 'true')


def preference(addon, kind):
    key = 'preferred_' + kind + '_language'
    if addon.getSetting('language_choices_migrated') == 'true':
        return normalize(addon.getSetting(key + '_choice'))
    return normalize(addon.getSetting(key + '_choice') or addon.getSetting(key))
