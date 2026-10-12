"""Browser checks for scene triggers, explanatory controls and motion playback."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

SITE = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default=(SITE / 'index.html').as_uri())
    args = parser.parse_args()
    errors = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=['--no-sandbox'])
        page = browser.new_page(viewport={'width':1440, 'height':1000}, reduced_motion='reduce')
        page.on('pageerror', lambda error:errors.append(str(error)))
        page.goto(args.url)
        page.evaluate('document.fonts.ready')

        def choose(number):
            page.locator(f'#scene-tab-{number:02}').click()
            page.locator('[data-atlas-view="motion"]').click()
            page.locator('#atlas-canvas').scroll_into_view_if_needed()

        def seek(seconds):
            page.locator('#atlas-progress').evaluate('(e,v)=>{e.value=v;e.dispatchEvent(new Event("input",{bubbles:true}));}', seconds * 100)

        def option(value):
            page.locator('#atlas-parameter').select_option(value)

        def state():
            return page.locator('#atlas-state-label').inner_text()

        def sphere_colors():
            return page.locator('#atlas-canvas circle[fill^="url("]').evaluate_all('(nodes)=>nodes.map(n=>n.getAttribute("fill"))')

        for number in range(1, 16):
            choose(number)
            assert page.locator('#atlas-trigger-text').inner_text()
            assert page.locator('#atlas-model-note').inner_text()
            for seconds in [0, 2, 4, 6, 8]:
                seek(seconds)
                svg = page.locator('#atlas-canvas').inner_html()
                assert 'NaN' not in svg and 'undefined' not in svg and 'Infinity' not in svg, number
            page.locator('[data-atlas-view="initial"]').click()
            page.wait_for_function('document.querySelector("#scene-image").naturalWidth > 0')
            assert page.locator('#scene-image').is_visible()
            assert not page.locator('#atlas-canvas').is_visible()
            page.locator('[data-atlas-view="motion"]').click()
            assert page.locator('#atlas-canvas').is_visible()
            parameter = page.locator('#atlas-parameter')
            if parameter.evaluate('(e)=>e.tagName') == 'SELECT':
                for value in parameter.locator('option').evaluate_all('(a)=>a.map(e=>e.value)'):
                    option(value)
                    seek(5)
                    assert 'NaN' not in page.locator('#atlas-canvas').inner_html(), (number, value)
            else:
                for value in [parameter.get_attribute('min'), parameter.get_attribute('max')]:
                    parameter.fill(value)
                    seek(5)
                    assert 'NaN' not in page.locator('#atlas-canvas').inner_html(), (number, value)

        # Counterfactual settings and event boundaries that matter scientifically.
        choose(2); option('red-blue'); seek(4)
        assert state() == 'NO EXTRA ATTRACTION'
        option('red-red'); seek(4)
        assert state() == 'RED–RED ATTRACTION'
        choose(5); page.locator('#atlas-parameter').fill('2'); seek(4)
        assert state() == 'BELOW THE THRESHOLD'
        page.locator('#atlas-parameter').fill('5'); seek(4)
        assert state() == 'ADDED BRAKING ACTIVE'
        choose(6); option('90'); seek(0)
        red = page.locator('#atlas-canvas circle[fill="url(#atlas-red)"]')
        start = red.evaluate('(e)=>[+e.getAttribute("cx"),+e.getAttribute("cy")]')
        seek(2)
        end = red.evaluate('(e)=>[+e.getAttribute("cx"),+e.getAttribute("cy")]')
        # A northward launch must bend east (right), not west.
        eastward_travel = ((end[0] - start[0]) / 43 + (end[1] - start[1]) / 22) / 2
        assert eastward_travel > 0
        choose(9); option('above'); seek(3)
        assert state() == 'INSIDE THE FOOTPRINT'
        seek(7)
        assert state() == 'EXIT MULTIPLIER APPLIED'
        option('beside'); seek(3)
        assert state() == 'OUTSIDE THE REGION'
        choose(10); option('outside'); seek(5)
        assert state() == 'AT REST OUTSIDE'
        choose(11); seek(3.1)
        assert state() == 'IN CONTACT'
        seek(4)
        assert state() == 'CONTACT HAS ENDED'
        option('wall'); seek(4)
        assert 'No boost' in page.locator('#atlas-canvas').text_content()
        choose(12); option('hold'); seek(2)
        colors = sphere_colors()
        assert colors == ['url(#atlas-blue)', 'url(#atlas-red)']
        seek(7)
        assert sphere_colors() == colors
        option('repeat'); seek(6)
        assert sphere_colors() == ['url(#atlas-red)', 'url(#atlas-blue)']
        choose(13); option('hold'); seek(7)
        assert page.locator('#atlas-value').inner_text().startswith('1 / 3')
        option('repeat'); seek(5.4)
        assert page.locator('#atlas-value').inner_text().startswith('2 / 3')
        seek(6)
        assert state() == 'THIRD CONTACT · UPWARD KICK'
        option('wall'); seek(7)
        assert page.locator('#atlas-value').inner_text().startswith('0 / 3')
        choose(14); option('hold'); seek(5.9)
        assert state() == 'VELOCITY STORED AT LAUNCH'
        seek(6)
        assert state() == 'GREEN TAKES THE STORED VELOCITY'
        choose(15); option('blue'); seek(3)
        assert 'FORCE PAUSED' in state()
        seek(6.5)
        assert 'FORCE RETURNS' in state()
        option('zero'); seek(3)
        assert state() == 'ZERO IMPULSE · NO PAUSE'

        # Playback remains explicit under reduced motion and can pause/seek.
        choose(7)
        page.wait_for_timeout(120)
        assert page.locator('#atlas-progress').input_value() == '0'
        page.locator('#atlas-play').click()
        page.wait_for_timeout(220)
        assert int(page.locator('#atlas-progress').input_value()) > 0
        page.locator('#atlas-play').click()
        before = page.locator('#atlas-progress').input_value()
        page.wait_for_timeout(120)
        assert page.locator('#atlas-progress').input_value() == before
        page.locator('#atlas-next').click()
        assert page.locator('#scene-tab-08').get_attribute('aria-selected') == 'true'
        page.locator('#scene-tab-08').focus(); page.keyboard.press('ArrowLeft')
        assert page.locator('#scene-tab-07').get_attribute('aria-selected') == 'true'
        page.locator('#atlas-tour').click()
        page.locator('#atlas-canvas').scroll_into_view_if_needed()
        assert page.locator('#atlas-tour').get_attribute('aria-pressed') == 'true'
        page.wait_for_function('document.querySelector("#scene-tab-02").getAttribute("aria-selected")==="true"', timeout=13000)
        page.locator('#atlas-tour').click()
        assert page.locator('#atlas-tour').get_attribute('aria-pressed') == 'false'

        opener = page.locator('.hero-actions [data-open-presentation]')
        opener.click()
        assert page.locator('#motion-dialog').is_visible()
        page.locator('#presentation-play').click()
        for index in range(4):
            page.locator(f'#presentation-chapters [data-motion-index="{index}"]').click()
            assert page.locator('#presentation-title').inner_text()
            page.locator('#presentation-progress').evaluate('(e,v)=>{e.value=v;e.dispatchEvent(new Event("input",{bubbles:true}));}', index * 120 + 70)
            assert 'NaN' not in page.locator('#presentation-canvas').inner_html()
        page.keyboard.press('Escape')
        assert not page.locator('#motion-dialog').is_visible()
        assert opener.evaluate('(e)=>document.activeElement===e')
        for width in [1440, 1024, 768, 390, 360, 320]:
            page.set_viewport_size({'width':width, 'height':900})
            choose(14)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), width
            opener.click()
            assert page.locator('#motion-dialog').evaluate('(e)=>e.scrollWidth<=e.clientWidth'), width
            page.keyboard.press('Escape')
        browser.close()
    assert not errors, errors
    print(json.dumps({'status':'PASS', 'checks':[
        'all 15 illustrations, all controls and original scene views',
        'force thresholds, boundary effects and inactive controls',
        'contact start/end, sustained contact, identity and third-contact history',
        '12-count transfer persists after holding red; 10-count pause and zero-push control',
        'play, pause, seek, keyboard navigation and automatic scene tour',
        'presentation chapters, focus return, responsive dialog and reduced motion',
        'no JavaScript errors']}, indent=2))


if __name__ == '__main__':
    main()
