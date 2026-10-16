"""Check recorded-film provenance and the shared case-study playback UI."""
import argparse
import hashlib
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

SITE=Path(__file__).resolve().parents[1]
ROOT=SITE.parent


def drag_progress(page, slider, fraction):
    slider.scroll_into_view_if_needed()
    box=slider.bounding_box()
    start=box['x']+6+(box['width']-12)*float(slider.input_value())/1000
    end=box['x']+6+(box['width']-12)*fraction
    y=box['y']+box['height']/2
    page.mouse.move(start,y)
    page.mouse.down()
    page.mouse.move(end,y,steps=12)
    page.mouse.up()


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
        if 'render' in case:
            assert hashlib.sha256((SITE/case['poster']).read_bytes()).hexdigest()==case['poster_sha256']
            reference=case['render']['reference']
            assert hashlib.sha256((ROOT/reference).read_bytes()).hexdigest()==case['render']['reference_sha256']
    errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1440,'height':1000})
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(args.url,wait_until='domcontentloaded')
        page.evaluate('document.fonts.ready')
        assert not page.evaluate('performance.getEntriesByType("resource").some(r=>/case-(question|color|tool)\\.mp4/.test(r.name))')
        assert page.locator('#explore .case-tabs button').count()==3
        assert page.locator('#explore details, #explore [data-film-seek], #explore a').count()==0
        for case in manifest['cases']:
            key=case['id']
            page.locator(f'#{key}-tab').click()
            panel=page.locator(f'#{key}-case')
            film=panel.locator('.case-film')
            video=film.locator('video')
            slider=film.locator('.case-progress')
            play=film.locator('.case-play')
            expect(panel).to_be_visible()
            assert page.locator('.case-panel[hidden] video').evaluate_all('(vs)=>vs.every(v=>v.paused)')
            # Selecting a case starts the complete film without a second choice.
            page.wait_for_function('(key)=>{const v=document.getElementById(`case-${key}-video`);return !v.paused&&v.currentTime>.1}',arg=key)
            assert video.evaluate('(v,d)=>Math.abs(v.duration-d)<.1',case['duration'])
            assert video.evaluate('(v,size)=>v.videoWidth===size[0]&&v.videoHeight===size[1]',[case.get('width',manifest['width']),case.get('height',manifest['height'])])
            assert not video.evaluate('v=>v.controls')
            expect(video).to_have_js_property('playbackRate',2)
            film.locator('.case-speed').select_option('1')
            assert float(film.get_attribute('data-duration'))==case['duration']
            for chapter in case['chapters']:
                slider.evaluate('(e,v)=>{e.value=v;e.dispatchEvent(new Event("input",{bubbles:true}));}',chapter['start']/case['duration']*1000)
                page.wait_for_function('([key,t])=>{const v=document.getElementById(`case-${key}-video`);return !v.paused&&Math.abs(v.currentTime-t)<.75}',arg=[key,chapter['start']])
                step=case['chapters'].index(chapter)
                expect(panel.locator(f'[data-case-stage="{step}"]')).to_be_visible()
                assert panel.locator('[data-case-stage]:visible').count()==1
            # A real pointer drag previews frames, preserving play/pause state.
            drag_progress(page,slider,.3)
            expect(video).to_have_js_property('paused',False)
            assert video.evaluate('v=>Math.abs(v.currentTime/v.duration-.3)<.03')
            play.click()
            expect(play).to_have_attribute('aria-label','Play case study')
            drag_progress(page,slider,.6)
            page.wait_for_function('(key)=>!document.getElementById(`case-${key}-video`).seeking',arg=key)
            assert video.evaluate('v=>v.paused&&Math.abs(v.currentTime/v.duration-.6)<.01')
            before=video.evaluate('v=>v.currentTime')
            page.wait_for_timeout(100)
            assert video.evaluate('v=>v.currentTime')==before
            slider.press('End')
            expect(slider).to_have_value('1000')
            slider.press('ArrowLeft')
            expect(slider).to_have_value('999')
            slider.press('Home')
            expect(slider).to_have_value('0')
            assert video.evaluate('v=>v.paused&&v.currentTime===0')
            expect(panel.locator('[data-case-stage="0"]')).to_be_visible()
            film.locator('.case-speed').select_option('2')
            expect(video).to_have_js_property('playbackRate',2)
            film.locator('.case-speed').select_option('1')
            film.locator('.case-fullscreen').click()
            page.wait_for_function('(key)=>document.fullscreenElement===document.querySelector(`#${key}-case .case-film`)',arg=key)
            # Fullscreen keeps the same progress controls inside the viewport.
            box=film.locator('.case-playback').bounding_box()
            assert box['y']>=0 and box['y']+box['height']<=page.viewport_size['height']+1
            film.locator('.case-fullscreen').click()
            page.wait_for_function('!document.fullscreenElement')
            film.locator('.case-reset').click()
            page.wait_for_function('(key)=>{const v=document.getElementById(`case-${key}-video`);return !v.paused&&v.currentTime>0&&v.currentTime<1}',arg=key)
            play.click()
            slider.press('Home')
            page.evaluate('document.activeElement.blur()')
            panel.screenshot(path=f'/tmp/longchang-case-page-{key}.png')
            play.click()
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
        # Scrubbing before the first play lazily loads the film and stays paused.
        cold=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
        cold.on('pageerror',lambda error:errors.append(str(error)))
        cold.goto(args.url,wait_until='domcontentloaded')
        progress=cold.locator('#question-case .case-progress')
        progress.scroll_into_view_if_needed()
        box=progress.bounding_box()
        assert box['width']>300
        # Native touch drag across the full-width mobile timeline.
        cdp=cold.context.new_cdp_session(cold)
        y=box['y']+box['height']/2
        cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':box['x']+6,'y':y}]})
        for fraction in [.1,.2,.3,.4]:
            cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':box['x']+6+(box['width']-12)*fraction,'y':y}]})
        cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
        cold.wait_for_function('(()=>{const v=document.querySelector("#case-question-video");return v.readyState>=2&&!v.seeking&&v.paused&&Math.abs(v.currentTime-12.8)<.1})()')
        cold.evaluate('document.activeElement.blur()')
        cold.locator('#explore').screenshot(path='/tmp/longchang-case-mobile-touch.png')
        cold.close()
        # A failed download offers a working retry rather than a dead poster.
        broken=browser.new_page(viewport={'width':1280,'height':900})
        broken.on('pageerror',lambda error:errors.append(str(error)))
        broken.route('**/case-color.mp4',lambda route:route.abort())
        broken.goto(args.url,wait_until='domcontentloaded')
        broken.locator('#color-tab').click()
        retry=broken.locator('#color-case .case-film-status button')
        expect(retry).to_be_visible()
        broken.unroute('**/case-color.mp4')
        retry.click()
        broken.wait_for_function('!document.querySelector("#case-color-video").paused && document.querySelector("#case-color-video").currentTime>.1')
        expect(broken.locator('#color-case .case-film-status')).to_be_hidden()
        browser.close()
    assert not errors,errors
    print('PASS: source/video hashes; case selection; custom progress, mouse/touch scrubbing, keyboard seek, pause/resume, speed, restart and fullscreen; offscreen/tab pause and retry; lazy seeking before playback; 320–1440 px layouts.')


if __name__=='__main__':main()
