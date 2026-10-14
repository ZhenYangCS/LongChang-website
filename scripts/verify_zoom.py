"""Exercise real pointer, wheel and touch paths, without changing the movie clock."""
import argparse
from playwright.sync_api import sync_playwright


def box(page,selector):
    return page.locator(selector).bounding_box()


def scale(page):
    return float(page.locator('#atlas-physics-view .physics-video-frame').get_attribute('data-zoom'))


def drag(page,x,y,dx,dy):
    page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+dx,y+dy,steps=8);page.mouse.up()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8765');args=parser.parse_args()
    errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader'])
        page=browser.new_page(viewport={'width':1366,'height':768});page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(args.url+'/#worlds');page.wait_for_load_state('networkidle')
        assert scale(page)>1 and page.locator('#atlas-physics-view .physics-video-frame').get_attribute('data-framing')=='detail'
        while scale(page)>2.5:page.locator('#scene-zoom-out').click()
        assert not page.locator('#physics-video').get_attribute('src'),'Zooming a poster should not download a movie'
        frame=box(page,'#atlas-physics-view .physics-video-frame');page.mouse.move(frame['x']+frame['width']/2,frame['y']+frame['height']/2)
        zoom_before=scale(page);scroll_before=page.evaluate('scrollY')
        page.mouse.wheel(0,160);page.wait_for_function('(y)=>scrollY>y+40',arg=scroll_before)
        assert scale(page)==zoom_before,'Page scrolling must not zoom the scene'
        page.evaluate('document.querySelector("#worlds").scrollIntoView({behavior:"instant",block:"start"})')
        frame=box(page,'#atlas-physics-view .physics-video-frame');x=frame['x']+frame['width']/2+15;y=frame['y']+frame['height']/2+8
        page.locator('#scene-zoom-in').click();page.locator('#scene-zoom-in').click()
        before=box(page,'#atlas-physics-view .physics-media');point=((x-before['x'])/before['width'],(y-before['y'])/before['height'])
        page.mouse.move(x,y);page.keyboard.down('Control');page.mouse.wheel(0,-100);page.wait_for_timeout(120);page.keyboard.up('Control')
        after=box(page,'#atlas-physics-view .physics-media');new_point=((x-after['x'])/after['width'],(y-after['y'])/after['height'])
        assert max(abs(a-b) for a,b in zip(point,new_point))<.002,(point,new_point)
        zoom_before=scale(page);scroll_before=page.evaluate('scrollY')
        page.keyboard.down('Meta');page.mouse.wheel(0,-60);page.wait_for_timeout(120);page.keyboard.up('Meta')
        assert scale(page)>zoom_before and abs(page.evaluate('scrollY')-scroll_before)<1
        after=box(page,'#atlas-physics-view .physics-media')
        before=after;drag(page,x,y,-70,-25);after=box(page,'#atlas-physics-view .physics-media')
        assert abs(after['x']-before['x']+70)<1 and abs(after['y']-before['y']+25)<1
        # Both opposite corners of the original room remain reachable.
        drag(page,x,y,3000,3000);after=box(page,'#atlas-physics-view .physics-media')
        assert abs(after['x']-frame['x'])<1 and abs(after['y']-frame['y'])<1
        drag(page,x,y,-3000,-3000);after=box(page,'#atlas-physics-view .physics-media')
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
        frame=box(page,'#atlas-physics-view .physics-video-frame');page.mouse.move(frame['x']+frame['width']/2,frame['y']+frame['height']/2)
        zoom_before=scale(page);page.mouse.wheel(0,-80);page.wait_for_timeout(120)
        assert scale(page)>zoom_before and page.locator('#scene-zoom-hint').text_content().startswith('Scroll')
        current=page.locator('#physics-video').evaluate('v=>({time:v.currentTime,src:v.currentSrc,paused:v.paused,rate:v.playbackRate})')
        assert current['paused'] and current['rate']==2 and current['src']==state['src'] and abs(current['time']-state['time'])<.02
        page.locator('#physics-play').click();page.wait_for_timeout(250)
        assert page.locator('#physics-video').evaluate('v=>v.currentTime')>state['time']+.2
        page.locator('#physics-fullscreen').click();page.wait_for_function('!document.fullscreenElement')
        page.locator('#atlas-physics-view .physics-video-frame').focus();page.keyboard.press('0');assert scale(page)==1
        page.locator('#physics-view').click();page.locator('#atlas-physics-view .physics-video-frame').focus();page.keyboard.press('+');assert scale(page)>2
        page.locator('#scene-tab-10').click();assert scale(page)>1
        page.locator('#physics-play').click()
        print('PASS: zoom preserves source, time, pause state and playback rate; fullscreen controls, keyboard and scene reset work.',flush=True)

        # Native rooms use the same page/fullscreen distinction in every mode.
        for api,activate,stage,ready in [
            ('RoomDemo','[data-room-mode=drag]','#room-stage','!!window.RoomDemo'),
            ('SceneRoom','[data-atlas-view=motion]','#scene-live-stage','!!window.SceneRoom')]:
            page.locator(activate).click();page.wait_for_function(ready,timeout=60000)
            page.evaluate(f'{api}.pause()');page.locator(stage).scroll_into_view_if_needed()
            span=f'(()=>{{const a={api}.project([0,0,0]),b={api}.project([1,0,0]);return Math.hypot(a.x-b.x,a.y-b.y);}})()'
            frame=box(page,stage);page.mouse.move(frame['x']+frame['width']/2,frame['y']+frame['height']/2)
            zoom_before=page.evaluate(span);scroll_before=page.evaluate('scrollY')
            page.mouse.wheel(0,150);page.wait_for_function('(y)=>scrollY>y+40',arg=scroll_before)
            assert abs(page.evaluate(span)-zoom_before)<.01,(api,'ordinary scrolling changed zoom')
            for modifier in ['Control','Meta']:
                page.locator(stage).scroll_into_view_if_needed();frame=box(page,stage);page.mouse.move(frame['x']+frame['width']/2,frame['y']+frame['height']/2)
                zoom_before=page.evaluate(span);scroll_before=page.evaluate('scrollY')
                page.keyboard.down(modifier);page.mouse.wheel(0,-70);page.wait_for_timeout(150);page.keyboard.up(modifier)
                assert page.evaluate(span)>zoom_before,(api,modifier)
                assert abs(page.evaluate('scrollY')-scroll_before)<1,(api,'modified wheel scrolled the page')
        page.locator('[data-scene-mode=view]').click();page.locator('#scene-live-fullscreen').click();page.wait_for_function('!!document.fullscreenElement')
        frame=box(page,'#scene-live-stage');page.mouse.move(frame['x']+frame['width']/2,frame['y']+frame['height']/2)
        zoom_before=page.evaluate(span);page.mouse.wheel(0,-70);page.wait_for_timeout(150)
        assert page.evaluate(span)>zoom_before
        assert 'Ctrl' not in page.locator('#scene-live-hint').text_content()
        page.locator('#scene-live-fullscreen').click();page.wait_for_function('!document.fullscreenElement')
        assert 'Ctrl' in page.locator('#scene-live-hint').text_content()
        print('PASS: ordinary wheels scroll the page; Ctrl/Command zoom both recorded and native rooms; fullscreen allows direct wheel zoom.',flush=True)

        phone=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
        phone.on('pageerror',lambda e:errors.append(str(e)));phone.goto(args.url+'/#worlds');phone.wait_for_function('Number(document.querySelector("#atlas-physics-view .physics-video-frame").dataset.zoom)>1')
        while scale(phone)>2.1:phone.locator('#scene-zoom-out').tap()
        before_pinch=scale(phone)
        phone.locator('#atlas-physics-view .physics-video-frame').scroll_into_view_if_needed();frame=box(phone,'#atlas-physics-view .physics-video-frame')
        x=frame['x']+frame['width']/2;y=frame['y']+frame['height']/2
        cdp=phone.context.new_cdp_session(phone)
        def touch(kind,points):cdp.send('Input.dispatchTouchEvent',{'type':kind,'touchPoints':points})
        def pair(d):return [{'id':1,'x':x-d,'y':y},{'id':2,'x':x+d,'y':y}]
        touch('touchStart',pair(25))
        for d in [30,35,40,45,50]:touch('touchMove',pair(d))
        touch('touchEnd',[]);assert abs(scale(phone)/before_pinch-2)<.1,scale(phone)
        before=box(phone,'#atlas-physics-view .physics-media');touch('touchStart',[{'id':1,'x':x,'y':y}])
        for d in [10,20,30,40]:touch('touchMove',[{'id':1,'x':x-d,'y':y+10}])
        touch('touchCancel',[]);after=box(phone,'#atlas-physics-view .physics-media')
        assert after['x']<before['x']-35
        assert not phone.locator('#atlas-physics-view .physics-video-frame').evaluate('e=>e.classList.contains("is-panning")')
        phone.locator('#scene-zoom-reset').tap();assert scale(phone)==1
        assert phone.locator('#atlas-physics-view .physics-video-frame').evaluate('e=>getComputedStyle(e).touchAction')!='none'
        assert phone.evaluate('document.documentElement.scrollWidth')==390
        browser.close()
    assert not errors,errors
    print('PASS: real two-finger pinch, single-finger pan, touch cancellation and mobile reset; no JavaScript errors.')


if __name__=='__main__':main()
