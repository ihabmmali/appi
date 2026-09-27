import hashlib
import re
from urllib.parse import urljoin, urlparse, urlunparse

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


def _split_kodi_url(value):
    core, marker, options = (value or '').partition('|')
    return core, options if marker else ''


def _join_kodi_options(base_options, child_options):
    if not base_options:
        return child_options
    if not child_options:
        return base_options
    return '{}&{}'.format(base_options.rstrip('&'), child_options.lstrip('&'))


def resolve_variant_url(base_url, variant_uri):
    """Resolve an HLS child URI without discarding provider auth material."""
    base_core, base_options = _split_kodi_url(base_url)
    child_core, child_options = _split_kodi_url(variant_uri)
    resolved = urljoin(base_core, child_core)

    base = urlparse(base_core)
    child = urlparse(child_core)
    parsed = urlparse(resolved)
    relative_child = not child.scheme and not child.netloc
    same_origin = (
        relative_child
        and (not parsed.hostname or parsed.hostname == base.hostname)
        and (not parsed.port or parsed.port == base.port)
    )
    # RFC URL resolution replaces the master's query for relative children.
    # Authenticated HLS providers commonly expect a master token/signature to
    # be inherited when the child does not specify its own query.
    if same_origin and base.query and not child.query:
        parsed = parsed._replace(query=base.query)
        resolved = urlunparse(parsed)

    options = _join_kodi_options(base_options, child_options)
    return '{}|{}'.format(resolved, options) if options else resolved


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

        peak_bandwidth = _integer(pending.get('BANDWIDTH'))
        average_bandwidth = _integer(pending.get('AVERAGE-BANDWIDTH'))
        width = height = 0
        resolution = pending.get('RESOLUTION') or ''
        if 'x' in resolution.lower():
            try:
                width, height = [int(part) for part in resolution.lower().split('x', 1)]
            except (TypeError, ValueError):
                width = height = 0

        resolved = resolve_variant_url(base_url, line)
        variants.append({
            'url': resolved,
            'uri': line,
            'bandwidth': average_bandwidth or peak_bandwidth,
            'average_bandwidth': average_bandwidth,
            'peak_bandwidth': peak_bandwidth,
            'width': width,
            'height': height,
            'name': pending.get('NAME') or pending.get('VIDEO') or '',
            'codecs': pending.get('CODECS') or '',
            'identity': hashlib.sha256(resolved.encode('utf-8', errors='replace')).hexdigest()[:16],
        })
        pending = None
    return variants


def variant_label(variant):
    parts = []
    if variant.get('height'):
        parts.append('{}p'.format(variant['height']))
    elif variant.get('width'):
        parts.append('{}px wide'.format(variant['width']))

    average = int(variant.get('average_bandwidth') or 0)
    peak = int(variant.get('peak_bandwidth') or 0)
    if average and peak and average != peak:
        parts.append(
            'avg {:.1f} / peak {:.1f} Mbit/s'.format(
                float(average) / 1000000.0, float(peak) / 1000000.0
            )
        )
    elif average or peak:
        parts.append('{:.1f} Mbit/s'.format(float(average or peak) / 1000000.0))

    if variant.get('codecs'):
        parts.append(str(variant['codecs']))
    if variant.get('name'):
        parts.append(str(variant['name']))
    return ' · '.join(parts) or 'HLS rendition'
