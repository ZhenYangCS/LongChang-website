"""Check live scene manipulation, view lifecycle, fullscreen and actual touch input."""
import argparse,math
from playwright.sync_api import sync_playwright

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8765');args=parser.parse_args();errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader'])
        page=browser.new_page(viewport={'width':1366,'height':768});page.on('pageerror',lambda e:errors.append(str(e)));page.goto(args.url+'/#worlds');page.wait_for_load_state('networkidle')
        assert not page.evaluate('performance.getEntriesByType("resource").some(r=>r.name.includes(".wasm"))')
        page.locator('[data-atlas-view=motion]').click();page.wait_for_function('window.SceneRoom?.getState().scene==="07"')
        assert page.evaluate('SceneRoom.getState().mode')=='drag'
        assert page.evaluate('!SceneRoom.isRunning()')
        page.locator('[data-scene-mode=push]').click()
        room=page.evaluate('SceneRoom.getRenderInfo().room')
        assert room['bounds']==[-6,6,-6,6,12] and abs(room['roofBottom']-12)<1e-6
        page.locator('#scene-live-reset').click();page.locator('#scene-live-stage').scroll_into_view_if_needed()
        pos=page.evaluate('SceneRoom.project("gray_ball_1")');page.mouse.move(pos['x'],pos['y']);page.mouse.down();page.mouse.move(pos['x']+65,pos['y']-20,steps=8);page.mouse.up()
        page.wait_for_function('Math.hypot(SceneRoom.getState().positions.gray_ball_1[0]+2.5,SceneRoom.getState().positions.gray_ball_1[1])>.2')
        page.locator('#scene-live-reset').click();page.locator('[data-scene-mode=drag]').click();pos=page.evaluate('SceneRoom.project("gray_ball_1")')
        page.mouse.move(pos['x'],pos['y']);page.mouse.down();page.mouse.move(pos['x'],pos['y']-50,steps=8)
        page.wait_for_function('SceneRoom.getState().positions.gray_ball_1[2]>2.1')
        lifted=page.evaluate('SceneRoom.getState().positions.gray_ball_1')
        assert math.hypot(lifted[0]+2.5,lifted[1])<.01,'Dragging straight up must not move the ball sideways'
        page.mouse.up();page.wait_for_function('SceneRoom.getState().positions.gray_ball_1[2]<.7')
        page.locator('#scene-live-reset').click();pos=page.evaluate('SceneRoom.project("gray_ball_1")')
        page.keyboard.down('Shift');page.mouse.move(pos['x'],pos['y']);page.mouse.down();page.mouse.move(pos['x']+35,pos['y']-10,steps=8)
        page.wait_for_function('SceneRoom.getState().time>.7')
        slid=page.evaluate('SceneRoom.getState().positions.gray_ball_1')
        assert math.hypot(slid[0]+2.5,slid[1])>.2 and abs(slid[2]-1.5)<.06,'Shift-drag must slide at the initial height'
        page.locator('#scene-live-stage canvas').dispatch_event('pointercancel',{'pointerId':1})
        assert page.evaluate('SceneRoom.getState().oracle.held') is None
        page.mouse.up();page.keyboard.up('Shift')
        page.locator('#scene-live-play').click();assert page.evaluate('!SceneRoom.isRunning()')
        state=page.evaluate('SceneRoom.getState()');page.locator('[data-atlas-view=physics]').click();page.wait_for_timeout(200)
        assert page.evaluate('SceneRoom.getState().time')==state['time']
        page.locator('[data-atlas-view=motion]').click();assert page.evaluate('SceneRoom.getState().time')==state['time']
        page.locator('#scene-live-fullscreen').click();page.wait_for_function('!!document.fullscreenElement')
        assert page.locator('#scene-live-controls').is_visible() and page.locator('#scene-live-play').is_visible()
        page.locator('[data-scene-mode=view]').click();assert page.evaluate('SceneRoom.getState().mode')=='view'
        before=page.evaluate('SceneRoom.project("gray_ball_1")');r=page.locator('#scene-live-stage').bounding_box();x=r['x']+r['width']/2;y=r['y']+r['height']/2
        page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+55,y+20,steps=8);page.mouse.up();after=page.evaluate('SceneRoom.project("gray_ball_1")');assert math.hypot(after['x']-before['x'],after['y']-before['y'])>3
        page.locator('#scene-live-fullscreen').click();page.wait_for_function('!document.fullscreenElement');assert page.locator('.scene-live-playback #scene-live-controls').count()==1
        for id in ['12','13','10','07']:
            page.evaluate('(id)=>showWorld(id)',id);page.wait_for_function('(id)=>window.SceneRoom?.getState().scene===id',arg=id)
            assert page.locator('#scene-live-stage canvas').count()==1
        page.locator('#scene-live-reset').click();assert page.evaluate('SceneRoom.getState().oracle.count')==0
        # A stationary grip on the heavier ball must use Workshop's mass-scaled
        # force, rather than the teaser's weaker spring (which drifted 0.27 high).
        page.evaluate('showWorld("03")');page.wait_for_function('window.SceneRoom?.getState().scene==="03"');page.locator('#scene-live-reset').click()
        page.locator('[data-scene-mode=drag]').click();pos=page.evaluate('SceneRoom.project("blue_ball")')
        page.mouse.move(pos['x'],pos['y']);page.mouse.down();page.wait_for_function('SceneRoom.getState().time>1.9')
        grip=page.evaluate('SceneRoom.getState()');assert grip['oracle']['held']=='blue_ball'
        assert abs(grip['positions']['blue_ball'][2]-grip['oracle']['gripTarget'][2])<.05
        page.mouse.up();assert page.evaluate('SceneRoom.getState().oracle.held') is None
        page.locator('#scene-live-reset').click();page.locator('[data-scene-mode=push]').click();page.locator('#scene-live-stage canvas').focus();page.keyboard.press('ArrowRight')
        page.wait_for_function('document.querySelector("#scene-live-play").getAttribute("aria-label")==="Pause live physics"')
        page.locator('[data-atlas-view=physics]').click();page.locator('#physics-play').click();assert page.locator('#atlas-tour').count()==0
        page.wait_for_function('!document.querySelector("#physics-video").paused');page.locator('#physics-play').click()
        page.locator('[data-room-mode=push]').click();page.wait_for_function('!!window.RoomDemo')
        wasm=page.evaluate('performance.getEntriesByType("resource").filter(r=>r.name.includes(".wasm")).length');assert wasm==1,wasm
        print('PASS: real push, lift/drop, rotate, pause/resume, fullscreen controls, fresh scene state and one shared WASM download.',flush=True)
        phone=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True);phone.on('pageerror',lambda e:errors.append(str(e)));phone.goto(args.url+'/#worlds')
        phone.locator('[data-atlas-view=motion]').tap();phone.wait_for_function('!!window.SceneRoom');phone.locator('#scene-live-reset').tap();phone.locator('#scene-live-stage').scroll_into_view_if_needed()
        phone.locator('[data-scene-mode=push]').tap()
        pos=phone.evaluate('SceneRoom.project("gray_ball_1")');cdp=phone.context.new_cdp_session(phone)
        cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[pos]})
        cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':pos['x']+32,'y':pos['y']-10}]})
        cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
        phone.wait_for_function('Math.hypot(SceneRoom.getState().positions.gray_ball_1[0]+2.5,SceneRoom.getState().positions.gray_ball_1[1])>.15')
        assert phone.evaluate('document.documentElement.scrollWidth')==390
        browser.close()
    assert not errors,errors
    print('PASS: mobile touch manipulates native bodies; no JavaScript errors.')

if __name__=='__main__':main()
