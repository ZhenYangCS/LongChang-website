"""Browser checks for the live world, concise scene films, and on-demand loading."""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright
from paper_scenes import paper_scene_names


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8765');parser.add_argument('--require-hd',action='store_true');args=parser.parse_args()
    names,_=paper_scene_names();errors=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader'])
        page=browser.new_page(viewport={'width':1440,'height':1000})
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(args.url);page.wait_for_load_state('networkidle')
        assert page.evaluate('document.readyState')=='complete'
        assert page.evaluate('performance.getEntriesByType("resource").filter(r=>/\\.(mp4|wasm)/.test(r.name)).length')==0
        assert page.locator('#scene-tab-07').get_attribute('aria-selected')=='true'
        assert page.locator('[data-atlas-view=initial]').count()==0
        assert page.locator('.atlas-copy').inner_text().strip().count('\n')<=2
        assert page.locator('#scene-picker .scene-choice-symbol').count()==15
        left=page.locator('.scene-index').bounding_box();right=page.locator('#scene-detail').bounding_box()
        assert left['x']+left['width']<right['x']
        assert abs(left['height']-right['height'])<1
        print('PASS: first load completes with no video or physics download.',flush=True)
        for i in range(1,16):
            id=f'{i:02}';page.locator('#scene-tab-'+id).click()
            assert page.locator('#scene-name').inner_text()==names[id]
            page.wait_for_function('!document.querySelector("#physics-video").paused')
            assert not page.locator('#oracle-chapters').is_visible()
            assert not page.locator('#atlas-model-note').is_visible()
            assert not page.locator('#scene-law').evaluate('(e)=>e.open')
            assert not page.locator('.full-rule').is_visible() and page.locator('#scene-law-text').text_content()
            assert len(page.locator('#oracle-plain').inner_text().split())<20
            page.locator('.physics-video-frame').scroll_into_view_if_needed()
            rule=page.locator('#oracle-plain').bounding_box();art=page.locator('.physics-video-frame').bounding_box()
            assert rule['y']+rule['height']<=art['y']
            if args.require_hd:assert page.locator('#physics-video').evaluate('(v)=>v.videoWidth')==1440
            assert page.locator('.physics-video-frame').get_attribute('data-framing')=='room'
            for rate in ['0.5','1','2','4']:
                page.locator('#physics-speed').select_option(rate)
                assert page.locator('#physics-video').evaluate('(v)=>v.playbackRate')==float(rate)
            left=page.locator('.scene-index').bounding_box();right=page.locator('#scene-detail').bounding_box()
            assert abs(left['height']-right['height'])<1
            page.locator('#physics-play').click();assert page.locator('#physics-video').evaluate('(v)=>v.paused')
            page.locator('#physics-progress').evaluate('e=>{e.value=650;e.dispatchEvent(new Event("input",{bubbles:true}));}')
            page.wait_for_function('()=>{const v=document.querySelector("#physics-video");return !v.seeking&&Math.abs(v.currentTime/v.duration-.65)<.02;}')
        # Changing framing preserves time and pause state; one video is decoded.
        page.locator('#physics-speed').select_option('1')
        t=page.locator('#physics-video').evaluate('(v)=>v.currentTime')
        source=page.locator('#physics-video').evaluate('(v)=>v.currentSrc')
        for mode in ['detail','room']:
            page.locator('#physics-view').click()
            assert page.locator('.physics-video-frame').get_attribute('data-framing')==mode
            assert page.locator('#physics-video').evaluate('(v)=>v.currentSrc')==source
            assert page.locator('#physics-video').evaluate('(v)=>v.paused')
            assert abs(page.locator('#physics-video').evaluate('(v)=>v.currentTime')-t)<.07
        page.locator('#physics-play').click()
        page.locator('#physics-view').click()
        page.wait_for_function('!document.querySelector("#physics-video").paused')
        page.locator('#physics-play').click()
        page.locator('#physics-fullscreen').click();page.wait_for_function('Boolean(document.fullscreenElement)');page.evaluate('document.exitFullscreen()')
        page.locator('#scene-law > summary').click()
        page.wait_for_function('document.querySelector("#oracle-chart path")!==null')
        assert page.locator('#physics-values').inner_text()
        page.locator('#atlas-tour').click();page.wait_for_function('!document.querySelector("#physics-video").paused')
        page.locator('#physics-video').evaluate('(v)=>v.currentTime=v.duration-.03');page.wait_for_function('LongChangAtlas.currentScene()==="02"')
        page.locator('#atlas-tour').click()
        print('PASS: 15 names, concise summaries and folded full rules, framing switch, playback rates, seek, fullscreen, measurements and tour.',flush=True)
        # Both views reserve the same space, including their bottom controls.
        for mode in ['physics','motion']:
            page.locator('[data-atlas-view='+mode+']').click()
            for i in range(1,16):
                page.evaluate('(id)=>showWorld(id)',f'{i:02}')
                panel=page.locator('#scene-detail').bounding_box();art=page.locator('#atlas-'+mode+'-view').bounding_box();dock=page.locator('.scene-foot').bounding_box()
                assert art['height']>180 and art['y']+art['height']<=dock['y']+.5,(mode,i,art,dock)
                assert abs(dock['y']+dock['height']-(panel['y']+panel['height']-1))<1,(mode,i)
                if mode=='motion':
                    page.wait_for_function('(id)=>window.SceneRoom?.getState().scene===id',arg=f'{i:02}',timeout=60000)
                    assert page.locator('#scene-live-controls').is_visible()
        page.locator('[data-atlas-view=physics]').click()
        page.locator('#replay-play').click();page.wait_for_function('!document.querySelector("#success-video").paused')
        page.locator('#replay-speed').select_option('2');assert page.locator('#success-video').evaluate('(v)=>v.playbackRate')==2
        page.locator('#replay-play').click()
        for width,height in [(1366,768),(1280,720),(1440,900)]:
            page.set_viewport_size({'width':width,'height':height})
            page.evaluate('document.querySelector("#worlds").scrollIntoView({behavior:"instant",block:"start"})')
            box=page.locator('.scene-workspace').bounding_box()
            assert box['y']>70 and box['y']+box['height']<=height,(width,height,box)
            tabs=page.locator('#scene-picker button').all()
            positions=[tab.bounding_box() for tab in tabs]
            assert len({round(b['x']) for b in positions})==5
            assert len({round(b['y']) for b in positions})==3
            assert all(page.locator('#scene-tab-'+f'{i:02}').is_visible() for i in range(1,16))
            for i in range(1,16):
                page.evaluate('(id)=>showWorld(id)',f'{i:02}')
                assert not page.locator('.full-rule').is_visible()
                assert page.locator('.physics-video-frame').bounding_box()['height']>=170
        for width in [1440,1024,768,390,360,320]:
            page.set_viewport_size({'width':width,'height':900})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
        page.locator('#scene-mobile-select').select_option('12')
        assert page.locator('#scene-name').inner_text()==names['12']
        page.wait_for_function('!document.querySelector("#physics-video").paused')
        page.locator('#physics-play').click()
        page.set_viewport_size({'width':1440,'height':1000})
        page.locator('[data-room-mode=push]').click();page.wait_for_function('Boolean(window.RoomDemo)',timeout=60000)
        pos=page.evaluate('RoomDemo.project("blue_ball")');page.mouse.move(pos['x'],pos['y']);page.mouse.down();page.mouse.move(pos['x']+65,pos['y']-25,steps=8);page.mouse.up()
        page.wait_for_function('Math.hypot(RoomDemo.getState().positions.blue_ball[0]+2,RoomDemo.getState().positions.blue_ball[1]+1.9)>.12',timeout=30000)
        page.locator('#room-reset').click();assert page.evaluate('RoomDemo.getState().time')==0
        page.locator('[data-room-mode=drag]').click();pos=page.evaluate('RoomDemo.project("blue_ball")')
        page.mouse.move(pos['x'],pos['y']);page.mouse.down();page.mouse.move(pos['x'],pos['y']-75,steps=8)
        page.wait_for_function('RoomDemo.getState().positions.blue_ball[2]>.6',timeout=30000);page.mouse.up()
        page.locator('#room-reset').click();pos=page.evaluate('RoomDemo.project("pendulum_bob")')
        page.mouse.move(pos['x'],pos['y']);page.mouse.down();page.mouse.move(pos['x']+55,pos['y'],steps=8)
        page.wait_for_function('Math.abs(RoomDemo.getState().qpos[0]+.4)>.05',timeout=30000);page.mouse.up()
        page.locator('#room-reset').click();page.locator('[data-room-mode=view]').click();assert page.evaluate('RoomDemo.getState().mode')=='view'
        print('PASS: native MuJoCo push, lift/drop, pendulum drag, reset and view controls.',flush=True)
        # Simulate a phone's actual touch event path, using the already loaded world.
        mobile=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
        mobile.goto(args.url);mobile.locator('[data-room-mode=push]').tap();mobile.wait_for_function('Boolean(window.RoomDemo)',timeout=60000)
        mobile.locator('#room-stage').scroll_into_view_if_needed();pos=mobile.evaluate('RoomDemo.project("blue_ball")')
        session=mobile.context.new_cdp_session(mobile)
        session.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[pos]})
        session.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':pos['x']+30,'y':pos['y']-12}]})
        session.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
        mobile.wait_for_function('Math.hypot(RoomDemo.getState().positions.blue_ball[0]+2,RoomDemo.getState().positions.blue_ball[1]+1.9)>.1',timeout=30000)
        assert mobile.evaluate('document.documentElement.scrollWidth')==390
        mobile.locator('#room-reset').tap();browser.close()
    assert not errors,errors
    print('PASS: 320–1440 px layout, real mobile touch, no JavaScript errors.')

if __name__=='__main__':main()
