"""Exercise restored Math controls and readable, local mathematical typesetting."""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8765');args=parser.parse_args()
    errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader'])
        page=browser.new_page(viewport={'width':1366,'height':768});page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(args.url+'/#worlds');page.wait_for_load_state('networkidle')
        assert page.locator('.atlas-view-switch button').all_text_contents()==['Demo','Experiment','Explain']
        assert not page.evaluate('performance.getEntriesByType("resource").some(r=>/\\.(wasm|mp4|woff2)/.test(r.name))')
        page.locator('[data-atlas-view=analysis]').click()
        for i in range(1,16):
            id=f'{i:02}';page.evaluate('(id)=>showWorld(id)',id)
            page.locator('#atlas-reset').click()
            assert page.locator('#analysis-formula math').count()>0
            assert page.locator('#atlas-controls').is_visible() and page.locator('#atlas-canvas').is_visible()
            assert not page.locator('#scene-live-stage').is_visible()
            control=page.locator('#atlas-parameter')
            if control.evaluate('e=>e.tagName')=='SELECT':
                values=control.locator('option').evaluate_all('options=>options.map(o=>o.value)')
                for v in values:control.select_option(v)
            else:
                control.evaluate('e=>{e.value=e.max;e.dispatchEvent(new Event("input",{bubbles:true}));}')
            assert page.locator('#scene-detail').get_attribute('data-view')=='analysis'
            page.locator('#atlas-progress').evaluate('e=>{e.value=650;e.dispatchEvent(new Event("input",{bubbles:true}));}')
            assert page.locator('#atlas-time').inner_text()=='6.5 / 8.0 s'
            assert not any(s in page.locator('#atlas-canvas').inner_html() for s in ['NaN','undefined'])
            page.locator('#atlas-play').click();page.wait_for_function('Number(document.querySelector("#atlas-progress").value)>650')
            page.locator('#atlas-play').click();t=page.locator('#atlas-progress').input_value();page.wait_for_timeout(50)
            assert page.locator('#atlas-progress').input_value()==t
            page.locator('#atlas-reset').click();assert page.locator('#atlas-progress').input_value()=='0'
            page.locator('.analysis-assumptions summary').click();assert page.locator('.analysis-assumptions p').is_visible()
            assert page.locator('.analysis-assumptions summary').inner_text()=='About this model'
            page.locator('.analysis-assumptions summary').click()
        assert page.evaluate('document.fonts.check(\'22px "STIX Two Math"\')')
        assert not page.evaluate('performance.getEntriesByType("resource").some(r=>/\\.(wasm|mp4)/.test(r.name))')
        page.locator('#analysis-fullscreen').click();page.wait_for_function('!!document.fullscreenElement')
        assert page.locator('.atlas-playback #atlas-controls').count()==1 and page.locator('#atlas-parameter').is_visible()
        page.locator('#analysis-fullscreen').click();page.wait_for_function('!document.fullscreenElement')
        assert page.locator('.scene-foot #atlas-controls').count()==1
        page.locator('[data-atlas-view=physics]').click()
        for i in range(1,16):
            page.evaluate('(id)=>showWorld(id)',f'{i:02}');page.locator('#scene-law > summary').click();page.evaluate('document.fonts.ready')
            text=page.locator('#scene-law-text').text_content()
            assert '^' not in text and '_' not in text,(i,text)
            page.wait_for_function('document.querySelector("#physics-values strong")!==null')
            assert page.locator('#physics-values span').first.evaluate('e=>getComputedStyle(e).fontSize')==page.locator('#physics-values strong').first.evaluate('e=>getComputedStyle(e).fontSize')=='12px'
            assert not any(t in page.locator('#physics-values').inner_text() for t in ['Waiting for impact','speed returned','v_z'])
            if i==8:
                assert page.locator('#scene-law-text mfrac').count()==2 and page.locator('#scene-law-text msub').count()>=2
                page.screenshot(path='/tmp/math-stix-08.png')
            page.locator('#scene-law > summary').click()
        for width,height in [(1366,768),(1280,720),(390,844),(320,740)]:
            page.set_viewport_size({'width':width,'height':height})
            page.locator('[data-atlas-view=analysis]').click()
            for i in range(1,16):
                page.evaluate('(id)=>showWorld(id)',f'{i:02}')
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(width,i)
                assert page.locator('#analysis-formula').evaluate('e=>e.scrollWidth<=e.clientWidth+1'),(width,i)
            page.locator('[data-atlas-view=physics]').click();page.evaluate('showWorld("08")');page.locator('#scene-law > summary').click()
            assert page.locator('#scene-law').evaluate('e=>e.scrollWidth<=e.clientWidth+1')
            page.locator('#scene-law > summary').click()
        page.set_viewport_size({'width':1366,'height':768});page.evaluate('showWorld("07")');page.locator('[data-atlas-view=analysis]').click();page.locator('#atlas-reset').click();page.screenshot(path=str(Path(__file__).resolve().parents[1]/'math-preview.png'))
        page.locator('[data-atlas-view=motion]').click();page.wait_for_function('window.SceneRoom?.getState().scene==="07"')
        page.locator('#scene-live-reset').click()
        page.locator('#scene-live-play').click();page.wait_for_function('SceneRoom.isRunning()')
        page.locator('[data-atlas-view=analysis]').click();time=page.evaluate('SceneRoom.getState().time');page.wait_for_timeout(120)
        assert page.evaluate('SceneRoom.getState().time')==time
        browser.close()
    assert not errors,errors
    print('PASS: all 15 Math formulas, parameters, playback, seek/reset, assumptions, fullscreen and view transitions; full rules have semantic fractions/subscripts; local font, lazy media, and 320–1366 px layout.')

if __name__=='__main__':main()
