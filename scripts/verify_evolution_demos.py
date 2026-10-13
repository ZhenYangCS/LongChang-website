"""Verify native demo provenance and one-control playback of three videos."""
import argparse
import hashlib
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

SITE=Path(__file__).resolve().parents[1]
ROOT=SITE.parent


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',default='http://127.0.0.1:8765')
    args=parser.parse_args()
    manifest=json.loads((SITE/'data/evolution-demos.json').read_text())
    assert [d['id'] for d in manifest['demos']]==['generate','mutate','compose']
    assert len({json.dumps(d['camera'],sort_keys=True) for d in manifest['demos']})==1
    for demo in manifest['demos']:
        assert hashlib.sha256((ROOT/demo['source']).read_bytes()).hexdigest()==demo['source_sha256']
        assert hashlib.sha256((SITE/demo['video']).read_bytes()).hexdigest()==demo['video_sha256']
        assert demo['physics_timestep']==.002
    errors=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1440,'height':1000})
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(args.url,wait_until='domcontentloaded')
        assert not page.evaluate('performance.getEntriesByType("resource").some(r=>/evolution-.*\\.mp4/.test(r.name))')
        root=page.locator('#evolution-demos')
        root.scroll_into_view_if_needed()
        page.wait_for_function('[...document.querySelectorAll("#evolution-demos video")].every(v=>!v.paused&&v.currentTime>.1)')
        assert page.locator('#evolution video').count()==3
        assert page.locator('#evolution button').count()==1
        for video in page.locator('#evolution video').all():
            assert video.evaluate('v=>v.videoWidth===720&&v.videoHeight===540&&Math.abs(v.duration-10)<.1&&v.loop&&v.muted')
        page.locator('#evolution-play').click()
        assert page.locator('#evolution video').evaluate_all('vs=>vs.every(v=>v.paused)')
        before=page.locator('#evolution video').evaluate_all('vs=>vs.map(v=>v.currentTime)')
        page.wait_for_timeout(160)
        assert page.locator('#evolution video').evaluate_all('vs=>vs.map(v=>v.currentTime)')==before
        page.locator('#evolution-play').press('Enter')
        page.wait_for_function('[...document.querySelectorAll("#evolution video")].every(v=>!v.paused)')
        page.evaluate('window.scrollTo({top:0,behavior:"instant"})')
        page.wait_for_function('[...document.querySelectorAll("#evolution video")].every(v=>v.paused)')
        root.scroll_into_view_if_needed()
        page.wait_for_function('[...document.querySelectorAll("#evolution video")].every(v=>!v.paused)')
        # Full exploration records are still reachable, outside the case section.
        page.evaluate('showDiscovery("07")')
        expect(page.locator('#exploration-dialog')).to_have_js_property('open',True)
        expect(page.locator('#success-tab-07')).to_have_attribute('aria-selected','true')
        page.wait_for_function('[...document.querySelectorAll("#evolution video")].every(v=>v.paused)')
        page.locator('#exploration-close').click()
        page.locator('#evolution-play').click()
        for width in [1440,1024,768,600,390,320]:
            page.set_viewport_size({'width':width,'height':1000})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
            if width>=768:
                ys=page.locator('.evolution-demo').evaluate_all('els=>els.map(e=>e.getBoundingClientRect().top)')
                assert max(ys)-min(ys)<1
        reduced=browser.new_page(viewport={'width':1280,'height':900},reduced_motion='reduce')
        reduced.on('pageerror',lambda error:errors.append(str(error)))
        reduced.goto(args.url,wait_until='domcontentloaded')
        reduced.locator('#evolution-demos').scroll_into_view_if_needed()
        assert not reduced.evaluate('performance.getEntriesByType("resource").some(r=>/evolution-.*\\.mp4/.test(r.name))')
        expect(reduced.locator('#evolution-play')).to_have_text('Play demos')
        reduced.locator('#evolution-play').click()
        reduced.wait_for_function('[...document.querySelectorAll("#evolution video")].every(v=>!v.paused&&v.currentTime>.1)')
        broken=browser.new_page(viewport={'width':1280,'height':900},reduced_motion='reduce')
        broken.on('pageerror',lambda error:errors.append(str(error)))
        broken.route('**/evolution-mutate.mp4',lambda route:route.abort())
        broken.goto(args.url,wait_until='domcontentloaded')
        broken.locator('#evolution-demos').scroll_into_view_if_needed()
        broken.locator('#evolution-play').click()
        expect(broken.locator('#evolution-play')).to_have_text('Retry demos')
        broken.unroute('**/evolution-mutate.mp4')
        broken.locator('#evolution-play').click()
        broken.wait_for_function('[...document.querySelectorAll("#evolution video")].every(v=>!v.paused&&v.currentTime>.1)')
        browser.close()
    assert not errors,errors
    print('PASS: native scene/video hashes, shared camera, three 10-second demos, one playback control, viewport/modal pause, reduced motion, retry and 320–1440 px layouts.')


if __name__=='__main__':main()
