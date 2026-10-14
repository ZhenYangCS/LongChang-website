"""Real pointer regressions for completed cold pushes, release position and walls."""
import argparse
import asyncio
import math
from playwright.async_api import async_playwright


async def check(url):
    errors = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--enable-unsafe-swiftshader'])
        page = await browser.new_page(viewport={'width':1366, 'height':900})
        page.on('pageerror', lambda error: errors.append(str(error)))
        await page.goto(url+'?scene=01#worlds')
        await page.locator('[data-atlas-view=motion]').click()
        await page.wait_for_function('window.SceneRoom?.getState().scene==="01"')
        await page.locator('#scene-live-stage').scroll_into_view_if_needed()
        point = await page.evaluate('SceneRoom.project("red_ball")')
        rect = await page.locator('#scene-live-stage').bounding_box()
        reference = ((point['x']-rect['x'])/rect['width'], (point['y']-rect['y'])/rect['height'])

        for native in [False, True]:
            for cancel in [False, True]:
                cold = await browser.new_page(viewport={'width':1366, 'height':900})
                cold.on('pageerror', lambda error: errors.append(str(error)))
                downloaded = asyncio.Event()
                async def wait_download(route):
                    await downloaded.wait()
                    await route.continue_()
                await cold.route('**/mujoco.wasm', wait_download)
                await cold.goto(url+('?scene=01#worlds' if native else ''), wait_until='networkidle')
                if native:
                    await cold.locator('[data-atlas-view=motion]').click()
                await cold.locator('[data-scene-mode=push]' if native else '[data-room-mode=push]').click()
                stage = cold.locator('#scene-live-stage' if native else '#room-stage')
                await stage.scroll_into_view_if_needed()
                box = await stage.bounding_box()
                u,v = reference if native else (.264,.695)
                x,y = box['x']+box['width']*u,box['y']+box['height']*v
                await cold.mouse.move(x,y)
                await cold.mouse.down()
                await cold.mouse.move(x+40,y,steps=4)
                await cold.mouse.up()
                if cancel:
                    await cold.locator('#scene-live-reset' if native else '#room-reset').click()
                downloaded.set()
                world = 'SceneRoom' if native else 'RoomDemo'
                await cold.wait_for_function(f'!!window.{world}', timeout=60000)
                if cancel:
                    await cold.wait_for_timeout(120)
                    assert await cold.evaluate(f'{world}.getState().lastPush') is None
                    assert await cold.evaluate(f'{world}.getState().time') == 0
                else:
                    state = await cold.evaluate(f'{world}.getState()')
                    assert state['lastPush']['body'] == ('red_ball' if native else 'blue_ball'), state
                    assert state['lastPush']['sequence'] == 1
                    assert math.hypot(*state['lastPush']['impulse']) > 0
                    await cold.wait_for_function(f'{world}.getState().time>.2')
                    assert await cold.evaluate(f'{world}.getState().lastPush.sequence') == 1
                await cold.close()
        print('PASS: a finished first push survives loading exactly once; reset cancels it in hero and scene player.', flush=True)

        # Every native body, with both a tap and a directional gesture.
        await page.locator('[data-scene-mode=push]').click()
        attempts = 0
        for n in range(1,16):
            scene = f'{n:02}'
            await page.evaluate('id=>showWorld(id)', scene)
            await page.wait_for_function('id=>window.SceneRoom?.getState().scene===id', arg=scene)
            await page.locator('#scene-live-stage').scroll_into_view_if_needed()
            names = await page.evaluate('Object.keys(SceneRoom.getState().positions)')
            for name in names:
                for dx in [0,40]:
                    await page.locator('#scene-live-reset').click()
                    before = await page.evaluate('SceneRoom.getState().positions')
                    point = await page.evaluate('name=>SceneRoom.project(name)', name)
                    await page.mouse.move(point['x'],point['y'])
                    await page.mouse.down()
                    await page.mouse.move(point['x']+dx,point['y'],steps=4)
                    await page.mouse.up()
                    pushed = await page.evaluate('SceneRoom.getState().lastPush')
                    assert pushed and pushed['body']==name and pushed['sequence']==1,(scene,name,dx,pushed)
                    assert math.hypot(*pushed['impulse'])>.01,(scene,name,pushed)
                    await page.wait_for_function('SceneRoom.getState().time>.2')
                    await page.evaluate('SceneRoom.pause()')
                    after = await page.evaluate('SceneRoom.getState().positions')
                    assert max(math.dist(before[key][:2],after[key][:2]) for key in names)>.001,(scene,name,dx)
                    attempts += 1
        print(f'PASS: {attempts} real tap/drag pushes across every body in all 15 scenes produce motion.', flush=True)

        await page.locator('[data-room-mode=push]').click()
        await page.wait_for_function('!!window.RoomDemo')
        await page.locator('#room-stage').scroll_into_view_if_needed()
        await page.locator('#room-reset').click()
        point = await page.evaluate('RoomDemo.project("blue_ball")')
        await page.mouse.move(point['x'],point['y']);await page.mouse.down()
        cdp = await page.context.new_cdp_session(page)
        await cdp.send('Input.dispatchMouseEvent', {'type':'mouseReleased','x':point['x']+45,'y':point['y'],'button':'left','clickCount':1})
        await page.mouse.up()  # Synchronize Playwright's button bookkeeping.
        pushed = await page.evaluate('RoomDemo.getState().lastPush')
        assert pushed['sequence']==1 and abs(pushed['impulse'][0])>.1,pushed
        print('PASS: a fast release uses its final position, even without a final pointermove.', flush=True)

        # Controlled near-wall state, exercising the same renderer and gesture code.
        await page.evaluate('''async()=>{
          RoomDemo.pause();SceneRoom.pause();
          const {createSceneSimulation}=await import('./assets/scene-physics.js'),{createRoom}=await import('./assets/room-world.js');
          const sim=await createSceneSimulation(await(await fetch('data/interactive-scenes/01.json')).json());
          const red=sim.bodies.red_ball;sim.data.qpos.set([5.89,0,.1],red.q);sim.mj.mj_forward(sim.model,sim.data);
          const stage=document.createElement('div');stage.id='push-wall-test';stage.style.cssText='position:fixed;z-index:9999;inset:30px auto auto 30px;width:800px;height:500px;background:white';document.body.append(stage);
          window.WallRoom=await createRoom(stage,()=>{},{simulation:sim});WallRoom.setMode('push');
        }''')
        point = await page.evaluate('WallRoom.project("red_ball")')
        target = await page.evaluate('WallRoom.project([7.5,0,.1])')
        await page.mouse.move(point['x'],point['y']);await page.mouse.down()
        await page.mouse.move(target['x'],target['y'],steps=5);await page.mouse.up()
        assert await page.evaluate('WallRoom.getState().lastPush.impulse[0]') > 0
        await page.evaluate('WallRoom.destroy();document.querySelector("#push-wall-test").remove()')
        print('PASS: an outward push near a wall keeps its intended direction.', flush=True)

        phone = await browser.new_page(viewport={'width':390,'height':844}, is_mobile=True, has_touch=True)
        phone.on('pageerror', lambda error: errors.append(str(error)))
        await phone.goto(url+'?scene=01#worlds')
        await phone.locator('[data-atlas-view=motion]').tap()
        await phone.wait_for_function('!!window.SceneRoom')
        await phone.locator('[data-scene-mode=push]').tap()
        await phone.locator('#scene-live-stage').scroll_into_view_if_needed()
        point = await phone.evaluate('SceneRoom.project("red_ball")')
        cdp = await phone.context.new_cdp_session(phone)
        await cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[point]})
        await cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':point['x']+35,'y':point['y']}]})
        await cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
        pushed = await phone.evaluate('SceneRoom.getState().lastPush')
        assert pushed and pushed['body']=='red_ball' and pushed['sequence']==1
        await browser.close()
    assert not errors,errors
    print('PASS: real touch push; no JavaScript errors.', flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8765/')
    asyncio.run(check(parser.parse_args().url))
