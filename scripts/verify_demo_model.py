"""Keep the recorded films independent of every merged model control."""
import argparse
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8765/')
    args = parser.parse_args()
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--enable-unsafe-swiftshader'])
        page = browser.new_page(viewport={'width':1366, 'height':900})
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(args.url, wait_until='networkidle')
        assert page.locator('#worlds .atlas-view-switch button').all_text_contents() == ['Demo', 'Interactive']
        page.locator('#physics-speed').select_option('1')
        for i in range(1, 16):
            scene = f'{i:02}'
            page.locator('#scene-tab-'+scene).click()
            page.wait_for_function('document.querySelector("#physics-video").readyState>=2&&!document.querySelector("#physics-video").paused')
            page.locator('#physics-play').click()
            page.locator('#physics-progress').evaluate('e=>{e.value=350;e.dispatchEvent(new Event("input",{bubbles:true}));}')
            page.wait_for_function('()=>{const v=document.querySelector("#physics-video");return !v.seeking&&Math.abs(v.currentTime/v.duration-.35)<.02;}')
            page.locator('#demo-rule').scroll_into_view_if_needed()
            page.wait_for_function('document.querySelector("#oracle-chart path")!==null&&!document.querySelector("#oracle-chart-wrap").hidden')
            before = page.locator('#physics-video').evaluate('v=>({src:v.currentSrc,time:v.currentTime,paused:v.paused})')
            assert before['paused']
            page.evaluate('window.recordedChart=document.querySelector("#oracle-chart path")')
            control = page.locator('#atlas-parameter')
            if control.evaluate('e=>e.tagName') == 'SELECT':
                values = control.locator('option').evaluate_all('els=>els.map(e=>e.value)')
                for value in values:
                    control.select_option(value)
                    assert page.evaluate('LongChangAtlas.getState().value') == value
            else:
                for bound in ['min', 'max']:
                    control.evaluate('(e,b)=>{e.value=e[b];e.dispatchEvent(new Event("input",{bubbles:true}));}', bound)
                    assert float(control.input_value()) == float(control.get_attribute(bound))
            page.locator('#atlas-reset').click()
            page.locator('#atlas-play').click()
            page.wait_for_function('LongChangAtlas.getState().time>.1')
            after = page.locator('#physics-video').evaluate('v=>({src:v.currentSrc,time:v.currentTime,paused:v.paused})')
            assert after == before, (scene, before, after)
            assert page.evaluate('window.recordedChart===document.querySelector("#oracle-chart path")'), scene
            assert page.locator('#atlas-physics-view').is_visible()
            assert page.locator('#scene-detail').get_attribute('data-view') == 'physics'
            assert not any(word in page.locator('#atlas-canvas').inner_html() for word in ['NaN', 'undefined'])
        print('PASS: all 15 recorded videos survive every model option and slider endpoint, with unchanged source, time, pause state and data plot.', flush=True)

        # With both panels in view, a model choice must not interrupt playback.
        page.set_viewport_size({'width':1366, 'height':1700})
        page.locator('#scene-tab-02').click()
        page.evaluate('document.querySelector("#worlds").scrollIntoView({block:"start",behavior:"instant"})')
        page.wait_for_function('!document.querySelector("#physics-video").paused')
        time = page.locator('#physics-video').evaluate('v=>v.currentTime')
        page.locator('#atlas-parameter').select_option('blue-blue')
        page.wait_for_timeout(200)
        assert page.locator('#physics-video').evaluate('v=>!v.paused')
        assert page.locator('#physics-video').evaluate('v=>v.currentTime') > time
        page.locator('#physics-play').click()
        page.locator('#physics-fullscreen').click()
        page.wait_for_function('document.fullscreenElement?.id==="atlas-physics-view"')
        page.locator('#physics-fullscreen').click()
        page.wait_for_function('!document.fullscreenElement')
        page.locator('#analysis-fullscreen').click()
        page.wait_for_function('document.fullscreenElement?.id==="demo-explanation"')
        assert page.locator('#atlas-parameter').is_visible()
        page.locator('#analysis-fullscreen').click()
        page.wait_for_function('!document.fullscreenElement')
        page.locator('[data-atlas-view=motion]').click()
        page.wait_for_function('window.SceneRoom?.getState().scene==="02"')
        assert not page.locator('#demo-explanation').is_visible()
        page.locator('[data-atlas-view=physics]').click()
        assert page.locator('#demo-explanation').is_visible()
        assert not page.evaluate('SceneRoom.isRunning()')
        assert page.locator('#atlas-parameter').input_value() == 'blue-blue'
        print('PASS: concurrent video/model playback, separate fullscreens and native Experiment switching.', flush=True)
        browser.close()
    assert not errors, errors


if __name__ == '__main__':
    main()
