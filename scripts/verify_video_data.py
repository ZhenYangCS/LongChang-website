"""Check chart ownership and playheads against the original recorded timelines."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

SITE = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8765/')
    args = parser.parse_args()
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--enable-unsafe-swiftshader'])
        page = browser.new_page(viewport={'width':1366, 'height':900})
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(args.url, wait_until='networkidle')
        page.locator('#physics-speed').select_option('1')
        assert page.locator('#atlas-physics-view #oracle-chart').count() == 1
        assert page.locator('#demo-explanation #oracle-chart').count() == 0
        for i in range(1, 16):
            scene = f'{i:02}'
            record = json.loads((SITE/f'data/scene-details/{scene}.json').read_text())
            page.locator('#scene-tab-'+scene).click()
            page.wait_for_function('document.querySelector("#physics-video").readyState>=2&&!document.querySelector("#physics-video").paused')
            page.locator('#physics-play').click()
            page.wait_for_function('!!document.querySelector("#oracle-cursor")')
            for fraction in [.15, .5, .85]:
                page.locator('#physics-progress').evaluate('(e,f)=>{e.value=f*1000;e.dispatchEvent(new Event("input",{bubbles:true}));}', fraction)
                page.wait_for_function('f=>{const v=document.querySelector("#physics-video");return !v.seeking&&Math.abs(v.currentTime/v.duration-f)<.01;}', arg=fraction)
                media_time = page.locator('#physics-video').evaluate('v=>v.currentTime')
                index = min(len(record['timeline'])-1, int(media_time*record['fps']))
                expected = record['timeline'][index]['time']
                actual = float(page.locator('#oracle-cursor').get_attribute('data-time'))
                assert abs(actual-expected) < .05, (scene, fraction, expected, actual)
            frozen = page.locator('#oracle-cursor').get_attribute('transform')
            page.locator('#atlas-parameter').evaluate('e=>{e.value=e.tagName==="SELECT"?e.options[e.options.length-1].value:e.max;e.dispatchEvent(new Event(e.tagName==="SELECT"?"change":"input",{bubbles:true}));}')
            page.wait_for_timeout(100)
            assert page.locator('#oracle-cursor').get_attribute('transform') == frozen
        print('PASS: all 15 video playheads match native recorded timestamps after seeking; independent model controls leave them unchanged.', flush=True)

        page.locator('#scene-tab-07').click()
        page.wait_for_function('!document.querySelector("#physics-video").paused')
        page.wait_for_function('Number(document.querySelector("#oracle-cursor").dataset.time)>.1')
        changes = page.evaluate('''async()=>{
          const cursor=document.querySelector('#oracle-cursor'),values=new Set();
          const observer=new MutationObserver(()=>values.add(cursor.dataset.time));
          observer.observe(cursor,{attributes:true,attributeFilter:['data-time']});
          await new Promise(resolve=>setTimeout(resolve,600));observer.disconnect();
          return values.size;
        }''')
        assert changes >= 8, changes
        page.locator('#physics-play').click()
        frozen = page.locator('#oracle-cursor').get_attribute('data-time')
        page.wait_for_timeout(200)
        assert page.locator('#oracle-cursor').get_attribute('data-time') == frozen
        page.locator('#physics-reset').click()
        assert float(page.locator('#oracle-cursor').get_attribute('data-time')) == 0
        page.locator('#physics-fullscreen').click()
        page.wait_for_function('document.fullscreenElement?.id==="atlas-physics-view"')
        assert page.locator('#oracle-chart').is_visible()
        page.locator('#physics-fullscreen').click()
        page.wait_for_function('!document.fullscreenElement')
        page.locator('#analysis-fullscreen').click()
        page.wait_for_function('document.fullscreenElement?.id==="demo-explanation"')
        assert page.evaluate('!document.fullscreenElement.contains(document.querySelector("#oracle-chart"))')
        page.locator('#analysis-fullscreen').click()
        page.wait_for_function('!document.fullscreenElement')
        print('PASS: playhead advances with video frames, freezes on pause, returns to zero on reset, and stays with the video in fullscreen.', flush=True)

        signals = json.loads((SITE/'data/evolution-signals.json').read_text())
        page.locator('#evolution').scroll_into_view_if_needed()
        assert page.locator('#evo-demo-view #evo-demo-chart').count() == 1
        assert page.locator('#evo-explanation #evo-demo-chart').count() == 0
        for key in ['generate', 'mutate', 'compose']:
            page.locator('[data-evolution='+key+']').click()
            page.wait_for_function('document.querySelector("#evo-demo-video").readyState>=2')
            page.wait_for_function('!!document.querySelector(".evo-recorded-cursor")')
            page.locator('#evo-demo-progress').evaluate('e=>{e.value=650;e.dispatchEvent(new Event("input",{bubbles:true}));}')
            page.wait_for_function('()=>{const v=document.querySelector("#evo-demo-video");return !v.seeking&&Math.abs(v.currentTime/v.duration-.65)<.01;}')
            samples = signals[key]['samples']
            expected = samples[round((len(samples)-1)*.65)][0]
            actual = float(page.locator('.evo-recorded-cursor').get_attribute('data-time'))
            assert abs(actual-expected) < .05, (key, expected, actual)
            frozen = page.locator('.evo-recorded-cursor').get_attribute('transform')
            page.locator('#evo-model-parameter').evaluate('e=>{e.selectedIndex=e.options.length-1;e.dispatchEvent(new Event("change",{bubbles:true}));}')
            page.wait_for_timeout(100)
            assert page.locator('.evo-recorded-cursor').get_attribute('transform') == frozen
        print('PASS: all three evolution charts follow their recorded videos and ignore the separate model clock.', flush=True)
        browser.close()
    assert not errors, errors


if __name__ == '__main__':
    main()
