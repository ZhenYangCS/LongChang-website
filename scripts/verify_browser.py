"""Exercise the static page in Chromium with Playwright (no server required).

Optional dependency: playwright and its Chromium browser. Screenshots go to
the requested --screenshots directory, which defaults to a temporary folder.
"""
import argparse
import json
from pathlib import Path
import tempfile

from playwright.sync_api import sync_playwright

SITE=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',default=(SITE/'index.html').as_uri())
    parser.add_argument('--screenshots',type=Path,default=Path(tempfile.gettempdir())/'longchang-page-review')
    args=parser.parse_args();args.screenshots.mkdir(parents=True,exist_ok=True)
    errors=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1440,'height':1000})
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(args.url)
        page.evaluate('document.fonts.ready')
        page.wait_for_function('document.querySelector("#success-video").readyState>=2')
        assert page.locator('.chart-model-row').count()==12
        assert page.locator('.heat-cell').count()==168
        assert page.locator('#scene-picker button').count()==15
        for metric,count in [('D',12),('C',12),('S',12),('all',36)]:
            page.locator(f'[data-metric="{metric}"]').click()
            assert page.locator('.chart-lane').count()==count
        for metric in ['C','S','D']:
            page.locator(f'[data-heat="{metric}"]').click()
            assert page.locator('.heat-cell').count()==168
        page.locator('.heat-cell').first.focus()
        assert page.locator('#chart-tooltip').is_visible()
        assert 'GPT-6-Astra' in page.locator('#chart-tooltip').inner_text()
        page.keyboard.press('Escape')
        assert not page.locator('#chart-tooltip').is_visible()
        for number in range(1,16):
            page.locator(f'#scene-tab-{number:02}').click()
            page.wait_for_function('document.querySelector("#scene-image").complete && document.querySelector("#scene-image").naturalWidth>0')
            assert f'{number:02}' in page.locator('#scene-number').inner_text()
        page.locator('#scene-law summary').click()
        assert '10 counts' in page.locator('#scene-law-text').inner_text()
        page.locator('#scene-law summary').click()
        for scene in ['07','06','14','15']:
            page.locator('#success-tab-'+scene).click()
            assert 'Astra' in page.locator('#discovery-run').inner_text()
            for chapter in range(3):
                page.locator(f'[data-chapter="{chapter}"]').click()
                page.wait_for_function('document.querySelector("#success-video").readyState>=2')
                page.locator('#replay-play').click()
                page.wait_for_timeout(250)
                assert int(page.locator('#replay-progress').input_value())>0
                page.locator('#replay-play').click()
                before=page.locator('#replay-progress').input_value()
                page.wait_for_timeout(80)
                assert page.locator('#replay-progress').input_value()==before
                page.locator('#replay-progress').evaluate('(e)=>{e.value=700;e.dispatchEvent(new Event("input",{bubbles:true}));}')
                page.wait_for_timeout(150)
                assert page.locator('#success-video').evaluate('(v)=>Math.abs(v.currentTime/v.duration-.7)<.03')
                page.locator('#replay-reset').click()
                assert page.locator('#replay-progress').input_value()=='0'
            page.locator('#lab-reset').click()
            before=page.locator('#law-canvas').inner_html()
            page.locator('#lab-play').click();page.wait_for_timeout(220)
            after=page.locator('#law-canvas').inner_html()
            assert before!=after
            assert 'NaN' not in after and 'undefined' not in after
            if scene=='07':
                page.locator('#lab-value').fill('3')
                page.locator('#lab-swap').click()
                assert '3.0 bricks' in page.locator('#lab-readout').inner_text()
            elif scene=='06':
                page.locator('#lab-select').select_option('90');page.wait_for_timeout(100)
                assert 'NaN' not in page.locator('#law-canvas').inner_html()
            elif scene=='14':
                page.locator('#lab-select').select_option('hold')
                assert 'Holding red' in page.locator('#lab-readout').inner_text()
                page.locator('#lab-select').select_option('moving')
                assert 'replaced' in page.locator('#lab-readout').inner_text()
            else:
                page.locator('[data-push="blue"]').click()
                assert 'nonzero push' in page.locator('#lab-readout').inner_text()
                page.locator('#lab-zero').click()
                assert 'unchanged' in page.locator('#lab-readout').inner_text()
            page.locator('#lab-reset').click()
        page.locator('.cycle-step').nth(2).click()
        assert 'judge' in page.locator('#cycle-explanation').inner_text()
        page.locator('#cycle-play').click();page.wait_for_timeout(100)
        page.locator('#cycle-play').click()
        page.locator('[data-heat="D"]').click()
        page.locator('[data-success-scene="07"]').click()
        assert page.locator('#success-tab-07').get_attribute('aria-selected')=='true'
        page.locator('#tool-tab').click()
        assert page.locator('#tool-case').is_visible()
        assert not page.locator('#color-case').is_visible()
        page.locator('#tool-tab').press('ArrowLeft')
        assert page.locator('#color-case').is_visible()
        for i in [0,1]:
            page.locator('.full-results').nth(i).locator('summary').click()
        assert page.locator('#full-results-table tbody tr').count()==12
        assert page.locator('#controlled-table tbody tr').count()==9
        for i in [0,1]:page.locator('.full-results').nth(i).locator('summary').click()
        page.locator('[data-chapter="0"]').click()
        page.locator('.success-evidence .note-details summary').click()
        assert 'red' in page.locator('#success-note').inner_text().lower()
        page.locator('.success-evidence .note-details summary').click()
        # Test every local download through the browser's HTTP client when served.
        if args.url.startswith('http'):
            links=page.locator('a[href^="downloads/"]').evaluate_all('(a)=>[...new Set(a.map(x=>x.href))]')
            for link in links:
                response=page.request.get(link)
                assert response.status==200,(link,response.status)
                assert len(response.body())>100
        # Check responsive overflow at both desktop and small-phone sizes.
        for width in [1440,1024,768,390,360,320]:
            page.set_viewport_size({'width':width,'height':900})
            page.wait_for_timeout(120)
            dimensions=page.evaluate('({width:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth})')
            assert dimensions['scroll']<=dimensions['width'],(width,dimensions)
        page.set_viewport_size({'width':1440,'height':1000})
        page.evaluate('window.scrollTo({top:0,behavior:"instant"});document.activeElement.blur()')
        page.screenshot(path=str(args.screenshots/'desktop.png'))
        page.screenshot(path=str(args.screenshots/'desktop-full.png'),full_page=True)
        mobile=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
        mobile.goto(args.url);mobile.evaluate('document.fonts.ready')
        assert mobile.evaluate('document.documentElement.scrollWidth')==390
        mobile.screenshot(path=str(args.screenshots/'mobile-full.png'),full_page=True)
        reduced=browser.new_page(viewport={'width':390,'height':844},reduced_motion='reduce')
        reduced.goto(args.url)
        assert reduced.evaluate('getComputedStyle(document.documentElement).scrollBehavior')=='auto'
        # Local-file operation also works with the network disabled.
        context=browser.new_context(offline=True)
        offline=context.new_page();offline.goto((SITE/'index.html').as_uri())
        assert offline.locator('.chart-model-row').count()==12
        assert offline.locator('#scene-picker button').count()==15
        context.close();browser.close()
    assert not errors,errors
    print(json.dumps({'status':'PASS','checks':['12 successful-run video chapters: play, pause, seek, reset',
        'four interactive law illustrations and animated framework',
        'all scene and metric switches','keyboard tabs and heatmap tooltips','full tables and downloads',
        '320–1440 px overflow','mobile touch layout','reduced motion','offline local-file operation',
        'no JavaScript errors'],'screenshots':str(args.screenshots)},indent=2))


if __name__=='__main__':main()
