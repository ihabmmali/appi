#!/usr/bin/env python3
"""Build Kodi packages and repository metadata from the source tree."""

import hashlib
import os
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ADDON_DIRS = [ROOT / 'plugin.video.appi', ROOT / 'repository.appi']


def addon_identity(directory):
    tree = ET.parse(directory / 'addon.xml')
    root = tree.getroot()
    addon_id = root.attrib['id']
    version = root.attrib['version']
    if directory.name != addon_id:
        raise RuntimeError('Directory {} does not match add-on id {}'.format(directory.name, addon_id))
    return addon_id, version


def excluded(path):
    parts = path.parts
    return (
        '__pycache__' in parts
        or path.name == '.DS_Store'
        or path.suffix in {'.pyc', '.pyo', '.zip'}
    )


def clean_old_package_files(directory, addon_id, current_zip_name):
    for path in directory.glob('{}-*.zip*'.format(addon_id)):
        if path.name not in {current_zip_name, current_zip_name + '.sha256'}:
            path.unlink()


def build_zip(directory, addon_id, version):
    output = directory / '{}-{}.zip'.format(addon_id, version)
    clean_old_package_files(directory, addon_id, output.name)
    if output.exists():
        output.unlink()
    sidecar = output.with_name(output.name + '.sha256')
    if sidecar.exists():
        sidecar.unlink()

    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(directory.rglob('*')):
            if path.is_dir() or excluded(path):
                continue
            arcname = Path(addon_id) / path.relative_to(directory)
            archive.write(path, arcname.as_posix())

    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_name(output.name + '.sha256').write_text(digest + '\n', encoding='ascii')

    with zipfile.ZipFile(output, 'r') as archive:
        top_levels = {name.split('/', 1)[0] for name in archive.namelist() if name}
        if top_levels != {addon_id}:
            raise RuntimeError('Invalid package layout for {}: {}'.format(addon_id, sorted(top_levels)))
    return output


def build_addons_xml():
    addons_root = ET.Element('addons')
    for directory in ADDON_DIRS:
        addon_root = ET.parse(directory / 'addon.xml').getroot()
        addons_root.append(addon_root)

    ET.indent(addons_root, space='  ')
    body = ET.tostring(addons_root, encoding='utf-8', xml_declaration=True)
    if not body.endswith(b'\n'):
        body += b'\n'
    (ROOT / 'addons.xml').write_bytes(body)

    digest = hashlib.sha256(body).hexdigest()
    (ROOT / 'addons.xml.sha256').write_text(digest + '\n', encoding='ascii')


def build_pages_entry(repository_zip):
    bootstrap = ROOT / repository_zip.name
    shutil.copy2(repository_zip, bootstrap)
    html = '''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Appi Kodi Repository</title>
</head>
<body>
  <h1>Appi Kodi Repository</h1>
  <p><a href="{name}">{name}</a></p>
</body>
</html>
'''.format(name=repository_zip.name)
    (ROOT / 'index.html').write_text(html, encoding='utf-8')


def clean_old_bootstrap_zips(current_name):
    for path in ROOT.glob('repository.appi-*.zip'):
        if path.name != current_name:
            path.unlink()


def main():
    built = {}
    for directory in ADDON_DIRS:
        addon_id, version = addon_identity(directory)
        built[addon_id] = build_zip(directory, addon_id, version)

    build_addons_xml()
    repo_zip = built['repository.appi']
    clean_old_bootstrap_zips(repo_zip.name)
    build_pages_entry(repo_zip)

    print('Built:')
    for addon_id, path in built.items():
        print('  {} -> {}'.format(addon_id, path.relative_to(ROOT)))
    print('  repository bootstrap -> {}'.format((ROOT / repo_zip.name).relative_to(ROOT)))
    print('  index -> addons.xml')
    print('  checksum -> addons.xml.sha256')
    print('  GitHub Pages -> index.html')


if __name__ == '__main__':
    main()
