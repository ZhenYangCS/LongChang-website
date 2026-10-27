"""Check touch preloading, cold retries and unchanged playback/rendering behavior."""
import argparse
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8765')
    args = parser.parse_args()
    url = args.url.rstrip('/') + '/'
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--enable-unsafe-swiftshader'])

        def tablet(save_data=False):
            page = browser.new_page(viewport={'width':820, 'height':1180},
                                    device_scale_factor=2, is_mobile=True, has_touch=True)
            page.on('pageerror', lambda error: errors.append(str(error)))
            if save_data:
                page.add_init_script("Object.defineProperty(navigator,'connection',{value:{saveData:true}})")
            page.add_init_script('''window.videoLoads=0;
                document.addEventListener('loadstart',event=>{
                  if(event.target.id==='physics-video')videoLoads++;
                },true);''')
            return page

        page = tablet()
        requests = []
        page.on('request', lambda request: requests.append(request.url))
        page.goto(url + '#worlds')
        page.wait_for_function('document.querySelector("#physics-video").readyState>=2')
        page.wait_for_function('performance.getEntriesByType("resource").some(r=>r.name.endsWith("mujoco.wasm"))')
        # Await already-started work, then check no renderer/simulation was created.
        page.evaluate('LongChangResources.interaction()')
        assert page.locator('.room-canvas').count() == 0
        assert not page.evaluate('!!window.RoomDemo || !!window.SceneRoom')
        assert page.locator('#studio-poster').is_visible()
        assert page.locator('#scene-play-overlay').inner_text() == '▶ Play'
        assert page.locator('#physics-video').evaluate('v=>v.paused && v.currentTime===0 && v.playbackRate===4 && v.videoWidth===1600')
        movies = {urlsplit(request).path for request in requests if '.mp4' in request}
        assert len(movies) == 1 and next(iter(movies)).endswith('/front-detail/scene-07.mp4'), movies
        assert not any('/evolution/' in request for request in requests)
        loads = page.evaluate('videoLoads')
        page.locator('#scene-play-overlay').tap()
        page.wait_for_function('!document.querySelector("#physics-video").paused && document.querySelector("#physics-video").currentTime>.05')
        assert page.evaluate('videoLoads') == loads, 'Play must reuse the prepared source'
        page.locator('#physics-play').tap()
        page.locator('#physics-progress').evaluate('e=>{e.value=650;e.dispatchEvent(new Event("input",{bubbles:true}));}')
        page.wait_for_function('''()=>{const v=document.querySelector('#physics-video');
            return !v.seeking && v.paused && Math.abs(v.currentTime/v.duration-.65)<.02;}''')
        page.locator('[data-atlas-view=motion]').tap()
        page.wait_for_function('window.SceneRoom?.getState().scene==="07"')
        quality = page.evaluate('SceneRoom.getRenderInfo()')
        assert quality['pixelRatio'] == 2 and quality['shadowMapSize'] == 2048, quality
        assert page.locator('#scene-live-speed').input_value() == '4'
        assert page.evaluate('!SceneRoom.isRunning() && SceneRoom.getState().time===0')
        assert sum('/interactive-scenes/07.json' in request for request in requests) == 1
        page.evaluate('showWorld("12");showWorld("15")')
        page.wait_for_function('window.SceneRoom?.getState().scene==="15"')
        assert page.locator('#scene-live-stage canvas').count() == 1
        assert sum(request.endswith('mujoco.wasm') for request in requests) == 1
        print('PASS: touch prepares one current video and one shared engine; no unsolicited simulation, unchanged HD/4x/2x pixels/2048 shadows, seek and rapid scene changes.', flush=True)

        page.locator('#case-question-video').scroll_into_view_if_needed()
        page.wait_for_function('document.querySelector("#case-question-video").readyState>=2')
        assert page.locator('#case-question-video').evaluate('v=>v.paused && v.currentTime===0 && v.playbackRate===2')
        assert not any('/case-color.mp4' in request or '/case-tool.mp4' in request for request in requests)
        page.locator('#question-case .case-play').tap()
        page.wait_for_function('document.querySelector("#case-question-video").currentTime>.05')
        page.locator('#evo-demo-video').scroll_into_view_if_needed()
        page.wait_for_function('document.querySelector("#evo-demo-video").readyState>=2')
        assert page.locator('#evo-demo-video').evaluate('v=>v.playbackRate===4 && v.videoWidth===1600')
        assert page.locator('#case-question-video').evaluate('v=>v.paused')
        page.locator('[data-evo-view=experiment]').tap()
        page.wait_for_function('!!window.LongChangEvolution.current()')
        assert sum(request.endswith('mujoco.wasm') for request in requests) == 1
        assert page.locator('#evo-demo-video').evaluate('v=>v.paused')
        page.close()
        print('PASS: only the current case film is prepared; case/evolution playback and shared interaction keep their existing behavior.', flush=True)

        # A failed speculative request must stay silent and allow a real tap to retry.
        page = tablet()
        attempts = {'video':0, 'wasm':0}

        def fail_once(route):
            kind = 'wasm' if route.request.url.endswith('.wasm') else 'video'
            attempts[kind] += 1
            if attempts[kind] == 1:
                route.fulfill(status=503, body='Try again')
            else:
                route.continue_()

        page.route('**/mujoco.wasm', fail_once)
        page.route('**/front-detail/scene-07.mp4*', fail_once)
        page.goto(url + '#worlds')
        page.wait_for_function('document.querySelector("#physics-video").preload==="none" && !document.querySelector("#physics-video").hasAttribute("src")')
        page.wait_for_timeout(750)
        assert attempts['video'] == 1 and attempts['wasm'] >= 1, attempts
        assert page.locator('#physics-error').is_hidden()
        assert page.locator('#scene-play-overlay').inner_text() == '▶ Play'
        page.locator('#scene-play-overlay').tap()
        page.wait_for_function('!document.querySelector("#physics-video").paused && document.querySelector("#physics-video").currentTime>.05')
        page.locator('[data-atlas-view=motion]').tap()
        page.wait_for_function('!!window.SceneRoom')
        assert attempts['video'] >= 2 and attempts['wasm'] >= 2, attempts
        page.close()
        print('PASS: speculative failures stay silent; tapping retries the original video and interaction.', flush=True)

        page = tablet(save_data=True)
        requests = []
        page.on('request', lambda request: requests.append(request.url))
        page.goto(url + '#worlds', wait_until='networkidle')
        page.wait_for_timeout(500)
        assert not any('.mp4' in request or '.wasm' in request for request in requests), requests
        # Scrubbing before the first play must load even when preload was none.
        page.locator('#physics-progress').evaluate('e=>{e.value=500;e.dispatchEvent(new Event("input",{bubbles:true}));}')
        page.wait_for_function('''()=>{const v=document.querySelector('#physics-video');
            return v.readyState>=2 && !v.seeking && v.paused && Math.abs(v.currentTime/v.duration-.5)<.02;}''')
        page.locator('[data-atlas-view=motion]').tap()
        page.wait_for_function('!!window.SceneRoom')
        page.close()
        print('PASS: Data Saver suppresses speculation; explicit seek/play/interaction remain available.', flush=True)
        browser.close()
    assert not errors, errors


if __name__ == '__main__':
    main()
