#!/usr/bin/env python3
"""Build Kodi packages, repository metadata, and GitHub Pages files."""

import hashlib
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
import zipfile


ROOT = Path(__file__).resolve().parents[1]
ADDON_DIRS = [ROOT / 'plugin.video.appi', ROOT / 'repository.appi']
FALLBACK_PLUGIN_VERSIONS = {
    '0.7.0': 'previous release',
    '0.6.3': 'known-good fallback',
}


def addon_identity(directory):
    root = ET.parse(directory / 'addon.xml').getroot()
    addon_id = root.attrib['id']
    version = root.attrib['version']
    if directory.name != addon_id:
        raise RuntimeError('Directory {} does not match add-on id {}'.format(directory.name, addon_id))
    return addon_id, version


def excluded(path):
    return (
        '__pycache__' in path.parts
        or path.name == '.DS_Store'
        or path.suffix in {'.pyc', '.pyo', '.zip'}
        or path.name.endswith('.zip.sha256')
    )


def retained_names(addon_id, current_zip_name):
    names = {current_zip_name, current_zip_name + '.sha256'}
    if addon_id == 'plugin.video.appi':
        for version in FALLBACK_PLUGIN_VERSIONS:
            name = '{}-{}.zip'.format(addon_id, version)
            names.update({name, name + '.sha256'})
    return names


def clean_old_package_files(directory, addon_id, current_zip_name):
    keep = retained_names(addon_id, current_zip_name)
    for path in directory.glob('{}-*.zip*'.format(addon_id)):
        if path.name not in keep:
            path.unlink()


def build_zip(directory, addon_id, version):
    output = directory / '{}-{}.zip'.format(addon_id, version)
    clean_old_package_files(directory, addon_id, output.name)
    output.unlink(missing_ok=True)
    sidecar = output.with_name(output.name + '.sha256')
    sidecar.unlink(missing_ok=True)

    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        directories = {Path(addon_id)}
        files = []
        for path in sorted(directory.rglob('*')):
            if excluded(path):
                continue
            relative = path.relative_to(directory)
            arcpath = Path(addon_id) / relative
            if path.is_dir():
                directories.add(arcpath)
            else:
                files.append((path, arcpath))
                parent = arcpath.parent
                while parent != Path('.'):
                    directories.add(parent)
                    if parent == Path(addon_id):
                        break
                    parent = parent.parent

        for directory_path in sorted(directories, key=lambda p: (len(p.parts), p.as_posix())):
            name = directory_path.as_posix().rstrip('/') + '/'
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = ((0o040755 & 0xFFFF) << 16) | 0x10
            archive.writestr(info, b'')

        for path, arcpath in files:
            info = zipfile.ZipInfo(arcpath.as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100644 & 0xFFFF) << 16
            archive.writestr(
                info, path.read_bytes(),
                compress_type=zipfile.ZIP_DEFLATED, compresslevel=9,
            )

    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    sidecar.write_text(digest + '\n', encoding='ascii')
    with zipfile.ZipFile(output, 'r') as archive:
        top_levels = {name.split('/', 1)[0] for name in archive.namelist() if name}
        if top_levels != {addon_id}:
            raise RuntimeError('Invalid package layout for {}: {}'.format(addon_id, sorted(top_levels)))
        bad = archive.testzip()
        if bad:
            raise RuntimeError('Corrupt ZIP member in {}: {}'.format(output.name, bad))
    return output


def build_addons_xml():
    addons_root = ET.Element('addons')
    for directory in ADDON_DIRS:
        addons_root.append(ET.parse(directory / 'addon.xml').getroot())
    ET.indent(addons_root, space='  ')
    body = ET.tostring(addons_root, encoding='utf-8', xml_declaration=True)
    if not body.endswith(b'\n'):
        body += b'\n'
    (ROOT / 'addons.xml').write_bytes(body)
    (ROOT / 'addons.xml.sha256').write_text(
        hashlib.sha256(body).hexdigest() + '\n', encoding='ascii'
    )


def build_pages_entry(plugin_zip):
    current = ROOT / plugin_zip.name
    shutil.copy2(plugin_zip, current)
    keep = {current.name}
    fallback_paths = []
    for version in sorted(FALLBACK_PLUGIN_VERSIONS, reverse=True):
        name = 'plugin.video.appi-{}.zip'.format(version)
        fallback = ROOT / name
        nested = ROOT / 'plugin.video.appi' / name
        if not fallback.exists() and nested.exists():
            shutil.copy2(nested, fallback)
        if fallback.exists():
            keep.add(name)
            fallback_paths.append((fallback, FALLBACK_PLUGIN_VERSIONS[version]))
    for path in ROOT.glob('plugin.video.appi-*.zip'):
        if path.name not in keep:
            path.unlink()
    for path in ROOT.glob('repository.appi-*.zip'):
        path.unlink()

    links = ['  <p><a href="{0}">{0}</a> (current)</p>'.format(current.name)]
    links.extend(
        '  <p><a href="{0}">{0}</a> ({1})</p>'.format(path.name, label)
        for path, label in fallback_paths
    )
    html = '''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Appi Kodi Add-on</title>
</head>
<body>
  <h1>Appi Kodi Add-on</h1>
{links}
</body>
</html>
'''.format(links='\n'.join(links))
    (ROOT / 'index.html').write_text(html, encoding='utf-8')


def main():
    built = {}
    for directory in ADDON_DIRS:
        addon_id, version = addon_identity(directory)
        built[addon_id] = build_zip(directory, addon_id, version)
    build_addons_xml()
    build_pages_entry(built['plugin.video.appi'])
    for addon_id, path in built.items():
        print('{} -> {}'.format(addon_id, path.relative_to(ROOT)))


if __name__ == '__main__':
    main()
