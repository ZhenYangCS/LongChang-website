"""Check shared data cancellation, WASM startup and unchanged rendering quality."""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright

SITE = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    args = parser.parse_args()
    url = args.url.rstrip('/') + '/'
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--enable-unsafe-swiftshader'])
        # Isolate the shared loader's cancellation and retry cases from page code.
        unit = browser.new_page()
        unit.add_script_tag(path=str(SITE / 'assets/resources.js'))
        unit.evaluate('''async () => {
          const calls=new Map(), parses=new Map(), aborted=new Map();
          window.fetch=(url,{signal})=>new Promise((resolve,reject)=>{
            const count=(calls.get(url)||0)+1;calls.set(url,count);
            const timer=setTimeout(()=>{
              const response=new Response('{"value":42}',{status:url.endsWith('/retry')&&count===1?503:200});
              const json=response.json.bind(response);
              response.json=()=>{parses.set(url,(parses.get(url)||0)+1);return json();};
              resolve(response);
            },30);
            signal.addEventListener('abort',()=>{clearTimeout(timer);aborted.set(url,true);reject(signal.reason);},{once:true});
          });
          const get=path=>LongChangResources.json('https://test.invalid/'+path);
          const check=(ok,label)=>{if(!ok)throw Error(label);};
          const [a,b]=await Promise.all([get('shared'),get('shared')]);
          check(a===b&&a.value===42,'Concurrent consumers must share parsed data');
          check(await get('shared')===a&&calls.get('https://test.invalid/shared')===1&&parses.get('https://test.invalid/shared')===1,'Cache must avoid download and parsing');
          const one=new AbortController();
          const cancelled=LongChangResources.json('https://test.invalid/partial',{signal:one.signal}).catch(e=>e.name);
          const kept=get('partial');one.abort();
          check(await cancelled==='AbortError'&&(await kept).value===42&&!aborted.has('https://test.invalid/partial'),'One caller must not cancel another');
          const all=new AbortController();
          const dropped=LongChangResources.json('https://test.invalid/all',{signal:all.signal}).catch(e=>e.name);
          all.abort();check(await dropped==='AbortError'&&aborted.has('https://test.invalid/all'),'Cancel unused requests');
          check((await get('all')).value===42&&calls.get('https://test.invalid/all')===2,'Cancelled request must be retryable');
          check(await get('retry').then(()=>false,()=>true),'HTTP errors must reject');
          check((await get('retry')).value===42&&calls.get('https://test.invalid/retry')===2,'Failed request must be retryable');
          for(let i=0;i<6;i++)await get('bounded-'+i);
          await get('bounded-5');check(calls.get('https://test.invalid/bounded-5')===1,'Recent data must remain cached');
          await get('bounded-0');check(calls.get('https://test.invalid/bounded-0')===2,'Old data must be evicted');
        }''')
        unit.close()
        print('PASS: shared download/parse, independent cancellation, retries and bounded cache.', flush=True)

        for fallback in [False, True]:
            page = browser.new_page(viewport={'width':1366, 'height':768})
            page.on('pageerror', lambda e: errors.append(str(e)))
            attempts = []
            def wasm_response(route):
                attempts.append(route.request.url)
                if len(attempts) == 1:
                    route.fulfill(status=503, body='Temporarily unavailable')
                else:
                    # A generic static host may use the wrong MIME type.
                    route.fulfill(status=200, content_type='application/octet-stream',
                                  path=str(SITE / 'assets/vendor/mujoco/mujoco.wasm'))
            page.route('**/mujoco.wasm', wasm_response)
            page.goto(url)
            page.wait_for_load_state('networkidle')
            assert not page.evaluate('performance.getEntriesByType("resource").some(r=>/\\.(mp4|wasm)/.test(r.name))')
            result = page.evaluate('''async fallback=>{
              if(fallback)WebAssembly.compileStreaming=undefined;
              const {getMujoco}=await import('./assets/mujoco-runtime.js');
              const failed=await getMujoco().then(()=>false,()=>true);
              const left=[],right=[];
              const [a,b]=await Promise.all([getMujoco(s=>left.push(s)),getMujoco(s=>right.push(s))]);
              return {failed,shared:a===b,left:left.length,right:right.length,ready:typeof a.MjData==='function'};
            }''', fallback)
            assert result['failed'] and result['shared'] and result['ready'], result
            assert 0 < result['left'] <= 102 and 0 < result['right'] <= 102, result
            assert len(attempts) == 2, attempts
            page.close()
        print('PASS: streaming and fallback WASM, retry, shared instance and progress, generic MIME type.', flush=True)

        page = browser.new_page(viewport={'width':1366, 'height':768}, device_scale_factor=2)
        page.on('pageerror', lambda e: errors.append(str(e)))
        requests = []
        page.on('request', lambda r: requests.append(r.url))
        page.goto(url)
        page.wait_for_load_state('networkidle')
        page.locator('#scene-tab-15').click()
        page.locator('#oracle-measurements').scroll_into_view_if_needed()
        page.wait_for_function('document.querySelector("#oracle-chart").children.length>0')
        page.wait_for_function('document.querySelector(".scene-trajectories").dataset.scene==="15"')
        assert sum('/data/scene-details/15.json' in r for r in requests) == 1
        page.locator('[data-atlas-view=motion]').click()
        page.wait_for_function('window.SceneRoom?.getState().scene==="15"', timeout=60000)
        page.locator('#scene-live-play').click()
        page.wait_for_timeout(2500)
        state = page.evaluate('SceneRoom.getRenderInfo()')
        assert state['pixelRatio'] == 2 and state['shadowMapSize'] == 2048 and not state['softShadows'], state
        page.evaluate('SceneRoom.pause()')
        assert page.locator('#scene-live-speed').input_value() == '4'
        assert not page.evaluate('crossOriginIsolated')
        page.close()
        browser.close()
    assert not errors, errors
    print('PASS: one scene-data request for charts and trails, fixed 2x pixels/2048 shadows, unchanged 4x physics and no isolation requirement.')


if __name__ == '__main__':
    main()
