"""Prepare only public application assets for static hosting (Python standard library)."""
from hashlib import sha256
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
ASSETS = (
    'index.html', 'styles.css', 'app.js', 'data.js', 'engine.js', 'sw.js',
    'icon.svg', 'manifest.webmanifest', 'apple-touch-icon.png',
    'icon-192.png', 'icon-512.png',
)


def build(source=ROOT, destination=None):
    source = Path(source).resolve()
    destination = Path(destination or source / '_site').resolve()
    if destination == source:
        raise ValueError('Build destination must be separate from source')
    payloads = {name: (source / name).read_bytes() for name in ASSETS}
    digest = sha256()
    for name, content in sorted(payloads.items()):
        digest.update(name.encode('utf-8') + b'\0' + content + b'\0')
    version = digest.hexdigest()[:16]
    # One cache namespace per Pages subdirectory; source changes automatically
    # trigger a new worker without asking the user to manage version numbers.
    worker = payloads['sw.js'].decode('utf-8')
    worker, count = re.subn(
        r"const CACHE='good-meal-v1';",
        "const CACHE_PREFIX='good-meal:'+self.registration.scope+':';\n"
        f"const CACHE=CACHE_PREFIX+'{version}';",
        worker, count=1,
    )
    if count != 1:
        raise ValueError('Service worker cache marker changed; update build script')
    worker = worker.replace("k.startsWith('good-meal-')", 'k.startsWith(CACHE_PREFIX)')
    worker = worker.replace('fetch(event.request)', "fetch(event.request,{cache:'no-cache'})")
    payloads['sw.js'] = worker.encode('utf-8')
    payloads['.nojekyll'] = b''
    payloads['version.json'] = (json.dumps({'version': version}) + '\n').encode('utf-8')
    destination.mkdir(parents=True, exist_ok=True)
    # Never recursively delete an output directory. Refuse unexpected files
    # instead of accidentally publishing them or removing user-owned content.
    unexpected = {p.name for p in destination.iterdir()} - set(payloads)
    if unexpected:
        raise ValueError('Unexpected files in build output: ' + ', '.join(sorted(unexpected)))
    for name, content in payloads.items():
        (destination / name).write_bytes(content)
    return version


if __name__ == '__main__':
    version = build()
    print(f'Prepared {len(ASSETS)} app assets in _site (version {version})')
