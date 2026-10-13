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
        page.locator('#scene-live-reset').click();page.locator('#scene-live-stage').scroll_into_view_if_needed()
        pos=page.evaluate('SceneRoom.project("gray_ball_1")');page.mouse.move(pos['x'],pos['y']);page.mouse.down();page.mouse.move(pos['x']+65,pos['y']-20,steps=8);page.mouse.up()
        page.wait_for_function('Math.hypot(SceneRoom.getState().positions.gray_ball_1[0]+2.5,SceneRoom.getState().positions.gray_ball_1[1])>.2')
        page.locator('#scene-live-reset').click();page.locator('[data-scene-mode=drag]').click();pos=page.evaluate('SceneRoom.project("gray_ball_1")')
        page.mouse.move(pos['x'],pos['y']);page.mouse.down();page.mouse.move(pos['x'],pos['y']-50,steps=8)
        page.wait_for_function('SceneRoom.getState().positions.gray_ball_1[2]>2.1');page.mouse.up()
        page.locator('#scene-live-play').click();assert page.evaluate('!SceneRoom.isRunning()')
        state=page.evaluate('SceneRoom.getState()');page.locator('[data-atlas-view=physics]').click();page.wait_for_timeout(200)
        assert page.evaluate('SceneRoom.getState().time')==state['time']
        page.locator('[data-atlas-view=motion]').click();assert page.evaluate('SceneRoom.getState().time')==state['time']
        page.locator('#scene-live-fullscreen').click();page.wait_for_function('!!document.fullscreenElement')
        assert page.locator('#scene-live-controls').is_visible() and page.locator('#scene-live-play').is_visible()
        page.locator('[data-scene-mode=view]').click();assert page.evaluate('SceneRoom.getState().mode')=='view'
        before=page.evaluate('SceneRoom.project("gray_ball_1")');r=page.locator('#scene-live-stage').bounding_box();x=r['x']+r['width']/2;y=r['y']+r['height']/2
        page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+55,y+20,steps=8);page.mouse.up();after=page.evaluate('SceneRoom.project("gray_ball_1")');assert math.hypot(after['x']-before['x'],after['y']-before['y'])>3
        page.locator('#scene-live-fullscreen').click();page.wait_for_function('!document.fullscreenElement');assert page.locator('.scene-foot #scene-live-controls').count()==1
        for id in ['12','13','10','07']:
            page.evaluate('(id)=>showWorld(id)',id);page.wait_for_function('(id)=>window.SceneRoom?.getState().scene===id',arg=id)
            assert page.locator('#scene-live-stage canvas').count()==1
        page.locator('#scene-live-reset').click();assert page.evaluate('SceneRoom.getState().oracle.count')==0
        page.locator('[data-room-mode=push]').click();page.wait_for_function('!!window.RoomDemo')
        wasm=page.evaluate('performance.getEntriesByType("resource").filter(r=>r.name.includes(".wasm")).length');assert wasm==1,wasm
        print('PASS: real push, lift/drop, rotate, pause/resume, fullscreen controls, fresh scene state and one shared WASM download.',flush=True)
        phone=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True);phone.on('pageerror',lambda e:errors.append(str(e)));phone.goto(args.url+'/#worlds')
        phone.locator('[data-atlas-view=motion]').tap();phone.wait_for_function('!!window.SceneRoom');phone.locator('#scene-live-reset').tap();phone.locator('#scene-live-stage').scroll_into_view_if_needed()
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
