#!/usr/bin/env python3
"""Build Kodi packages, repository metadata, and GitHub Pages bootstrap files."""

import hashlib
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ADDON_DIRS = [ROOT / 'plugin.video.appi', ROOT / 'repository.appi']


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
    )


def clean_old_package_files(directory, addon_id, current_zip_name):
    for path in directory.glob('{}-*.zip*'.format(addon_id)):
        if path.name not in {current_zip_name, current_zip_name + '.sha256'}:
            path.unlink()


def build_zip(directory, addon_id, version):
    output = directory / '{}-{}.zip'.format(addon_id, version)
    clean_old_package_files(directory, addon_id, output.name)
    output.unlink(missing_ok=True)
    sidecar = output.with_name(output.name + '.sha256')
    sidecar.unlink(missing_ok=True)

    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(directory.rglob('*')):
            if path.is_dir() or excluded(path):
                continue
            arcname = (Path(addon_id) / path.relative_to(directory)).as_posix()
            info = zipfile.ZipInfo(arcname, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100644 & 0xFFFF) << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

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


def clean_old_root_packages(current_names):
    for pattern in ('plugin.video.appi-*.zip', 'repository.appi-*.zip'):
        for path in ROOT.glob(pattern):
            if path.name not in current_names:
                path.unlink()


def build_pages_entry(plugin_zip, repository_zip):
    root_plugin = ROOT / plugin_zip.name
    root_repo = ROOT / repository_zip.name
    shutil.copy2(plugin_zip, root_plugin)
    shutil.copy2(repository_zip, root_repo)
    clean_old_root_packages({root_plugin.name, root_repo.name})

    html = '''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Appi Kodi Add-on</title>
</head>
<body>
  <h1>Appi Kodi Add-on</h1>
  <p><a href="{plugin}">{plugin}</a></p>
  <p><a href="{repository}">{repository}</a> (optional update repository)</p>
</body>
</html>
'''.format(plugin=root_plugin.name, repository=root_repo.name)
    (ROOT / 'index.html').write_text(html, encoding='utf-8')


def main():
    built = {}
    for directory in ADDON_DIRS:
        addon_id, version = addon_identity(directory)
        built[addon_id] = build_zip(directory, addon_id, version)

    build_addons_xml()
    build_pages_entry(built['plugin.video.appi'], built['repository.appi'])

    print('Built:')
    for addon_id, path in built.items():
        print('  {} -> {}'.format(addon_id, path.relative_to(ROOT)))
    print('  direct plugin bootstrap -> {}'.format(built['plugin.video.appi'].name))
    print('  optional repository bootstrap -> {}'.format(built['repository.appi'].name))
    print('  repository index -> addons.xml')
    print('  checksum -> addons.xml.sha256')
    print('  GitHub Pages -> index.html')


if __name__ == '__main__':
    main()
