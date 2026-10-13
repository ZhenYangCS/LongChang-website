"""Regress cold-start gestures, small targets and interrupted room interactions."""
import argparse
import asyncio

from playwright.async_api import async_playwright


async def check(url):
    errors = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, args=['--no-sandbox', '--enable-unsafe-swiftshader'])

        async def cold_page(release_early=False):
            page = await browser.new_page(viewport={'width':1366, 'height':900})
            page.on('pageerror', lambda e: errors.append(str(e)))

            async def delayed_download(route):
                await asyncio.sleep(.8)
                await route.continue_()

            await page.route('**/mujoco.wasm', delayed_download)
            await page.goto(url, wait_until='networkidle')
            assert not await page.evaluate('performance.getEntriesByType("resource").some(r=>r.name.endsWith(".wasm"))')
            await page.locator('#room-stage').scroll_into_view_if_needed()
            box = await page.locator('#room-stage').bounding_box()
            # The blue ball in the Figure 1 poster, before a canvas exists.
            x, y = box['x'] + box['width']*.264, box['y'] + box['height']*.695
            await page.mouse.move(x, y)
            await page.mouse.down()
            await page.mouse.move(x, y-45, steps=5)
            assert await page.locator('#room-stage').get_attribute('aria-busy') == 'true'
            if release_early:
                await page.mouse.up()
            await page.wait_for_function('!!window.RoomDemo', timeout=60000)
            if release_early:
                await page.wait_for_timeout(200)
                assert await page.evaluate('RoomDemo.getState().time') == 0
                assert not await page.locator('#room-stage .room-grab-marker').is_visible()
            else:
                await page.wait_for_function('RoomDemo.getState().positions.blue_ball[2]>.9')
                assert await page.evaluate('RoomDemo.getState().selected') == 'blue_ball'
                await page.mouse.up()
            return page

        page = await cold_page()
        cancelled = await cold_page(release_early=True)
        await cancelled.close()
        for offset in [0, 12, 16]:
            await page.evaluate('RoomDemo.reset()')
            point = await page.evaluate('RoomDemo.project("blue_ball")')
            await page.mouse.move(point['x']+offset, point['y'])
            await page.mouse.down()
            await page.mouse.move(point['x']+offset, point['y']-45, steps=5)
            await page.wait_for_function('RoomDemo.getState().positions.blue_ball[2]>.9')
            assert await page.locator('#room-stage .room-grab-marker.is-held').is_visible()
            await page.mouse.up()
        # The hand settles at the height under the pointer, without surface spin.
        await page.evaluate('RoomDemo.reset()')
        point = await page.evaluate('RoomDemo.project("blue_ball")')
        target = await page.evaluate('RoomDemo.project([-2,-1.9,1.6])')
        await page.mouse.move(point['x'], point['y'])
        await page.mouse.down()
        await page.mouse.move(target['x'], target['y'], steps=6)
        await page.wait_for_function('Math.abs(RoomDemo.getState().positions.blue_ball[2]-1.6)<.06')
        await page.wait_for_timeout(200)
        assert abs(await page.evaluate('RoomDemo.getState().positions.blue_ball[2]')-1.6) < .04
        await page.evaluate('window.dispatchEvent(new Event("blur"))')
        await page.mouse.up()
        assert not await page.locator('#room-stage .room-grab-marker').is_visible()
        await page.wait_for_function('RoomDemo.getState().positions.blue_ball[2]<.6')
        print('PASS: first held gesture survives loading; released gestures stay cancelled; small targets and stable lift/drop.', flush=True)

        await page.locator('[data-atlas-view=motion]').click()
        await page.locator('[data-scene-mode=drag]').click()
        for i in range(1, 16):
            scene = f'{i:02}'
            await page.evaluate('id=>showWorld(id)', scene)
            await page.wait_for_function('id=>window.SceneRoom?.getState().scene===id', arg=scene, timeout=60000)
            await page.locator('#scene-live-reset').click()
            await page.locator('#scene-live-stage').scroll_into_view_if_needed()
            state = await page.evaluate('SceneRoom.getState()')
            name = min(state['positions'], key=lambda name: state['positions'][name][2])
            point = await page.evaluate('name=>SceneRoom.project(name)', name)
            # Some collision scenes place balls only a few pixels apart.
            # Aim at the centre here; target margins are checked separately.
            await page.mouse.move(point['x'], point['y'])
            await page.mouse.down()
            await page.mouse.move(point['x'], point['y']-20, steps=4)
            assert await page.evaluate('SceneRoom.getState().oracle.held') == name, scene
            await page.mouse.up()
            assert await page.evaluate('SceneRoom.getState().oracle.held') is None, scene
            assert await page.locator('#scene-live-stage canvas').count() == 1
        print('PASS: grab/release works in all 15 scenes after switching; no duplicated canvases.', flush=True)

        # Re-grab a moving ball at 4x, using the position just displayed rather
        # than resetting to a stationary target before every attempt.
        await page.evaluate('showWorld("07")')
        await page.wait_for_function('window.SceneRoom?.getState().scene==="07"')
        await page.locator('#scene-live-reset').click()
        await page.locator('#scene-live-stage').scroll_into_view_if_needed()
        for attempt in range(30):
            point = await page.evaluate('SceneRoom.project("gray_ball_1")')
            await page.mouse.move(point['x'], point['y'])
            await page.wait_for_timeout(35)
            await page.mouse.down()
            assert await page.evaluate('SceneRoom.getState().oracle.held') == 'gray_ball_1', attempt
            await page.mouse.move(point['x']+(10 if attempt%2 else -10), point['y']-15, steps=4)
            await page.wait_for_timeout(65)
            await page.mouse.up()
            await page.wait_for_timeout(65)
        await page.evaluate('SceneRoom.pause()')
        print('PASS: 30 consecutive moving-ball re-grabs at 4x.', flush=True)

        phone = await browser.new_page(viewport={'width':390, 'height':844}, is_mobile=True, has_touch=True)
        phone.on('pageerror', lambda e: errors.append(str(e)))
        await phone.goto(url)
        await phone.locator('[data-room-mode=drag]').tap()
        await phone.wait_for_function('!!window.RoomDemo', timeout=60000)
        await phone.locator('#room-stage').scroll_into_view_if_needed()
        point = await phone.evaluate('RoomDemo.project("blue_ball")')
        cdp = await phone.context.new_cdp_session(phone)
        await cdp.send('Input.dispatchTouchEvent', {'type':'touchStart', 'touchPoints':[{'x':point['x']-20, 'y':point['y']}]})
        await cdp.send('Input.dispatchTouchEvent', {'type':'touchMove', 'touchPoints':[{'x':point['x']-20, 'y':point['y']-38}]})
        await phone.wait_for_function('RoomDemo.getState().positions.blue_ball[2]>.9')
        await cdp.send('Input.dispatchTouchEvent', {'type':'touchEnd', 'touchPoints':[]})
        assert await phone.evaluate('document.documentElement.scrollWidth<=innerWidth')
        print('PASS: touch targets allow a finger-width margin; no horizontal overflow.', flush=True)
        await browser.close()
    assert not errors, errors


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8765/')
    asyncio.run(check(parser.parse_args().url))
