"""Exercise the three-card chooser, cancellation, daily selections and migration."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

def run():
    server = ThreadingHTTPServer(('127.0.0.1',0), partial(QuietHandler,directory=str(ROOT)))
    Thread(target=server.serve_forever,daemon=True).start()
    url=f'http://127.0.0.1:{server.server_port}/'
    results=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch()
            context=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,device_scale_factor=2)
            page=context.new_page()
            errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(url,wait_until='networkidle')
            def action(name): return page.locator(f'[data-action="{name}"]')
            def state(): return page.evaluate("JSON.parse(localStorage.getItem('good-meal:v1'))")
            def ids(): return page.locator('.choice-radio').evaluate_all('(inputs)=>inputs.map(i=>i.value)')
            def check(name,condition=True):
                assert condition,name
                results.append(name)
            def dismiss():
                page.locator('#close-sheet').click()
                expect(page.locator('#sheet')).not_to_be_visible()
            def confirm(index=0):
                chosen=ids()[index]
                page.locator('.choice-card').nth(index).click()
                expect(action('confirm-choice')).to_be_enabled()
                action('confirm-choice').click()
                expect(page.locator('#sheet')).not_to_be_visible()
                expect(page.locator('#main>.meal-card')).to_be_visible()
                return chosen

            check('Fresh visit asks user to pick instead of silently deciding',page.locator('.picker-invitation').is_visible())
            page.locator('[data-action="meal"][data-value="lunch"]').click()
            check('Meal switch opens three unique choices',len(ids())==3 and len(set(ids()))==3)
            before=state()
            expect(action('confirm-choice')).to_be_disabled()
            first_batch=ids()
            page.locator('.choice-card').nth(1).click()
            check('Preview does not commit a selection',state()==before)
            check('Selection uses native accessible radio and highlight',page.locator('.choice-card.selected').count()==1 and page.locator('.choice-radio:checked').count()==1)
            action('refresh-choices').click()
            check('Next batch avoids previous three when possible',not set(first_batch)&set(ids()))
            expect(action('confirm-choice')).to_be_disabled()
            dismiss()
            check('Cancel preserves stored choices',state()==before)
            action('shuffle').click()
            selected=confirm(1)
            check('Confirmed card becomes current meal',state()['current']['id']==selected and state()['selections']['lunch']['recipe']['id']==selected)
            base_parts=state()['current']['parts']
            page.locator('.part-swap[data-value="starch"]').click()
            action('replace-part').first.click()
            updated=state()['current']
            check('Inline replacement changes only selected component',updated['parts'][0]['id']!=base_parts[0]['id'] and updated['parts'][1:]==base_parts[1:])
            page.locator('[data-action="meal"][data-value="dinner"]').click()
            dinner_id=confirm()
            page.locator('[data-action="meal"][data-value="lunch"]').click()
            dismiss()
            check('Lunch edits survive switching to dinner and back',state()['current']['parts']==updated['parts'])
            check('Dinner is remembered separately',state()['selections']['dinner']['recipe']['id']==dinner_id)
            page.reload(wait_until='networkidle')
            check('Edited meal survives reload',state()['current']['parts']==updated['parts'])

            # The constrained pool is shown honestly, without duplicate cards.
            page.locator('[data-action="meal"][data-value="breakfast"]').click();dismiss()
            page.locator('[data-action="type"][data-value="free"]').click()
            action('shuffle').click()
            check('Two matches produce two cards, no duplicate filler',len(ids())==2 and len(set(ids()))==2)
            expect(action('refresh-choices')).to_be_disabled()
            dismiss();action('scene').click()
            page.locator('[data-action="set-scene"][data-value="quick"]').click()
            action('shuffle').click()
            check('One match produces one selectable card',len(ids())==1)
            confirm()

            # Exclusions and scene filters apply to every candidate, not only the selected one.
            page.locator('[data-action="type"][data-value="lean"]').click()
            page.locator('#preferences-button').click()
            for value in ['鸡蛋','奶制品','鸡肉']:
                page.locator(f'input[name="excluded"][value="{value}"]').check()
            page.locator('#preferences-form button[type="submit"]').click()
            page.locator('[data-action="meal"][data-value="lunch"]').click()
            choices=ids()
            ok=page.evaluate("""async ids=>{const d=await import('./data.js');return ids.every(id=>{const r=d.RECIPES.find(r=>r.id===id);return r.type==='lean'&&r.meals.includes('lunch')&&r.scenes.includes('quick')&&!r.parts.some(p=>p.tags.some(t=>['鸡蛋','奶制品','鸡肉'].includes(t)))})}""",choices)
            check('All three-card options obey type, meal, scene and exclusions',ok and len(choices)>0)
            dismiss();page.locator('#preferences-button').click()
            page.locator('input[name="excluded"][value="牛肉"]').check()
            page.locator('input[name="excluded"][value="鱼类"]').check()
            page.locator('#preferences-form button[type="submit"]').click()
            page.locator('[data-action="meal"][data-value="lunch"]').click()
            check('Empty pool offers no made-up choices',len(ids())==0 and page.locator('.choice-empty').is_visible())
            expect(action('confirm-choice')).to_be_disabled();dismiss()

            # Prepare a full pool, inspect responsive modal and keyboard navigation.
            page.locator('#preferences-button').click()
            for checkbox in page.locator('#preferences-form input').all():checkbox.uncheck()
            page.locator('#preferences-form button[type="submit"]').click()
            action('scene').click();page.locator('[data-action="set-scene"][data-value="all"]').click()
            for width,height in [(320,568),(375,667),(390,844),(430,932),(844,390)]:
                page.set_viewport_size({'width':width,'height':height})
                action('shuffle').click()
                page.wait_for_timeout(450)
                sheet=page.locator('#sheet').bounding_box()
                footer=action('confirm-choice').bounding_box()
                check(f'Chooser fits {width}x{height} with visible confirmation',sheet['x']>=0 and sheet['y']>=0 and sheet['width']<=width and footer['y']>=0 and footer['y']+footer['height']<=height)
                check(f'No horizontal modal overflow {width}',page.locator('#sheet').evaluate('(e)=>e.scrollWidth<=e.clientWidth'))
                confirm(2)

            page.set_viewport_size({'width':390,'height':844})
            action('shuffle').click()
            page.locator('.choice-radio').first.focus()
            page.keyboard.press('Space')
            page.keyboard.press('ArrowDown')
            check('Native radio keyboard navigation updates selection',page.locator('.choice-radio').nth(1).is_checked() and page.locator('.choice-card').nth(1).evaluate('(e)=>e.classList.contains("selected")'))
            page.wait_for_timeout(300)
            (ROOT/'screenshots').mkdir(exist_ok=True)
            page.screenshot(path=str(ROOT/'screenshots'/'iphone-three-choices.png'))
            page.keyboard.press('Escape');expect(page.locator('#sheet')).not_to_be_visible()
            page.emulate_media(reduced_motion='reduce')
            action('shuffle').click()
            check('Reduced motion disables card entrance animation',page.locator('.choice-card').first.evaluate('(e)=>getComputedStyle(e).animationName')=='none')
            dismiss()

            # Old v1 backups stay readable; a past day's picks do not become today's choices.
            migrated=page.evaluate("""async()=>{const e=await import('./engine.js');const d=await import('./data.js');const old=e.defaults();delete old.selections;old.meal='lunch';old.current=d.RECIPES.find(r=>r.id==='m01');old.favorites=['m01'];const result=e.validateState(old);return result.favorites[0]==='m01'&&result.selections.lunch.recipe.id==='m01'}""")
            check('Old backups migrate without losing favorite or current meal',migrated)
            page.evaluate("""()=>{const s=JSON.parse(localStorage.getItem('good-meal:v1'));for(const item of Object.values(s.selections))item.date='2000-01-01';localStorage.setItem('good-meal:v1',JSON.stringify(s));}""")
            page.reload(wait_until='networkidle')
            check('New day prompts a fresh choice',page.locator('.picker-invitation').is_visible())
            page.locator('[data-tab="mine"]').click()
            action('new-recipe').click()
            page.locator('[name="title"]').fill('长食材名称的便当')
            page.locator('[name="starch"]').fill('米饭')
            page.locator('[name="protein"]').fill('鸡肉'*40)
            page.locator('[name="veg"]').fill('青菜')
            page.locator('#recipe-form button[type="submit"]').click()
            action('detail').first.click();action('use-recipe').click()
            page.locator('.part-swap[data-value="starch"]').click()
            action('replace-part').first.click()
            page.reload(wait_until='networkidle')
            check('Long custom ingredient names remain valid after replacement and reload',page.locator('.storage-warning').count()==0 and len(state()['current']['title'])<=60)
            check('No JavaScript errors',not errors)
            browser.close()
    finally:
        server.shutdown()
    print(f'PASS: {len(results)} chooser checks')
    for result in results: print('  '+result)

if __name__=='__main__':run()
