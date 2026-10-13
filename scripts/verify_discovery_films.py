"""Validate archived evidence and synchronized, annotated trial comparisons."""
import argparse
import hashlib
import json
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from playwright.sync_api import expect, sync_playwright

SITE = Path(__file__).resolve().parents[1]
PAIRS = {'07': [1, 2], '06': [0, 1], '14': [0, 1], '15': [1, 2]}
MEDIA = '.discovery-trial video'


def open_comparison(page, scene, repeat):
    page.locator(f'[data-result-scene="{scene}"]').click()
    page.locator(f'#evidence-run-{repeat}').click()
    page.locator('#evidence-film').click()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8765/')
    args = parser.parse_args()
    films = json.loads((SITE/'data/discovery-films.js').read_text().removeprefix('window.DISCOVERY_FILMS = ').rstrip(';\n'))
    sources = json.loads((SITE/'data/discoveries.js').read_text().removeprefix('window.DISCOVERIES = ').rstrip(';\n'))
    by_id = {source['id']: source for source in sources}
    provenance = json.loads((SITE/'data/discovery-provenance.json').read_text())
    guides = json.loads((SITE/'data/discovery-guides.json').read_text())
    projections = 0
    for film in films:
        source = by_id[film['id']]
        assert film['episode_id'] == source['episode_id'] and all(source['verdict'].values())
        assert [part['source'] for part in film['segments']] == [part['video'] for part in source['chapters']]
        assert hashlib.sha256((SITE/film['video']).read_bytes()).hexdigest() == film['sha256']
        archive = next(item for item in provenance if item['episode_id'] == source['episode_id'])
        for chapter in source['chapters']:
            guide = guides[chapter['video']]
            assert guide['video_sha256'] == hashlib.sha256((SITE/chapter['video']).read_bytes()).hexdigest()
            assert guide['replay_sha256'] == archive['replay_sha256']
            assert (guide['start'], guide['end']) == (chapter['start'], chapter['end'])
            if film['id'] == '07':
                continue
            # Check projection independently against actual colored pixels in
            # the rendered source, including moving objects near both edges.
            reader = imageio_ffmpeg.read_frames(str(SITE/chapter['video']))
            metadata = next(reader)
            count = len(guide['tracks'][0]['points'])
            for index, raw in enumerate(reader):
                if index not in {0, count//2, count-1}:
                    continue
                pixels = np.frombuffer(raw, dtype=np.uint8).reshape(metadata['size'][1], metadata['size'][0], 3)
                for track in guide['tracks']:
                    x, y = map(round, track['points'][index])
                    radius = max(2, round(track['radius']*.4))
                    color = pixels[max(0,y-radius):y+radius+1, max(0,x-radius):x+radius+1].mean(axis=(0,1))
                    channel = {'red_ball':0, 'green_ball':1, 'blue_ball':2}[track['name']]
                    assert color[channel] > max(np.delete(color, channel))*1.12, (chapter['video'], index, track['name'], color)
                    projections += 1
            reader.close()
    print(f'PASS: evidence hashes, archived time ranges and {projections} video-pixel checks of object markers.', flush=True)

    errors = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width':1366, 'height':900})
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(args.url, wait_until='domcontentloaded')
        assert page.locator(MEDIA).evaluate_all('(vs)=>vs.every(v=>!v.getAttribute("src"))')
        assert page.locator('[data-result-scene]').count() == 15
        expect(page.locator('[data-result-scene="07"]')).to_contain_text('Tile rebounds')
        assert page.locator('.result-scene:visible').count() == 14
        for scene, indices in PAIRS.items():
            source = by_id[scene]
            trials = [source['chapters'][index] for index in indices]
            spans = [trial['end']-trial['start'] for trial in trials]
            duration = max(spans)
            open_comparison(page, scene, source['repeat'])
            page.wait_for_function('''() => [...document.querySelectorAll('.discovery-trial video')].every(v=>v.readyState>=2&&!v.paused)''')
            page.wait_for_function('document.querySelectorAll(".discovery-target").length>=2')
            expect(page.locator('#discovery-title')).to_have_text(source['name'])
            assert page.locator('#exploration-dialog button:visible').count() == 3
            assert page.locator(MEDIA).evaluate_all('(vs)=>vs.map(v=>v.getAttribute("src"))') == [trial['video'] for trial in trials]
            page.wait_for_timeout(200)
            elapsed = page.locator(MEDIA).evaluate_all('(vs)=>vs.map(v=>v.currentTime/v.duration)')
            assert abs(elapsed[0]*spans[0]-elapsed[1]*spans[1]) < .18
            page.locator('#replay-play').click()
            frozen = page.locator(MEDIA).evaluate_all('(vs)=>vs.map(v=>v.currentTime)')
            page.wait_for_timeout(120)
            assert page.locator(MEDIA).evaluate_all('(vs)=>vs.map(v=>v.currentTime)') == frozen
            for fraction in [.5, .8, 1]:
                page.locator('#replay-progress').evaluate('(e,v)=>{e.value=v;e.dispatchEvent(new Event("input",{bubbles:true}));}', fraction*1000)
                page.wait_for_function('''() => [...document.querySelectorAll('.discovery-trial video')].every(v=>!v.seeking)''')
                elapsed = page.locator(MEDIA).evaluate_all('(vs)=>vs.map(v=>v.currentTime/v.duration)')
                for index in range(2):
                    assert abs(elapsed[index]*spans[index]-min(fraction*duration, spans[index])) < .03
                marker_frames = page.locator('.discovery-guide').evaluate_all('(gs)=>gs.map(g=>Number(g.dataset.frame))')
                video_frames = page.locator(MEDIA).evaluate_all('(vs)=>vs.map(v=>Math.floor(v.currentTime*24))')
                assert all(abs(marker-video) <= 1 for marker, video in zip(marker_frames, video_frames))
            page.locator('#replay-play').click()
            page.wait_for_function('''() => [...document.querySelectorAll('.discovery-trial video')].every(v=>!v.paused&&v.currentTime<1)''')
            page.locator('#replay-fullscreen').click()
            page.wait_for_function('!!document.fullscreenElement')
            assert page.locator('.discovery-trial:visible').count() == 2
            page.locator('#replay-fullscreen').click()
            page.wait_for_function('!document.fullscreenElement')
            page.locator('#exploration-close').click()
            page.wait_for_function('''() => [...document.querySelectorAll('.discovery-trial video')].every(v=>v.paused&&!v.getAttribute('src'))''')
            expect(page.locator('#evidence-film')).to_be_focused()
            page.locator('#evidence-close').click()
            expect(page.locator(f'[data-result-scene="{scene}"]')).to_be_focused()
        print('PASS: named scene entries, complete counts, both players, shared simulation time, seek, replay, fullscreen and cleanup.', flush=True)

        # A failed source must be retriable without reopening the comparison.
        page.route('**/success-07-2.mp4', lambda route: route.fulfill(status=503, body='unavailable'))
        page.evaluate('showDiscovery("07")')
        expect(page.locator('#success-status')).to_contain_text('could not load')
        page.unroute('**/success-07-2.mp4')
        page.locator('#replay-play').click()
        page.wait_for_function('''() => [...document.querySelectorAll('.discovery-trial video')].every(v=>v.readyState>=2&&!v.paused)''')
        page.keyboard.press('Escape')
        expect(page.locator('#exploration-dialog')).not_to_be_visible()
        for width in [1440, 1024, 768, 390, 360, 320]:
            page.set_viewport_size({'width':width, 'height':900})
            page.locator('[data-model="GPT-6-Astra"]').click()
            open_comparison(page, '07', 3)
            page.wait_for_function('''() => [...document.querySelectorAll('.discovery-trial video')].every(v=>v.readyState>=2&&!v.paused)''')
            assert page.locator('#exploration-dialog').evaluate('e=>e.scrollWidth<=e.clientWidth')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.keyboard.press('Escape')
            expect(page.locator('#exploration-dialog')).not_to_be_visible()
            page.locator('#evidence-close').click()
        page.locator('[data-model="Claude-Opus-5"]').click()
        assert page.locator('.result-scene .result-D').all_text_contents() == ['0/3']*14
        assert page.locator('[data-result-scene]').count() == 15
        browser.close()
    assert not errors, errors
    print('PASS: failed-load retry, 320–1440 px layout, mobile entries, zero-discovery models and no JavaScript errors.')


if __name__ == '__main__':
    main()
