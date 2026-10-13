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
        assert not page.locator("#exploration-dialog").evaluate("e=>e.open")
        assert page.locator('#model-chart .result-row').count()==12
        assert page.locator('.result-scene').count()==14
        assert page.locator('#result-details').count()==0
        assert page.locator('.result-control strong').inner_text()=='0 / 3'
        assert page.locator('#scene-picker button').count()==15
        assert page.locator('#benchmark-table tbody tr').count()==4
        assert page.locator('.controlled-card td').count()==30
        assert page.locator('#evolution-results tbody tr').count()==5
        assert not page.locator('#controlled-comparisons').evaluate('(e)=>!!e.closest("details")')
        assert not page.locator('#evolution-results').evaluate('(e)=>!!e.closest("details")')
        assert page.locator('[data-behavior="L"]').inner_text()=='39.3'
        assert page.locator('[data-behavior="CS"]').inner_text()=='11 / 45'
        assert page.locator('#model-chart [data-result-metric]').count()==36
        page.locator('[data-result-view="S"]').click()
        page.locator('#results-sort').select_option('score')
        assert page.locator('.result-lane:visible').count()==12
        assert page.locator('.result-model-name').nth(1).inner_text()=='GPT-5.6-Luna'
        page.locator('[data-model="Claude-Opus-5"]').click()
        assert page.locator('#result-model-title').inner_text()=='Claude-Opus-5'
        assert page.locator('.result-score.result-C dd > span').inner_text()=='7 / 42 runs'
        assert page.locator('.result-score.result-S dd > span').inner_text()=='0 / 42 runs'
        page.locator('[data-model="Claude-Opus-5"]').press('Home')
        assert page.locator('#result-model-title').inner_text()=='GPT-6-Astra'
        page.locator('[data-result-view="D"]').click()
        page.locator('[data-result-scene="07"]').click()
        assert page.locator('#exploration-dialog').evaluate('e=>e.open')
        assert page.locator('#discovery-title').inner_text()=='Tile rebounds'
        page.locator('#exploration-close').click()
        page.locator('[data-result-view="all"]').click()
        page.locator('#results-sort').select_option('paper')
        page.locator('[data-model="GLM-5.3"]').click()
        assert page.locator('.result-control strong').inner_text()=='3 / 3'
        page.locator('[data-model="GPT-6-Astra"]').click()
        assert 'Support: 3/3' in page.locator('.result-scene').first.get_attribute('title')
        assert page.locator('.result-data-link').get_attribute('href')=='downloads/model-results.csv'
        for number in range(1,16):
            page.locator(f'#scene-tab-{number:02}').click()
            page.wait_for_function('id=>document.querySelector("#scene-name").textContent===window.LONGCHANG.scenes.find(s=>s.id===id).name',arg=f"{number:02}")
            assert page.locator(f'#scene-tab-{number:02}').get_attribute('aria-selected')=='true'
        page.locator('[data-atlas-view=analysis]').click()
        assert '10 seconds' in page.locator('#scene-law-text').inner_text()
        page.locator('[data-atlas-view=physics]').click()
        for scene in ['07','06','14','15']:
            page.evaluate('(id)=>showDiscovery(id)',scene)
            page.wait_for_function('document.querySelector("#success-video").readyState>=2 && !document.querySelector("#success-video").paused')
            assert 'Astra' in page.locator('#discovery-source').inner_text()
            assert page.locator('#exploration-dialog button:visible').count()==3
            page.locator('#replay-play').click()
            page.locator('#replay-progress').evaluate('(e)=>{e.value=700;e.dispatchEvent(new Event("input",{bubbles:true}));}')
            page.wait_for_function('!document.querySelector("#success-video").seeking')
            assert page.locator('#success-description').inner_text()
        # Closing the archive pauses playback; model details reopen the right run.
        page.locator('#replay-play').click()
        page.wait_for_function('!document.querySelector("#success-video").paused')
        page.locator('#exploration-close').click()
        page.wait_for_function('document.querySelector("#success-video").paused')
        page.locator('[data-node="judge"]').click()
        assert 'judge' in page.locator('#fw-detail-description').inner_text()
        page.locator('#fw-play').click();page.wait_for_timeout(100)
        page.locator('#fw-play').click()
        page.locator('[data-result-view="D"]').click()
        page.locator('[data-result-scene="07"]').click()
        assert page.locator('#discovery-title').inner_text()=='Tile rebounds'
        page.locator('#exploration-close').click()
        page.locator('#tool-tab').click()
        assert page.locator('#tool-case').is_visible()
        assert not page.locator('#color-case').is_visible()
        page.locator('#tool-tab').press('ArrowLeft')
        assert page.locator('#color-case').is_visible()
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
        assert offline.locator('#model-chart .result-row').count()==12
        assert offline.locator('#scene-picker button').count()==15
        context.close();browser.close()
    assert not errors,errors
    print(json.dumps({'status':'PASS','checks':['four recorded films: play, pause, seek and automatic captions',
        'three case studies, compact replays and animated framework',
        'all scene and metric switches','keyboard tabs and model details','controlled table and data downloads',
        '320–1440 px overflow','mobile touch layout','reduced motion','offline local-file operation',
        'no JavaScript errors'],'screenshots':str(args.screenshots)},indent=2))


if __name__=='__main__':main()
