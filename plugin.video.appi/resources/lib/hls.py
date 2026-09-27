import re
from urllib.parse import urljoin

_ATTR_RE = re.compile(r'([A-Z0-9-]+)=(?:"([^"]*)"|([^,]*))', re.IGNORECASE)


def _attributes(value):
    result = {}
    for match in _ATTR_RE.finditer(value or ''):
        result[match.group(1).upper()] = (match.group(2) if match.group(2) is not None else match.group(3)).strip()
    return result


def _integer(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def parse_master(text, base_url):
    lines = [line.strip() for line in (text or '').splitlines()]
    variants = []
    pending = None
    for line in lines:
        if line.startswith('#EXT-X-STREAM-INF:'):
            pending = _attributes(line.split(':', 1)[1])
            continue
        if pending is None or not line or line.startswith('#'):
            continue
        bandwidth = _integer(pending.get('AVERAGE-BANDWIDTH') or pending.get('BANDWIDTH'))
        width = height = 0
        resolution = pending.get('RESOLUTION') or ''
        if 'x' in resolution.lower():
            try:
                width, height = [int(part) for part in resolution.lower().split('x', 1)]
            except (TypeError, ValueError):
                width = height = 0
        variants.append({
            'url': urljoin(base_url, line),
            'bandwidth': bandwidth,
            'width': width,
            'height': height,
            'name': pending.get('NAME') or pending.get('VIDEO') or '',
            'codecs': pending.get('CODECS') or '',
        })
        pending = None
    return variants


def variant_label(variant):
    parts = []
    if variant.get('height'):
        parts.append('{}p'.format(variant['height']))
    elif variant.get('width'):
        parts.append('{}px wide'.format(variant['width']))
    if variant.get('bandwidth'):
        parts.append('{:.1f} Mbit/s'.format(float(variant['bandwidth']) / 1000000.0))
    if variant.get('name'):
        parts.append(str(variant['name']))
    return ' · '.join(parts) or 'HLS rendition'
