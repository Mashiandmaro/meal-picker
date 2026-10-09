"""Verify Pages subdirectory hosting, allowlisted publication and cache updates."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from tempfile import TemporaryDirectory
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_site import ASSETS, build
from playwright.sync_api import sync_playwright


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def run():
    with TemporaryDirectory() as temp:
        temp = Path(temp)
        source = temp / 'source'
        source.mkdir()
        for name in ASSETS:
            shutil.copyfile(ROOT / name, source / name)
        (source / 'debug.log').write_text('not for publication', encoding='utf-8')
        website = temp / 'web' / 'meal-picker'
        version1 = build(source, website)
        assert build(source, website) == version1
        assert set(p.name for p in website.iterdir()) == set(ASSETS) | {'.nojekyll', 'version.json'}
        server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(temp / 'web')))
        Thread(target=server.serve_forever, daemon=True).start()
        try:
            url = f'http://127.0.0.1:{server.server_port}/meal-picker/'
            with sync_playwright() as p:
                browser = p.chromium.launch()
                context = browser.new_context(viewport={'width':390, 'height':844}, is_mobile=True, has_touch=True)
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda e: errors.append(str(e)))
                page.goto(url, wait_until='networkidle')
                page.wait_for_selector('.meal-card')
                page.wait_for_function('navigator.serviceWorker.controller !== null')
                scope = page.evaluate('(async()=> (await navigator.serviceWorker.ready).scope)()')
                assert scope == url
                cache1 = f'good-meal:{url}:{version1}'
                assert page.evaluate('(async()=>await caches.keys())()') == [cache1]
                page.locator('[data-action="favorite"]').click()
                favorites = page.evaluate("JSON.parse(localStorage.getItem('good-meal:v1')).favorites")
                context.set_offline(True)
                page.reload(wait_until='load')
                page.wait_for_selector('.meal-card')
                context.set_offline(False)

                # A source change must create a new cache, preserve user data,
                # and survive the next offline launch after the update activates.
                with (source / 'styles.css').open('a', encoding='utf-8') as f:
                    f.write('\n:root{--release-check:updated;}\n')
                version2 = build(source, website)
                assert version2 != version1
                page.evaluate('(async()=>await (await navigator.serviceWorker.ready).update())()')
                page.wait_for_function("async()=>{const r=await navigator.serviceWorker.ready;return !!r.waiting}")
                page.close()
                page = context.new_page()
                page.goto(url, wait_until='networkidle')
                page.wait_for_function('(async()=>{const k=await caches.keys();return k.length===1 && k[0].endsWith("' + version2 + '")})()')
                assert page.evaluate("JSON.parse(localStorage.getItem('good-meal:v1')).favorites") == favorites
                assert page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--release-check').trim()") == 'updated'
                context.set_offline(True)
                page.reload(wait_until='load')
                page.wait_for_selector('.meal-card')
                assert page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--release-check').trim()") == 'updated'
                assert not errors
                browser.close()
        finally:
            server.shutdown()
    print('PASS: Pages subpath, public asset allowlist, deterministic build, offline launch, cache update, preserved favorites')


if __name__ == '__main__':
    run()
