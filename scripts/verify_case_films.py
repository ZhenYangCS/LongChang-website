"""Check recorded-film provenance, chapter playback and responsive presentation."""
import argparse
import hashlib
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

SITE=Path(__file__).resolve().parents[1]
ROOT=SITE.parent


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',default='http://127.0.0.1:8765')
    args=parser.parse_args()
    manifest=json.loads((SITE/'data/case-films.json').read_text())
    for source in manifest['sources'].values():
        for path, key in [('path','sha256'),('session','session_sha256')]:
            assert hashlib.sha256((ROOT/source[path]).read_bytes()).hexdigest()==source[key]
    for case in manifest['cases']:
        assert hashlib.sha256((SITE/case['video']).read_bytes()).hexdigest()==case['video_sha256']
    errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1440,'height':1000})
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(args.url,wait_until='domcontentloaded')
        page.evaluate('document.fonts.ready')
        assert not page.evaluate('performance.getEntriesByType("resource").some(r=>/case-(question|color|tool)\\.mp4/.test(r.name))')
        for case in manifest['cases']:
            key=case['id']
            page.locator(f'#{key}-tab').click()
            panel=page.locator(f'#{key}-case')
            film=panel.locator('.case-film')
            video=film.locator('video')
            expect(panel).to_be_visible()
            assert page.locator('.case-panel[hidden] video').evaluate_all('(vs)=>vs.every(v=>v.paused)')
            # Seeking an unloaded film must land in the requested chapter.
            if key=='tool':
                film.locator('[data-film-seek="14"]').click()
                page.wait_for_function('document.querySelector("#case-tool-video").currentTime>=14')
            else:
                film.locator('.case-film-start').click()
            page.wait_for_function('(key)=>{const v=document.getElementById(`case-${key}-video`);return !v.paused&&v.currentTime>.1}',arg=key)
            assert video.evaluate('(v,d)=>Math.abs(v.duration-d)<.1',case['duration'])
            assert video.evaluate('v=>v.videoWidth===1280&&v.videoHeight===720')
            for chapter in case['chapters']:
                button=film.locator(f'[data-film-seek="{chapter["start"]}"]')
                button.focus()
                button.press('Enter')
                page.wait_for_function('([key,t])=>{const v=document.getElementById(`case-${key}-video`);return !v.paused&&Math.abs(v.currentTime-t)<.75}',arg=[key,chapter['start']])
                expect(button).to_have_attribute('aria-pressed','true')
            video.evaluate('v=>v.pause()')
            video.evaluate('v=>v.currentTime=v.duration*.5')
            page.wait_for_timeout(100)
            before=video.evaluate('v=>v.currentTime')
            page.wait_for_timeout(100)
            assert video.evaluate('v=>v.currentTime')==before
            video.evaluate('v=>v.requestFullscreen()')
            page.wait_for_function('!!document.fullscreenElement')
            page.evaluate('document.exitFullscreen()')
            page.wait_for_function('!document.fullscreenElement')
            video.evaluate('v=>v.currentTime=0')
            page.wait_for_timeout(80)
            panel.screenshot(path=f'/tmp/longchang-case-page-{key}.png')
            video.evaluate('v=>v.play()')
            page.evaluate('window.scrollTo({top:0,behavior:"instant"})')
            expect(video).to_have_js_property('paused',True)
        # A case change through keyboard navigation also pauses the old film.
        page.locator('#question-tab').click()
        page.locator('#case-question-video').evaluate('v=>v.play()')
        page.locator('#question-tab').focus()
        page.locator('#question-tab').press('ArrowRight')
        expect(page.locator('#color-case')).to_be_visible()
        expect(page.locator('#case-question-video')).to_have_js_property('paused',True)
        for width in [1440,1024,768,390,320]:
            page.set_viewport_size({'width':width,'height':900})
            for case in manifest['cases']:
                page.locator('#'+case['id']+'-tab').click()
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(width,case['id'])
        page.locator('#tool-case').screenshot(path='/tmp/longchang-case-page-mobile.png')
        # A failed download offers a working retry rather than a dead poster.
        broken=browser.new_page(viewport={'width':1280,'height':900})
        broken.on('pageerror',lambda error:errors.append(str(error)))
        broken.route('**/case-color.mp4',lambda route:route.abort())
        broken.goto(args.url,wait_until='domcontentloaded')
        broken.locator('#color-tab').click()
        broken.locator('#color-case .case-film-start').click()
        retry=broken.locator('#color-case .case-film-status button')
        expect(retry).to_be_visible()
        broken.unroute('**/case-color.mp4')
        retry.click()
        broken.wait_for_function('!document.querySelector("#case-color-video").paused && document.querySelector("#case-color-video").currentTime>.1')
        expect(broken.locator('#color-case .case-film-status')).to_be_hidden()
        browser.close()
    assert not errors,errors
    print('PASS: source/video hashes; three films and nine chapters; play, pause, seek, fullscreen, offscreen/tab pause, retry; lazy loading and 320–1440 px layouts; no JavaScript errors.')


if __name__=='__main__':main()
