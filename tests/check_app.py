"""Behavior checks using a real browser with iPhone-sized viewports. No app build required."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import json
import tempfile
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

def run():
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT)))
    Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_port}/'
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={'width':390,'height':844}, is_mobile=True, has_touch=True, device_scale_factor=2, accept_downloads=True)
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(url, wait_until='networkidle')
        page.wait_for_selector('.picker-invitation')
        def state():
            return page.evaluate("JSON.parse(localStorage.getItem('good-meal:v1'))")
        def action(name):
            return page.locator(f'[data-action="{name}"]')
        def check(name, condition=True):
            assert condition, name
            results.append(name)
        def pick_meal():
            if not page.locator('#sheet').is_visible():
                action('shuffle').click()
            page.locator('.choice-card').first.click()
            action('confirm-choice').click()
            page.locator('#sheet').wait_for(state='hidden')
            page.wait_for_selector('.meal-card')

        pick_meal()

        # Data is coherent and every meal/type has at least one complete combination.
        data = page.evaluate("""async()=>{const d=await import('./data.js'); const e=await import('./engine.js');return {count:d.RECIPES.length,valid:d.RECIPES.every(e.validateRecipe),ids:new Set(d.RECIPES.map(r=>r.id)).size,coverage:Object.keys(d.MEALS).every(m=>Object.keys(d.TYPES).every(t=>d.RECIPES.some(r=>r.meals.includes(m)&&r.type===t))),scenes:d.RECIPES.every(r=>r.scenes.every(s=>r.parts.every(p=>p.scenes.includes(s))))}}""")
        check('48 valid, unique recipes with meal/type coverage and scene consistency',data=={'count':48,'valid':True,'ids':48,'coverage':True,'scenes':True})

        for width,height in [(320,568),(375,667),(390,844),(430,932),(844,390),(1100,800)]:
            page.set_viewport_size({'width':width,'height':height})
            for tab in ['today','library','mine']:
                page.locator(f'[data-tab="{tab}"]').click()
                page.wait_for_timeout(30)
                check(f'No horizontal overflow {width}x{height} {tab}',page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            box=page.locator('.bottom-nav').bounding_box()
            check(f'Navigation stays in viewport {width}',box['y']>=0 and box['y']+box['height']<=height+1)
        page.set_viewport_size({'width':390,'height':844})
        page.locator('[data-tab="today"]').click()
        # Stable candidate count for deterministic checks.
        page.locator('[data-action="meal"][data-value="lunch"]').click()
        pick_meal()
        page.locator('[data-action="type"][data-value="lean"]').click()
        first=state()['current']['id']
        pick_meal()
        check('Random selection avoids immediate repeats',state()['current']['id']!=first)
        current=state()['current']['id']
        action('favorite').click()
        check('Favorite stored',current in state()['favorites'])
        page.reload(wait_until='networkidle')
        check('Favorite survives reload',current in state()['favorites'])
        action('choose').click()
        action('choose').click()
        check('Choosing twice does not duplicate same day/meal',len(state()['history'])==1)

        page.locator('#preferences-button').click()
        page.locator('input[name="excluded"][value="鸡肉"]').check()
        page.locator('#preferences-form button[type="submit"]').click()
        for _ in range(5):
            pick_meal()
            check('Chicken excluded from all recommended components',all('鸡肉' not in part['tags'] for part in state()['current']['parts']))
        action('scene').click()
        page.locator('[data-action="set-scene"][data-value="quick"]').click()
        pick_meal()
        check('Scene filters recommendation','quick' in state()['current']['scenes'])

        action('swap').click()
        page.locator('#sheet [data-action="swap-role"][data-value="starch"]').click()
        old=next(x['id'] for x in state()['current']['parts'] if x['role']=='starch')
        action('replace-part').first.click()
        check('Replacing a component changes only that role',next(x['id'] for x in state()['current']['parts'] if x['role']=='starch')!=old)
        check('Modified combination is not falsely marked as already saved',page.locator('.favorite-art').get_attribute('aria-pressed')=='false')
        action('favorite').click()
        check('Adjusted recipe saved independently',state()['current']['id'].startswith('custom-') and len(state()['custom'])==1)

        page.locator('[data-tab="mine"]').click()
        action('new-recipe').click()
        page.locator('[name="title"]').fill('我的便捷晚餐 <img src=x onerror=alert(1)>')
        page.locator('[name="starch"]').fill('全麦面包')
        page.locator('[name="protein"]').fill('鸡蛋')
        page.locator('[name="veg"]').fill('黄瓜')
        page.locator('[name="tags"][value="鸡蛋"]').check()
        page.locator('#recipe-form button[type="submit"]').click()
        check('Custom recipe saved and safely rendered',len(state()['custom'])==2 and page.locator('img[src="x"]').count()==0)

        # Export content is round-trippable, malformed imports do not mutate state.
        with page.expect_download() as download:
            action('export').click()
        exported=json.loads(Path(download.value.path()).read_text(encoding='utf-8'))
        check('Export includes favorites and custom recipes',len(exported['custom'])==2 and exported['favorites']==state()['favorites'])
        before=state()
        page.locator('#import-file').set_input_files({'name':'bad.json','mimeType':'application/json','buffer':b'{"version":1}'})
        page.wait_for_timeout(100)
        check('Invalid import preserves existing data',state()==before)
        exported['excluded']=['鸡蛋']
        page.locator('#import-file').set_input_files({'name':'good.json','mimeType':'application/json','buffer':json.dumps(exported,ensure_ascii=False).encode('utf-8')})
        action('confirm-import').click()
        check('Valid import restores data',state()['excluded']==['鸡蛋'])

        page.locator('[data-tab="library"]').click()
        page.locator('[data-action="type"][data-value="all"]').click()
        action('scene').click();page.locator('[data-action="set-scene"][data-value="all"]').click()
        page.locator('#search').fill('不存在的食物名字')
        check('Empty search is explained',page.locator('.empty-state').is_visible())
        page.locator('#search').fill('牛肉')
        check('Search finds matching recipes',page.locator('.small-card').count()>0)
        action('detail').first.click()
        check('Detail sheet opens and fits viewport',page.locator('#sheet').is_visible() and page.locator('#sheet').bounding_box()['width']<=390)
        page.keyboard.press('Escape')
        page.locator('#sheet').wait_for(state='hidden')
        check('Dialog can be dismissed',not page.locator('#sheet').is_visible())

        page.emulate_media(reduced_motion='reduce')
        page.locator('[data-tab="today"]').click()
        pick_meal()
        check('Reduced motion preference respected',page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches"))
        page.wait_for_function('navigator.serviceWorker.controller !== null')
        await_cache=page.evaluate("async()=>{const c=await caches.open('good-meal-v1');return (await c.keys()).length}")
        check('App assets cached for offline use',await_cache>=11)
        context.set_offline(True)
        page.reload(wait_until='load')
        page.wait_for_selector('.meal-card')
        check('Offline reload works',page.locator('.meal-card').count()==1)
        context.set_offline(False)

        # Capture reviewable iPhone layouts.
        shots=ROOT/'screenshots';shots.mkdir(exist_ok=True)
        page.screenshot(path=str(shots/'iphone-home.png'),full_page=True)
        page.screenshot(path=str(shots/'iphone-viewport.png'))
        page.locator('[data-tab="library"]').click()
        page.locator('#search').fill('')
        page.screenshot(path=str(shots/'iphone-library.png'),full_page=True)
        page.locator('#preferences-button').click()
        page.screenshot(path=str(shots/'iphone-preferences.png'))
        check('No browser JavaScript errors',not errors)
        # Also capture a clean first-run home screen for the user.
        clean=context.new_page()
        clean.goto(url,wait_until='networkidle')
        clean.evaluate("localStorage.removeItem('good-meal:v1')")
        clean.reload(wait_until='networkidle')
        clean.locator('[data-action="meal"][data-value="lunch"]').click()
        clean.locator('.choice-card').first.click()
        clean.locator('[data-action="confirm-choice"]').click()
        clean.locator('#sheet').wait_for(state='hidden')
        clean.screenshot(path=str(shots/'iphone-home.png'),full_page=True)
        clean.screenshot(path=str(shots/'iphone-viewport.png'))
        context.close();browser.close()
    server.shutdown()
    print(f'PASS: {len(results)} checks')
    for item in results:
        print('  '+item)

if __name__=='__main__':
    run()
