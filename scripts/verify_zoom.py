"""Check real wheel/pinch input in Try it and preserve fixed Demo cameras."""
import argparse
from playwright.sync_api import sync_playwright


def span_script(api):
    return f'''(() => {{
      const a = {api}.project([0, 0, 1]), b = {api}.project([1, 0, 1]);
      return Math.hypot(a.x - b.x, a.y - b.y);
    }})()'''


def center(page, stage):
    page.locator(stage).scroll_into_view_if_needed()
    box = page.locator(stage).bounding_box()
    return box['x'] + box['width'] / 2, box['y'] + box['height'] / 2


def wheel(page, api, stage, delta=-80, modifier=None):
    x, y = center(page, stage)
    page.mouse.move(x, y)
    span = span_script(api)
    before, scroll = page.evaluate(span), page.evaluate('scrollY')
    state = page.evaluate(f'{api}.getState()')
    if modifier:
        page.keyboard.down(modifier)
    try:
        page.mouse.wheel(0, delta)
        comparison = '>' if delta < 0 else '<'
        page.wait_for_function(f'(before) => {span} {comparison} before', arg=before)
    finally:
        if modifier:
            page.keyboard.up(modifier)
    assert abs(page.evaluate('scrollY') - scroll) < 1, 'Zoom must not scroll the page'
    assert page.evaluate(f'{api}.getState()') == state, 'Camera zoom must not change physics'
    assert page.evaluate(f'!{api}.isRunning()'), 'Zoom must not start physics'


def controls(page, api, stage, mode):
    x, y = center(page, stage)
    span = span_script(api)
    toggle = page.locator(stage + ' [data-room-wheel]')
    assert toggle.get_attribute('aria-checked') == 'false'
    before, scroll = page.evaluate(span), page.evaluate('scrollY')
    page.mouse.move(x, y)
    page.mouse.wheel(0, -120)
    page.wait_for_function('(y) => scrollY < y - 40', arg=scroll)
    assert abs(page.evaluate(span) - before) < .01, (mode, 'Wheel zoom Off must allow page scrolling')
    modifier = 'Control'
    wheel(page, api, stage, modifier=modifier)
    wheel(page, api, stage, delta=80, modifier=modifier)
    state = page.evaluate(f'{api}.getState()')
    toggle.press('Enter')
    assert toggle.get_attribute('aria-checked') == 'true'
    assert toggle.inner_text() == 'Wheel zoom\nOn'
    assert page.evaluate(f'{api}.getState()') == state
    wheel(page, api, stage)
    wheel(page, api, stage, delta=80)
    toggle.press('Space')
    assert toggle.get_attribute('aria-checked') == 'false'
    fit = page.locator(stage + ' [data-room-zoom=fit]')
    fit.click()
    before = page.evaluate(span)
    position = page.evaluate(f'{api}.project([0, 0, 1])')
    state = page.evaluate(f'{api}.getState()')
    page.locator(stage + ' [data-room-zoom=in]').press('Enter')
    assert abs(page.evaluate(span) / before - 1.25) < .001
    focus = page.evaluate(f'''() => {{
      const positions = Object.values({api}.getState().positions);
      return {api}.project([0, 1, 2].map(k => positions.reduce((s, p) => s + p[k], 0) / positions.length));
    }}''')
    box = page.locator(stage).bounding_box()
    assert abs(focus['x'] - box['x'] - box['width'] / 2) < 1
    assert abs(focus['y'] - box['y'] - box['height'] / 2) < 1
    page.locator(stage + ' [data-room-zoom=out]').click()
    assert abs(page.evaluate(span) - before) < .01
    # Cursor-based zoom shifts the target as well as changing the scale.
    wheel(page, api, stage, modifier=modifier)
    fit.click()
    assert abs(page.evaluate(span) - before) < .01
    restored = page.evaluate(f'{api}.project([0, 0, 1])')
    assert all(abs(restored[k] - position[k]) < .01 for k in ['x', 'y'])
    assert page.evaluate(f'{api}.getState()') == state, 'Fit must not reset physics'
    assert page.locator(stage + ' .room-view-tools').count() == 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8765')
    args = parser.parse_args()
    url = args.url.rstrip('/') + '/'
    errors, bad = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(args=['--no-sandbox', '--enable-unsafe-swiftshader'])
        page = browser.new_page(viewport={'width':1366, 'height':900}, reduced_motion='reduce')
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('response', lambda response: bad.append((response.status, response.url)) if response.status >= 400 else None)
        page.goto(url + '#worlds')
        assert page.locator('#physics-view,.scene-zoom-tools').count() == 0
        page.locator('[data-atlas-view=motion]').click()
        for number in range(1, 16):
            scene = f'{number:02}'
            page.evaluate('(id) => showWorld(id)', scene)
            page.wait_for_function('(id) => window.SceneRoom?.getState().scene === id', arg=scene, timeout=60000)
            for mode in ['drag', 'push', 'view']:
                page.locator(f'[data-scene-mode={mode}]').click()
                controls(page, 'SceneRoom', '#scene-live-stage', mode)
            assert 'scroll to zoom' in page.locator('#scene-live-hint').inner_text()
        print('PASS: all 15 scenes support the Wheel zoom switch, page scrolling when Off, and zoom/Fit buttons in every tool mode; physics stays paused.', flush=True)

        for modifier in ['Control', 'Meta']:
            wheel(page, 'SceneRoom', '#scene-live-stage', modifier=modifier)
        page.locator('#scene-live-fullscreen').click()
        page.wait_for_function('!!document.fullscreenElement')
        page.locator('[data-scene-mode=drag]').click()
        assert page.locator('#scene-live-stage [data-room-wheel]').is_disabled()
        assert page.locator('#scene-live-stage [data-room-wheel]').get_attribute('aria-checked') == 'true'
        wheel(page, 'SceneRoom', '#scene-live-stage')
        page.locator('#scene-live-fullscreen').click()
        page.wait_for_function('!document.fullscreenElement')
        assert page.locator('#scene-live-stage [data-room-wheel]').is_enabled()
        assert page.locator('#scene-live-stage [data-room-wheel]').get_attribute('aria-checked') == 'false'
        page.mouse.move(2, 400)
        old_scroll = page.evaluate('scrollY')
        page.mouse.wheel(0, 180)
        page.wait_for_function('(y) => scrollY > y + 40', arg=old_scroll)

        evo = 'LongChangEvolution.current()'
        page.locator('[data-evo-view=experiment]').click()
        for key in ['generate', 'mutate', 'compose']:
            page.locator(f'#evo-tab-{key}').click()
            page.wait_for_function(f'(key) => {evo}?.getState().scene === key', arg=key, timeout=60000)
            for mode in ['drag', 'push', 'view']:
                page.locator(f'[data-evo-mode={mode}]').click()
                controls(page, evo, '#evo-stage', mode)
            assert 'scroll to zoom' in page.locator('#evo-hint').inner_text()
        for modifier in ['Control', 'Meta']:
            wheel(page, evo, '#evo-stage', modifier=modifier)
        page.locator('#evo-fullscreen').click()
        page.wait_for_function('!!document.fullscreenElement')
        page.locator('[data-evo-mode=push]').click()
        wheel(page, evo, '#evo-stage')
        page.locator('#evo-fullscreen').click()
        page.wait_for_function('!document.fullscreenElement')
        print('PASS: all three evolved scenes, Ctrl/Command gestures, fullscreen, and scrolling outside the canvas.', flush=True)

        # Already-loaded rooms share the choice; new scenes and reloads retain it.
        scene_switch = page.locator('#scene-live-stage [data-room-wheel]')
        evo_switch = page.locator('#evo-stage [data-room-wheel]')
        scene_switch.click()
        assert evo_switch.get_attribute('aria-checked') == 'true'
        assert page.evaluate('localStorage.getItem("longchang-wheel-zoom")') == 'true'
        page.locator('#evo-tab-generate').click()
        page.wait_for_function(f'{evo}?.getState().scene === "generate"', timeout=60000)
        assert evo_switch.get_attribute('aria-checked') == 'true'
        wheel(page, evo, '#evo-stage')
        page.reload()
        page.locator('[data-atlas-view=motion]').click()
        page.wait_for_function('!!window.SceneRoom', timeout=60000)
        assert scene_switch.get_attribute('aria-checked') == 'true'
        wheel(page, 'SceneRoom', '#scene-live-stage')
        page.locator('[data-evo-view=experiment]').click()
        page.wait_for_function(f'!!{evo}', timeout=60000)
        assert evo_switch.get_attribute('aria-checked') == 'true'
        evo_switch.click()
        assert scene_switch.get_attribute('aria-checked') == 'false'
        page.reload()
        page.locator('[data-atlas-view=motion]').click()
        page.wait_for_function('!!window.SceneRoom', timeout=60000)
        assert scene_switch.get_attribute('aria-checked') == 'false'
        print('PASS: wheel preference synchronizes both sections and survives scene changes and reloads in either state.', flush=True)

        for tab, stage, video in [
            ('[data-atlas-view=physics]', '#worlds .physics-video-frame', '#physics-video'),
            ('[data-evo-view=demo]', '#evo-demo-view', '#evo-demo-video'),
        ]:
            page.locator(tab).click()
            x, y = center(page, stage)
            page.locator(video).evaluate('v => v.pause()')
            before = page.locator(video).evaluate('v => ({src:v.currentSrc,time:v.currentTime,rate:v.playbackRate})')
            page.mouse.move(x, y)
            old_scroll = page.evaluate('scrollY')
            page.mouse.wheel(0, -100)
            page.wait_for_function('(y) => scrollY < y - 20', arg=old_scroll)
            assert page.locator(video).evaluate('v => ({src:v.currentSrc,time:v.currentTime,rate:v.playbackRate})') == before

        page.locator('[data-room-mode=view]').click()
        page.wait_for_function('!!window.RoomDemo', timeout=60000)
        page.evaluate('RoomDemo.pause()')
        x, y = center(page, '#room-stage')
        before = page.evaluate(span_script('RoomDemo'))
        page.mouse.move(x, y)
        old_scroll = page.evaluate('scrollY')
        page.mouse.wheel(0, 180)
        page.wait_for_function('(y) => scrollY > y + 40', arg=old_scroll)
        assert abs(page.evaluate(span_script('RoomDemo')) - before) < .01
        wheel(page, 'RoomDemo', '#room-stage', modifier='Control')
        print('PASS: fixed Demo cameras and the introductory figure scrolling behavior.', flush=True)

        phone = browser.new_page(viewport={'width':390, 'height':844}, is_mobile=True, has_touch=True, reduced_motion='reduce')
        phone.on('pageerror', lambda error: errors.append(str(error)))
        phone.goto(url + '#worlds')
        cdp = phone.context.new_cdp_session(phone)
        for api, tab, stage, hint in [
            ('SceneRoom', '[data-atlas-view=motion]', '#scene-live-stage', '#scene-live-hint'),
            (evo, '[data-evo-view=experiment]', '#evo-stage', '#evo-hint'),
        ]:
            phone.locator(tab).tap()
            phone.wait_for_function(f'!!window.{api}', timeout=60000)
            x, y = center(phone, stage)
            assert 'pinch to zoom' in phone.locator(hint).inner_text()
            before = phone.evaluate(span_script(api))
            state = phone.evaluate(f'{api}.getState()')
            def pair(distance):
                return [{'id':1, 'x':x-distance, 'y':y}, {'id':2, 'x':x+distance, 'y':y}]
            cdp.send('Input.dispatchTouchEvent', {'type':'touchStart', 'touchPoints':pair(25)})
            for distance in [30, 35, 40, 45, 50]:
                cdp.send('Input.dispatchTouchEvent', {'type':'touchMove', 'touchPoints':pair(distance)})
            cdp.send('Input.dispatchTouchEvent', {'type':'touchEnd', 'touchPoints':[]})
            assert phone.evaluate(span_script(api)) > before * 1.5
            assert phone.evaluate(f'{api}.getState()') == state
            assert phone.locator(stage + ' canvas').get_attribute('title') == 'Pinch to zoom'
            phone.locator(stage + ' [data-room-zoom=fit]').tap()
            assert abs(phone.evaluate(span_script(api)) - before) < .01
            assert phone.evaluate(f'{api}.getState()') == state
            for button in phone.locator(stage + ' .room-view-tools button').all():
                box = button.bounding_box()
                assert box['width'] >= 44 and box['height'] >= 44
            assert phone.evaluate('document.documentElement.scrollWidth <= innerWidth')
        # Restricted storage still permits changing the preference for this visit.
        restricted = browser.new_page(viewport={'width':1366, 'height':900})
        restricted.on('pageerror', lambda error: errors.append(str(error)))
        restricted.add_init_script('Object.defineProperty(window,"localStorage",{get(){throw new Error("Storage blocked");}})')
        restricted.goto(url + '#worlds')
        restricted.locator('[data-atlas-view=motion]').click()
        restricted.wait_for_function('!!window.SceneRoom', timeout=60000)
        restricted.locator('#scene-live-stage [data-room-wheel]').click()
        assert restricted.locator('#scene-live-stage [data-room-wheel]').get_attribute('aria-checked') == 'true'
        wheel(restricted, 'SceneRoom', '#scene-live-stage')
        browser.close()
    assert not errors, errors
    assert not bad, bad
    print('PASS: real mobile pinch in both Try it sections; no JavaScript errors or failed resources.')


if __name__ == '__main__':
    main()
