"""Test direct gestures against the model's mathematical outcomes."""
import argparse,math
from playwright.sync_api import sync_playwright

def center(page):
    box=page.locator('#atlas-canvas .model-hit').first.bounding_box()
    return box['x']+box['width']/2,box['y']+box['height']/2

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8765');args=parser.parse_args();errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1366,'height':768});page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(args.url+'/#worlds');page.locator('[data-atlas-view=physics]').click();page.locator('#demo-explanation').scroll_into_view_if_needed()
        def choose(id):page.evaluate('(id)=>showWorld(id)',id);page.locator('#atlas-reset').click()
        def start(dx,dy):
            x,y=center(page);page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+dx,y+dy,steps=12)
            return x+dx,y+dy
        choose('07');lift=page.locator('#atlas-canvas').evaluate('s=>Math.abs(s.getScreenCTM().d)*62*.5');x,y=start(0,-lift)
        state=page.evaluate('LongChangAtlas.getState()');assert state['value']>2 and not state['playing']
        assert abs(center(page)[1]-y)<4,'The held ball should follow the pointer vertically'
        expected=f"Red {state['value']*.81:.2f} · Blue {state['value']*.0225:.3f}"
        assert page.locator('#atlas-value').text_content()==expected
        page.mouse.up();page.wait_for_function('LongChangAtlas.getState().time>.15')
        choose('05');start(-60,-30);assert float(page.locator('#atlas-parameter').input_value())<2.5
        assert 'brake off' in page.locator('#atlas-state-label').text_content();page.mouse.up()
        choose('08');start(70,35);impulse=float(page.locator('#atlas-parameter').input_value());assert impulse>3
        speed=2*impulse/(1+math.sqrt(1+4*(impulse/2.2)**2))
        assert page.locator('#atlas-value').text_content().startswith(f'{speed:.3f}') and speed<2.2;page.mouse.up()
        choose('06');start(60,-30);assert page.locator('#atlas-parameter').input_value()=='90';page.mouse.up()
        choose('04');point=page.locator('#atlas-canvas').evaluate('s=>{const p=new DOMPoint(232.5,95).matrixTransform(s.getScreenCTM());return {x:p.x,y:p.y};}')
        page.mouse.click(point['x'],point['y']);assert page.locator('#atlas-parameter').input_value()=='4.5'
        choose('07');start(0,-20);page.keyboard.press('Escape')
        assert page.locator('#atlas-parameter').input_value()=='2' and not page.evaluate('LongChangAtlas.getState().playing');page.mouse.up()
        choose('07');start(0,-20);page.evaluate('window.dispatchEvent(new Event("blur"))')
        assert page.locator('#atlas-parameter').input_value()=='2' and not page.evaluate('LongChangAtlas.getState().playing');page.mouse.up()
        assert not page.evaluate('window.SceneRoom || document.querySelector("#physics-video").hasAttribute("src")')
        page.locator('#analysis-fullscreen').click();page.wait_for_function('!!document.fullscreenElement');page.locator('#atlas-reset').click();start(0,-35)
        assert float(page.locator('#atlas-parameter').input_value())>2;page.mouse.up();page.locator('#analysis-fullscreen').click();page.wait_for_function('!document.fullscreenElement')
        choose('12');x,y=center(page);page.mouse.click(x,y);page.wait_for_function('LongChangAtlas.getState().time>.2')
        # Other parts of the page can warm their own runtime on pointer entry.
        # The model must never activate the native scene or its recorded video.
        assert not page.evaluate('window.SceneRoom || document.querySelector("#physics-video").hasAttribute("src")')
        phone=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True);phone.on('pageerror',lambda e:errors.append(str(e)))
        phone.goto(args.url+'/#worlds');phone.locator('[data-atlas-view=physics]').tap();phone.locator('#demo-explanation').scroll_into_view_if_needed();phone.locator('#atlas-reset').tap();phone.locator('#atlas-canvas').scroll_into_view_if_needed()
        x,y=center(phone);x+=20;cdp=phone.context.new_cdp_session(phone)
        cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x,'y':y}]})
        for step in [5,10,15,20]:cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x,'y':y-step}]})
        assert float(phone.locator('#atlas-parameter').input_value())>2
        cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]});phone.wait_for_function('LongChangAtlas.getState().time>.1')
        assert phone.evaluate('document.documentElement.scrollWidth<=innerWidth')
        browser.close()
    assert not errors,errors
    print('PASS: mouse and touch lift, rebound prediction, braking threshold, impulse response, aiming, phase selection, cancellation, fullscreen scaling and replay; model controls stay independent of scene physics and video.')

if __name__=='__main__':main()
