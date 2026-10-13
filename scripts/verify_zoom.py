"""Exercise real pointer, wheel and touch paths, without changing the movie clock."""
import argparse
from playwright.sync_api import sync_playwright


def box(page,selector):
    return page.locator(selector).bounding_box()


def scale(page):
    return float(page.locator('.physics-video-frame').get_attribute('data-zoom'))


def drag(page,x,y,dx,dy):
    page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+dx,y+dy,steps=8);page.mouse.up()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8765');args=parser.parse_args()
    errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader'])
        page=browser.new_page(viewport={'width':1366,'height':768});page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(args.url+'/#worlds');page.wait_for_load_state('networkidle')
        assert scale(page)==1
        page.locator('#physics-view').click();assert scale(page)==2
        assert not page.locator('#physics-video').get_attribute('src'),'Zooming a poster should not download a movie'
        frame=box(page,'.physics-video-frame');x=frame['x']+frame['width']/2+15;y=frame['y']+frame['height']/2+8
        page.locator('#scene-zoom-in').click();page.locator('#scene-zoom-in').click()
        before=box(page,'.physics-media');point=((x-before['x'])/before['width'],(y-before['y'])/before['height'])
        page.mouse.move(x,y);page.mouse.wheel(0,-100);page.wait_for_timeout(120)
        after=box(page,'.physics-media');new_point=((x-after['x'])/after['width'],(y-after['y'])/after['height'])
        assert max(abs(a-b) for a,b in zip(point,new_point))<.002,(point,new_point)
        before=after;drag(page,x,y,-70,-25);after=box(page,'.physics-media')
        assert abs(after['x']-before['x']+70)<1 and abs(after['y']-before['y']+25)<1
        # Both opposite corners of the original room remain reachable.
        drag(page,x,y,3000,3000);after=box(page,'.physics-media')
        assert abs(after['x']-frame['x'])<1 and abs(after['y']-frame['y'])<1
        drag(page,x,y,-3000,-3000);after=box(page,'.physics-media')
        assert abs(after['x']+after['width']-frame['x']-frame['width'])<1
        assert abs(after['y']+after['height']-frame['y']-frame['height'])<1
        page.mouse.dblclick(x,y);assert scale(page)==1
        print('PASS: zoom stays under the cursor; dragging reaches every room corner; double-click restores the whole room.',flush=True)

        page.locator('#physics-play').click();page.wait_for_function('!document.querySelector("#physics-video").paused')
        page.locator('#physics-play').click();page.locator('#physics-speed').select_option('2')
        page.locator('#physics-progress').evaluate('e=>{e.value=550;e.dispatchEvent(new Event("input"));}')
        page.wait_for_function('!document.querySelector("#physics-video").seeking')
        state=page.locator('#physics-video').evaluate('v=>({time:v.currentTime,src:v.currentSrc})')
        page.locator('#physics-view').click();page.locator('#scene-zoom-in').click()
        page.locator('#physics-fullscreen').click();page.wait_for_function('!!document.fullscreenElement')
        assert page.locator('#physics-play').is_visible() and page.locator('#physics-speed').is_visible()
        page.locator('#scene-zoom-out').click()
        current=page.locator('#physics-video').evaluate('v=>({time:v.currentTime,src:v.currentSrc,paused:v.paused,rate:v.playbackRate})')
        assert current['paused'] and current['rate']==2 and current['src']==state['src'] and abs(current['time']-state['time'])<.02
        page.locator('#physics-play').click();page.wait_for_timeout(250)
        assert page.locator('#physics-video').evaluate('v=>v.currentTime')>state['time']+.2
        page.locator('#physics-fullscreen').click();page.wait_for_function('!document.fullscreenElement')
        page.locator('.physics-video-frame').focus();page.keyboard.press('0');assert scale(page)==1
        page.locator('#physics-view').click();page.locator('.physics-video-frame').focus();page.keyboard.press('+');assert scale(page)>2
        page.locator('#scene-tab-10').click();assert scale(page)==1
        page.locator('#physics-play').click()
        print('PASS: zoom preserves source, time, pause state and playback rate; fullscreen controls, keyboard and scene reset work.',flush=True)

        phone=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
        phone.on('pageerror',lambda e:errors.append(str(e)));phone.goto(args.url+'/#worlds');phone.locator('#physics-view').tap()
        phone.locator('.physics-video-frame').scroll_into_view_if_needed();frame=box(phone,'.physics-video-frame')
        x=frame['x']+frame['width']/2;y=frame['y']+frame['height']/2
        cdp=phone.context.new_cdp_session(phone)
        def touch(kind,points):cdp.send('Input.dispatchTouchEvent',{'type':kind,'touchPoints':points})
        def pair(d):return [{'id':1,'x':x-d,'y':y},{'id':2,'x':x+d,'y':y}]
        touch('touchStart',pair(25))
        for d in [30,35,40,45,50]:touch('touchMove',pair(d))
        touch('touchEnd',[]);assert 3.8<scale(phone)<4.2,scale(phone)
        before=box(phone,'.physics-media');touch('touchStart',[{'id':1,'x':x,'y':y}])
        for d in [10,20,30,40]:touch('touchMove',[{'id':1,'x':x-d,'y':y+10}])
        touch('touchCancel',[]);after=box(phone,'.physics-media')
        assert after['x']<before['x']-35
        assert not phone.locator('.physics-video-frame').evaluate('e=>e.classList.contains("is-panning")')
        phone.locator('#scene-zoom-reset').tap();assert scale(phone)==1
        assert phone.locator('.physics-video-frame').evaluate('e=>getComputedStyle(e).touchAction')!='none'
        assert phone.evaluate('document.documentElement.scrollWidth')==390
        browser.close()
    assert not errors,errors
    print('PASS: real two-finger pinch, single-finger pan, touch cancellation and mobile reset; no JavaScript errors.')


if __name__=='__main__':main()
