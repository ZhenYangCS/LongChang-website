"""Push moving bodies through real mouse/touch gestures without pausing them."""
import argparse
import math
from playwright.sync_api import sync_playwright


def repeat_push(page, api, name, *, touch=False, rate=4):
    page.evaluate("""({api,name,rate})=>{
      const world=window[api];world.reset();world.setMode('push');world.setSpeed(rate);
      const x=world.getState().positions[name][0];
      world.push(name,[api==='RoomDemo'?-4:(x<0?-4:4),0,0]);
    }""", dict(api=api,name=name,rate=rate))
    page.wait_for_function(f'{api}.getState().time>.18')
    aim=page.evaluate("""({api,name})=>{
      const world=window[api],position=world.getState().positions[name];
      const start=world.project(name),end=world.project([position[0]+1,position[1],position[2]]);
      return {start,dx:end.x-start.x,dy:end.y-start.y,time:world.getState().time};
    }""",dict(api=api,name=name))
    start=aim['start']
    if not touch:page.mouse.move(**start)
    page.wait_for_timeout(180)
    # If another body has moved onto the old aim point, follow the intended
    # ball to an exposed edge. Visible current objects must win over history.
    follow=page.evaluate("""({api,name,start})=>{
      const world=window[api],others=Object.keys(world.getState().positions).filter(n=>n!==name).map(n=>world.project(n));
      if(!others.some(p=>Math.hypot(p.x-start.x,p.y-start.y)<32))return null;
      const point=world.project(name);
      others.sort((a,b)=>Math.hypot(a.x-point.x,a.y-point.y)-Math.hypot(b.x-point.x,b.y-point.y));
      const nearest=others[0],distance=Math.hypot(point.x-nearest.x,point.y-nearest.y);
      if(distance<32&&distance>.01){point.x+=(point.x-nearest.x)/distance*16;point.y+=(point.y-nearest.y)/distance*16;}
      return point;
    }""",dict(api=api,name=name,start=start))
    if follow:start=follow
    end=dict(x=start['x']+aim['dx'],y=start['y']+aim['dy'])
    if touch:
        cdp=page.context.new_cdp_session(page)
        cdp.send('Input.dispatchTouchEvent',dict(type='touchStart',touchPoints=[start]))
        page.wait_for_timeout(60)
        cdp.send('Input.dispatchTouchEvent',dict(type='touchMove',touchPoints=[end]))
        cdp.send('Input.dispatchTouchEvent',dict(type='touchEnd',touchPoints=[]))
        cdp.detach()
    else:
        if follow:page.mouse.move(**start)
        page.mouse.down()
        page.wait_for_timeout(60)
        page.mouse.move(**end,steps=4)
        page.mouse.up()
    state=page.evaluate(f'{api}.getState()');pushed=state['lastPush']
    context=(api,state.get('scene'),name,rate,touch,pushed)
    assert pushed and pushed['body']==name and pushed['sequence']==2,context
    # One world-unit eastward pointer displacement must stay eastward even if
    # the ball has moved since its clicked position was displayed.
    # Browser input coordinates have subpixel rounding.
    assert math.isclose(pushed['impulse'][0],3,abs_tol=.02),context
    assert abs(pushed['impulse'][1])<.02 and pushed['impulse'][2]==0,context
    assert pushed['time']>aim['time'],context
    if state.get('scene')=='15':
        assert math.isclose(state['oracle']['quietUntil'],pushed['time']+10,abs_tol=1e-8)
    if state.get('scene')=='14' and name=='red_ball':
        assert len(state['oracle']['pending'])==2,context
    page.evaluate(f'{api}.pause()')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8765/');args=parser.parse_args()
    errors=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(args=['--no-sandbox','--enable-unsafe-swiftshader'])
        page=browser.new_page(viewport={'width':1440,'height':1000},reduced_motion='reduce')
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(args.url,wait_until='domcontentloaded')
        page.locator('[data-room-mode=push]').click();page.wait_for_function('!!window.RoomDemo')
        page.locator('#room-stage').scroll_into_view_if_needed()
        for rate in [1,4]:
            for name in ['red_ball','blue_ball']:repeat_push(page,'RoomDemo',name,rate=rate)
        print('PASS: both homepage balls can be pushed again while moving at 1× and 4×.',flush=True)
        page.evaluate('showWorld("01")');page.locator('[data-atlas-view=motion]').click()
        page.locator('[data-scene-mode=push]').click()
        attempts=0
        for n in range(1,16):
            scene=f'{n:02}'
            page.evaluate('id=>showWorld(id)',scene)
            page.wait_for_function('id=>window.SceneRoom?.getState().scene===id',arg=scene)
            page.locator('#scene-live-stage').scroll_into_view_if_needed()
            names=page.evaluate('Object.keys(SceneRoom.getState().positions)')
            for name in names:
                repeat_push(page,'SceneRoom',name);attempts+=1
            print(f'PASS: Scene {scene}, {len(names)} moving bodies.',flush=True)
        page.locator('[data-evo-view=experiment]').click()
        for scene in ['generate','mutate','compose']:
            page.locator(f'#evo-tab-{scene}').click()
            page.wait_for_function('id=>LongChangEvolution.current()?.getState().scene===id',arg=scene)
            page.evaluate('window.EvolvedRoom=LongChangEvolution.current()')
            page.locator('#evo-stage').scroll_into_view_if_needed()
            for name in page.evaluate('Object.keys(EvolvedRoom.getState().positions)'):
                repeat_push(page,'EvolvedRoom',name)
        print('PASS: all three evolved scenes accept repeated moving-body pushes.',flush=True)
        page.close()
        phone=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,reduced_motion='reduce')
        phone.on('pageerror',lambda error:errors.append(str(error)))
        phone.goto(args.url,wait_until='domcontentloaded')
        phone.locator('[data-room-mode=push]').tap();phone.wait_for_function('!!window.RoomDemo')
        phone.locator('#room-stage').scroll_into_view_if_needed()
        repeat_push(phone,'RoomDemo','blue_ball',touch=True)
        phone.locator('[data-atlas-view=motion]').tap();phone.locator('[data-scene-mode=push]').tap()
        for n in range(1,16):
            scene=f'{n:02}'
            phone.evaluate('id=>showWorld(id)',scene)
            phone.wait_for_function('id=>window.SceneRoom?.getState().scene===id',arg=scene)
            phone.locator('#scene-live-stage').scroll_into_view_if_needed()
            name=phone.evaluate('Object.keys(SceneRoom.getState().positions)[0]')
            repeat_push(phone,'SceneRoom',name,touch=True)
        browser.close()
    assert not errors,errors
    print(f'PASS: {attempts} moving bodies across all 15 scenes, homepage, evolved scenes, and touch in all 15 scenes; correct impulse direction, live time and scene 14/15 timers.',flush=True)


if __name__=='__main__':main()
