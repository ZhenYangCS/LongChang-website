"""Verify motion guides against recorded poses and the film's crop camera."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

SITE = Path(__file__).resolve().parents[1]


def projection(entry, position):
    camera = entry['detail_camera']
    width, height = entry['detail_dimensions']
    delta = [p-c for p, c in zip(position, camera['position'])]
    right = sum(a*b for a, b in zip(delta, camera['right']))
    up = sum(a*b for a, b in zip(delta, camera['up']))
    left, top, end_x, end_y = entry['detail_crop']
    return [left+(.5+right/(camera['span']*width/height))*(end_x-left),
            top+(.5-up/camera['span'])*(end_y-top)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8765')
    args = parser.parse_args()
    errors = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width': 1366, 'height': 1000}, reduced_motion='reduce')
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(args.url, wait_until='domcontentloaded')
        assert not page.evaluate('performance.getEntriesByType("resource").some(r => r.name.includes("/scene-details/"))')
        guides = page.locator('.scene-trajectories')
        for number in range(1, 16):
            scene_id = f'{number:02}'
            entry = json.loads((SITE/f'data/scene-details/{scene_id}.json').read_text())
            page.evaluate('(id) => showWorld(id)', scene_id)
            page.locator('#physics-progress').evaluate('e => {e.value=600; e.dispatchEvent(new Event("input", {bubbles:true}));}')
            page.wait_for_function('document.querySelector("#physics-video").readyState>=2 && !document.querySelector("#physics-video").seeking')
            if entry.get('proof'):
                expect(guides).to_have_attribute('data-status', 'baked')
                assert not guides.is_visible(), 'Do not duplicate guides already rendered in the film'
                if any(label[2]=='dashed' for label in entry['proof']['labels']):
                    key=page.locator('.scene-motion-key')
                    expect(key).to_be_visible()
                    assert 'This world' in key.inner_text() and 'Ordinary physics' in key.inner_text()
                continue
            page.wait_for_function('(id) => {const g=document.querySelector(".scene-trajectories");return g.dataset.status==="ready" && g.dataset.scene===id;}', arg=scene_id)
            expect(guides).to_be_visible()
            frame = entry['timeline'][int(guides.get_attribute('data-frame'))]
            endpoints = page.locator('.scene-motion-path').evaluate_all('paths => paths.map(p => ({name:p.dataset.object, point:(()=>{const v=p.getPointAtLength(p.getTotalLength());return [v.x,v.y];})()}))')
            assert set(p['name'] for p in endpoints) == set(frame['objects'])
            for path in endpoints:
                expected = projection(entry, frame['objects'][path['name']]['position'])
                assert max(abs(a-b) for a, b in zip(path['point'], expected)) < .01, (scene_id, path, expected)
            assert not any(s in guides.inner_html() for s in ['NaN', 'undefined'])

        page.evaluate('showWorld("06")')
        page.locator('#physics-progress').evaluate('e => {e.value=50;e.dispatchEvent(new Event("input",{bubbles:true}));}')
        expect(guides).to_have_attribute('data-scene', '06')
        expect(page.locator('.scene-motion-action-label')).to_have_text('Push')
        assert page.locator('[data-vector="force"]').count() == 1
        page.locator('#physics-play').click()
        before = int(guides.get_attribute('data-frame'))
        page.wait_for_function('(frame) => Number(document.querySelector(".scene-trajectories").dataset.frame)>frame', arg=before)
        page.locator('#physics-play').click()
        before = page.locator('.scene-motion-path').first.get_attribute('d')
        page.wait_for_timeout(160)
        assert page.locator('.scene-motion-path').first.get_attribute('d') == before

        # One compositor transform moves both the film and its guides.
        source = page.locator('#physics-video').evaluate('video => video.currentSrc')
        time = page.locator('#physics-video').evaluate('video => video.currentTime')
        for _ in range(2):
            page.locator('#physics-view').click()
            assert page.locator('.scene-motion-path').first.get_attribute('d') == before
            assert page.locator('#physics-video').evaluate('video => video.currentSrc') == source
            assert abs(page.locator('#physics-video').evaluate('video => video.currentTime')-time) < .01
        page.locator('#physics-fullscreen').click()
        page.wait_for_function('Boolean(document.fullscreenElement)')
        expect(guides).to_be_visible()
        page.evaluate('document.exitFullscreen()')
        page.wait_for_function('!document.fullscreenElement')
        for width in [1440, 1024, 390, 320]:
            page.set_viewport_size({'width': width, 'height': 900})
            assert page.locator('.scene-motion-path').first.get_attribute('d') == before
        page.locator('#physics-reset').click()
        expect(guides).to_be_hidden()
        page.locator('[data-atlas-view="analysis"]').click()
        expect(guides).to_be_hidden()
        browser.close()
    assert not errors, errors
    print('PASS: all 15 scenes use recorded guides or retain their baked motion annotations.')
    print('PASS: trajectory endpoints match the film camera to <0.01 source pixels.')
    print('PASS: launch/force arrows, playback, pause, reset, seeking, zoom and fullscreen.')
    print('PASS: lazy loading, responsive alignment, view changes, no JavaScript errors.')


if __name__ == '__main__':
    main()
