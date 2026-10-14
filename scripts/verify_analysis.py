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
        assert page.locator('#worlds .atlas-view-switch button').all_text_contents()==['Demo','Interactive']
        assert not page.evaluate('performance.getEntriesByType("resource").some(r=>/\\.(wasm|mp4)/.test(r.name))')
        page.locator('[data-atlas-view=physics]').click();page.locator('#demo-explanation').scroll_into_view_if_needed()
        for i in range(1,16):
            id=f'{i:02}';page.evaluate('(id)=>showWorld(id)',id)
            page.locator('#atlas-reset').click()
            assert page.locator('#analysis-formula math').count()>0
            assert page.locator('#atlas-controls').is_visible() and page.locator('#atlas-canvas').is_visible()
            assert not page.locator('#scene-live-stage').is_visible()
            control=page.locator('#atlas-parameter')
            if page.locator('#atlas-controls input[type=radio]').count()>0:
                values=page.locator('#atlas-controls input[type=radio]').evaluate_all('options=>options.map(o=>o.value)')
                for v in values:page.locator(f'#atlas-controls input[type=radio][value="{v}"]').check()
            else:
                control.evaluate('e=>{e.value=e.max;e.dispatchEvent(new Event("input",{bubbles:true}));}')
            assert page.locator('#scene-detail').get_attribute('data-view')=='physics'
            page.locator('#atlas-progress').evaluate('e=>{e.value=650;e.dispatchEvent(new Event("input",{bubbles:true}));}')
            assert page.locator('#atlas-time').text_content()=='6.5 / 8.0 s'
            assert not any(s in page.locator('#atlas-canvas').inner_html() for s in ['NaN','undefined'])
            page.locator('#atlas-play').click();page.wait_for_function('Number(document.querySelector("#atlas-progress").value)>650')
            page.locator('#atlas-play').click();t=page.locator('#atlas-progress').input_value();page.wait_for_timeout(50)
            assert page.locator('#atlas-progress').input_value()==t
            page.locator('#atlas-reset').click();assert page.locator('#atlas-progress').input_value()=='0'
            assert page.locator('.analysis-assumptions').count()==0
            assert not page.locator('#atlas-progress').is_visible() and not page.locator('.scene-foot').is_visible()
            assert page.locator('#atlas-controls').is_visible()
        assert page.evaluate('document.fonts.check(\'22px "STIX Two Math"\')')
        assert not page.evaluate('performance.getEntriesByType("resource").some(r=>/\\.(wasm|mp4)/.test(r.name))')
        page.locator('#analysis-fullscreen').click();page.wait_for_function('!!document.fullscreenElement')
        assert page.locator('.atlas-playback #atlas-controls').count()==1 and page.locator('#atlas-controls').is_visible()
        page.locator('#analysis-fullscreen').click();page.wait_for_function('!document.fullscreenElement')
        assert page.locator('.atlas-playback #atlas-controls').count()==1
        for i in range(1,16):
            page.evaluate('(id)=>showWorld(id)',f'{i:02}');page.evaluate('document.fonts.ready')
            assert page.locator('#analysis-model-note').is_visible()
            assert page.locator('#model-heading').text_content()==('Count the touches' if i==13 else 'Simplified model') and page.locator('#analysis-model-note').text_content()
            assert page.locator('#full-rule-label').text_content()=='Scene rule'
            text=page.locator('#scene-law-text').text_content()
            assert '^' not in text and '_' not in text,(i,text)
            page.locator('#demo-rule').scroll_into_view_if_needed()
            page.wait_for_function('!document.querySelector("#oracle-chart-wrap").hidden')
            assert page.locator('#oracle-signal').text_content().startswith('Video data · ')
            assert page.locator('#oracle-chart').is_visible() and page.locator('#scene-law a[download]').count()==0
            assert page.locator('#scene-law summary').count()==0
            if i==8:
                assert page.locator('#analysis-formula mfrac').count()==2 and page.locator('#analysis-formula msup').count()>=2
                page.screenshot(path='/tmp/math-stix-08.png')
            if i==12:
                assert 'Red' in page.locator('#oracle-chart').text_content() and 'Blue' in page.locator('#oracle-chart').text_content()
        for width,height in [(1366,768),(1280,720),(390,844),(320,740)]:
            page.set_viewport_size({'width':width,'height':height})
            page.locator('[data-atlas-view=physics]').click();page.locator('#demo-explanation').scroll_into_view_if_needed()
            for i in range(1,16):
                page.evaluate('(id)=>showWorld(id)',f'{i:02}')
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(width,i)
                assert page.locator('#analysis-formula').evaluate('e=>e.scrollWidth<=e.clientWidth+1'),(width,i)
            page.evaluate('showWorld("08")')
            assert page.locator('#scene-law').evaluate('e=>e.scrollWidth<=e.clientWidth+1')
            page.locator('[data-atlas-view=physics]').click();assert page.locator('#scene-law').is_visible()
        page.set_viewport_size({'width':1366,'height':768});page.evaluate('showWorld("07")');page.locator('[data-atlas-view=physics]').click();page.locator('#demo-explanation').scroll_into_view_if_needed();page.locator('#atlas-reset').click();page.locator('#demo-explanation').screenshot(path=str(Path(__file__).resolve().parents[1]/'math-preview.png'))
        page.locator('[data-atlas-view=motion]').click();page.wait_for_function('window.SceneRoom?.getState().scene==="07"')
        page.locator('#scene-live-reset').click()
        page.locator('#scene-live-play').click();page.wait_for_function('SceneRoom.isRunning()')
        page.locator('[data-atlas-view=physics]').click();page.locator('#demo-explanation').scroll_into_view_if_needed();time=page.evaluate('SceneRoom.getState().time');page.wait_for_timeout(120)
        assert page.evaluate('SceneRoom.getState().time')==time
        browser.close()
    assert not errors,errors
    print('PASS: all 15 integrated Demo formulas, parameters, play/reset, fullscreen and view transitions; rules, recorded plots and sources are integrated without extra disclosures; local mathematical font, lazy media, and 320–1366 px layout.')

if __name__=='__main__':main()
