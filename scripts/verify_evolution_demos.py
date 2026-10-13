"""Verify evolution provenance, native/browser parity and interactive experiments."""
import argparse
import hashlib
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

SITE = Path(__file__).resolve().parents[1]
ROOT = SITE.parent


def native_cases():
    from render_physics_demos import World, load_scene, arrange
    import numpy as np
    cases = []
    specs = [
        ('generate', 'pause and recovery', 11, [(0, 'push', 'blue_ball', [0, .05, 0])]),
        ('generate', 'zero push does not postpone recovery', 11, [(0, 'push', 'red_ball', [.2, 0, .1]), (8, 'push', 'blue_ball', [0, 0, 0])]),
        ('generate', 'another push restarts the pause', 18.2, [(0, 'push', 'red_ball', [.1, 0, 0]), (8, 'push', 'blue_ball', [0, .05, 0])]),
        ('mutate', 'hand movement after waiting', 14.2, [(12, 'grip', 'object_2', [3.9, 3, .1]), (14, 'release', None, None)]),
        ('mutate', 'inclusive square boundary', .2, [(0, 'place', 'object_2', [3.5, 3, .1])]),
        ('compose', 'independent copy and suppression clocks', 18.2, [(0, 'push', 'red_ball', [0, -1.2, 0]), (8, 'push', 'blue_ball', [0, .05, 0])]),
        ('compose', 'multiple full 3D copies and zero push', 13.2, [(0, 'push', 'red_ball', [.2, -.2, .1]), (1, 'push', 'red_ball', [.1, -.1, .2]), (8, 'push', 'blue_ball', [0, 0, 0])]),
    ]
    for key, label, duration, events in specs:
        config = json.loads((SITE / f'data/evolution/{key}.json').read_text())
        source = ROOT / config['source']
        definition = json.loads(source.read_text())['scenes'][0]
        assert hashlib.sha256(source.read_bytes()).hexdigest() == config['source_sha256']
        world = World(load_scene(source, definition['id']))
        world._motion = None
        arrange(world, config['preparation'])
        trace, cursor, ticks = [], 0, round(duration / .002)
        for tick in range(ticks + 1):
            while cursor < len(events) and events[cursor][0] <= world.data.time + 1e-8:
                _, kind, name, value = events[cursor]
                if kind == 'push':
                    _, dof = world.bodies[name]
                    bid = world.model.body(name).id
                    world.data.qvel[dof:dof+3] += np.array(value) / world.model.body_mass[bid]
                    if any(value):
                        world.scene.on_launch(world.model, world.data, name)
                elif kind == 'place':
                    arrange(world, {name: value})
                elif kind == 'grip':
                    world.workshop.holds = {name: dict(target=np.array(value))}
                else:
                    world.workshop.holds.clear()
                cursor += 1
            if tick % 25 == 0 or tick == ticks:
                state = world.scene.state
                trace.append(dict(tick=tick, qpos=world.data.qpos.tolist(), qvel=world.data.qvel.tolist(),
                                  quietUntil=getattr(state, 'quiet_until', getattr(state, '_quiet_until', 0)),
                                  pending=[t for t, _ in getattr(state, 'pending_copies', [])]))
            if tick < ticks:
                world.step()
        cases.append(dict(key=key, label=label, events=events, ticks=ticks, trace=trace))
    return cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8765')
    args = parser.parse_args()
    cases = native_cases()
    trace = json.loads((SITE / 'data/evolution/reference-trace.json').read_text())
    original = json.loads((ROOT / trace['source']['session_path']).read_text())
    assert trace['turns'] == original['turns'] and trace['report'] == original['report']
    assert hashlib.sha256((ROOT / trace['source']['session_path']).read_bytes()).hexdigest() == trace['source']['session_sha256']
    for demo in json.loads((SITE / 'data/evolution-demos.json').read_text())['demos']:
        assert hashlib.sha256((SITE / demo['video']).read_bytes()).hexdigest() == demo['video_sha256']
        assert hashlib.sha256((ROOT / demo['source']).read_bytes()).hexdigest() == demo['source_sha256']
    errors = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=['--no-sandbox', '--enable-unsafe-swiftshader'])
        page = browser.new_page(viewport={'width':1440, 'height':1000})
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(args.url, wait_until='domcontentloaded')
        # Use a blank same-origin page for deterministic parity checks, avoiding live render loops.
        physics = browser.new_page()
        physics.goto(args.url + '/data/evolution/generate.json')
        results = physics.evaluate('''async ({cases, base}) => {
          const {createEvolutionSimulation} = await import(base + '/assets/evolution-physics.js');
          const results = [];
          for (const c of cases) {
            const config = await (await fetch(base + `/data/evolution/${c.key}.json`)).json();
            const s = await createEvolutionSimulation(config);
            let cursor=0, index=0, positionError=0, velocityError=0, stateError=0;
            for (let tick=0; tick<=c.ticks; tick++) {
              while (cursor<c.events.length && c.events[cursor][0]<=s.data.time+1e-8) {
                const [time,kind,name,value] = c.events[cursor++];
                if (kind==='push') s.launch(name,value);
                else if (kind==='place') { const b=s.bodies[name];s.data.qpos.set(value,b.q);s.mj.mj_forward(s.model,s.data); }
                else if (kind==='grip') s.setGrip(name,value);
                else s.releaseGrip();
              }
              if (index<c.trace.length && c.trace[index].tick===tick) {
                const r=c.trace[index++], info=s.info();
                r.qpos.forEach((v,i)=>positionError=Math.max(positionError,Math.abs(s.data.qpos[i]-v)));
                r.qvel.forEach((v,i)=>velocityError=Math.max(velocityError,Math.abs(s.data.qvel[i]-v)));
                if (Math.abs(info.quietUntil-r.quietUntil)>1e-8 || info.pending.length!==r.pending.length || info.pending.some((t,i)=>Math.abs(t-r.pending[i])>1e-8)) stateError++;
              }
              if (tick<c.ticks) s.step();
            }
            s.reset();
            if (s.info().quietUntil!==0 || s.info().pending.length || s.data.time!==0) stateError++;
            results.push({key:c.key,label:c.label,positionError,velocityError,stateError}); s.destroy();
          }
          return results;
        }''', dict(cases=cases, base=args.url.rstrip('/')))
        for result in results:
            print(result, flush=True)
            assert result['positionError'] < 1e-8 and result['velocityError'] < 1e-8 and result['stateError'] == 0, result
        physics.close()
        assert not page.evaluate('performance.getEntriesByType("resource").some(r=>/data\\/evolution\\//.test(r.name))')
        assert not page.evaluate('performance.getEntriesByType("resource").some(r=>/evolution-.*\\.mp4/.test(r.name))')
        demo = page.locator('#evo-demo-video')
        page.locator('#evo-visual').scroll_into_view_if_needed()
        page.wait_for_function('document.querySelector("#evo-demo-video").currentTime>.1')
        assert page.evaluate('LongChangEvolution.view()==="demo" && !LongChangEvolution.current()')
        expect(page.locator('[data-evo-view=demo]')).to_have_attribute('aria-pressed', 'true')
        expect(page.locator('#evo-experiment-view')).to_be_hidden()
        assert demo.evaluate('v=>v.controls && v.loop && v.muted')
        for key in ['mutate','compose','generate']:
            page.locator(f'#evo-tab-{key}').click()
            page.wait_for_function('(key)=>{const v=document.querySelector("#evo-demo-video");return v.currentSrc.endsWith(`evolution-${key}.mp4`) && !v.paused && v.currentTime>.1}', arg=key)
            assert page.evaluate('!LongChangEvolution.current()')
        for quote, selector in [(trace['weakness']['evidence'][0]['quote'], '#evo-trace-error'), (trace['weakness']['contradiction'][0]['quote'], '#evo-trace-correction')]:
            assert page.locator(selector).text_content().strip('“”') == quote
        assert page.locator('#controlled #evolution-results').count() == 0
        assert page.locator('#evolution .evo-workspace #evolution-results tbody tr').count() == 5
        page.locator('.evo-design summary').click()
        expect(page.locator('#evo-trace-error')).to_be_visible()
        page.locator('.evo-design summary').click()
        # Try it yourself opens an untouched live world, with no scripted actions.
        page.locator('#evo-try').click()
        page.wait_for_function('!!LongChangEvolution.current()')
        assert not page.evaluate('LongChangEvolution.current().isRunning()')
        assert page.evaluate('LongChangEvolution.current().getState().time') == 0
        assert demo.evaluate('v=>v.paused')
        expect(page.locator('[data-evo-view=experiment]')).to_have_attribute('aria-pressed', 'true')
        expect(page.locator('#evo-demo-view')).to_be_hidden()
        expect(page.locator('#evo-start')).to_be_hidden()
        canvas = page.locator('#evo-stage canvas.room-canvas')
        canvas.focus(); canvas.press('ArrowRight')
        page.wait_for_function('LongChangEvolution.current().getState().time>.2')
        assert page.evaluate('LongChangEvolution.current().getState().oracle.quietUntil>0')
        page.locator('#evo-play').click()
        before = page.evaluate('LongChangEvolution.current().getState()')
        page.locator('[data-evo-view=demo]').click()
        page.wait_for_function('!document.querySelector("#evo-demo-video").paused')
        page.wait_for_timeout(120)
        assert page.evaluate('LongChangEvolution.current().getState().qpos') == before['qpos']
        # A user pause in Demo survives an Experiment round trip.
        demo.evaluate('v=>v.pause()')
        page.wait_for_timeout(50)
        video_time = demo.evaluate('v=>v.currentTime')
        page.locator('[data-evo-view=experiment]').click()
        assert page.evaluate('LongChangEvolution.current().getState().time') == before['time']
        page.locator('[data-evo-view=demo]').click()
        assert demo.evaluate('v=>v.paused && Math.abs(v.currentTime-'+str(video_time)+')<.01')
        page.locator('[data-evo-view=experiment]').click()
        page.locator('#evo-reset').click()
        assert page.evaluate('LongChangEvolution.current().getState().time') == 0
        # Free hand manipulation changes the spatial gate without launching.
        page.locator('#evo-tab-generate').press('ArrowRight')
        page.wait_for_function('LongChangEvolution.current()?.getState().scene==="mutate"')
        expect(page.locator('#evo-tab-mutate')).to_have_attribute('aria-selected', 'true')
        page.locator('[data-evo-mode=drag]').click()
        page.locator('#evo-stage').scroll_into_view_if_needed()
        start = page.evaluate('LongChangEvolution.current().project("object_2")')
        end = page.evaluate('LongChangEvolution.current().project([3.9,3,.1])')
        page.keyboard.down('Shift'); page.mouse.move(start['x'],start['y']); page.mouse.down()
        page.mouse.move(end['x'],end['y'],steps=12)
        page.wait_for_function('!LongChangEvolution.current().getState().oracle.blocked')
        page.mouse.up(); page.keyboard.up('Shift')
        state = page.evaluate('LongChangEvolution.current().getState()')
        assert state['oracle']['quietUntil'] == 0 and state['oracle']['forceActive']
        page.locator('#evo-tab-compose').click()
        page.wait_for_function('LongChangEvolution.current()?.getState().scene==="compose"')
        page.locator('[data-evo-mode=push]').click()
        canvas.focus(); canvas.press('ArrowDown')
        page.wait_for_function('LongChangEvolution.current().getState().oracle.pending.length===1')
        # Switching views preserves the live experiment and its queued effect.
        page.locator('[data-evo-view=demo]').click()
        page.wait_for_function('!LongChangEvolution.current().isRunning()')
        state = page.evaluate('LongChangEvolution.current().getState()')
        page.wait_for_function('!document.querySelector("#evo-demo-video").paused')
        assert len(state['oracle']['pending']) == 1
        page.wait_for_timeout(120)
        assert page.evaluate('LongChangEvolution.current().getState().time') == state['time']
        page.locator('[data-evo-view=experiment]').click()
        page.wait_for_function('LongChangEvolution.current().isRunning()')
        page.evaluate('window.scrollTo({top:0,behavior:"instant"})')
        page.wait_for_function('!LongChangEvolution.current().isRunning()')
        page.locator('#evo-visual').scroll_into_view_if_needed()
        page.wait_for_function('LongChangEvolution.current().isRunning()')
        page.evaluate('showDiscovery("07")')
        page.wait_for_function('!LongChangEvolution.current().isRunning()')
        page.locator('#exploration-close').click()
        page.wait_for_function('LongChangEvolution.current().isRunning()')
        page.locator('#evo-play').click()
        for key in ['generate','mutate','compose']:
            design = json.loads((SITE / f'data/evolution/{key}-design.json').read_text())
            assert hashlib.sha256((ROOT / design['source']).read_bytes()).hexdigest() == design['source_sha256']
        for width in [1440,1024,768,600,390,320]:
            page.set_viewport_size({'width':width,'height':1000})
            for view in ['demo','experiment']:
                page.locator(f'[data-evo-view={view}]').click()
                assert page.locator('#evolution').evaluate('section=>section.scrollWidth<=innerWidth'), (width,view)
        page.set_viewport_size({'width':1440,'height':1000})
        page.locator('#evolution').screenshot(path='/tmp/evolution-experiment-view.png')
        page.locator('[data-evo-view=demo]').click()
        page.locator('#evolution').screenshot(path='/tmp/evolution-demo-view.png')
        phone = browser.new_page(viewport={'width':390,'height':844}, is_mobile=True, has_touch=True, reduced_motion='reduce')
        phone.on('pageerror',lambda error:errors.append(str(error)))
        phone.goto(args.url+'/#evolution', wait_until='domcontentloaded')
        phone.locator('#evo-visual').scroll_into_view_if_needed()
        phone.wait_for_function('document.querySelector("#evo-demo-video").readyState>=2')
        assert phone.locator('#evo-demo-video').evaluate('v=>v.paused')
        assert phone.evaluate('!LongChangEvolution.current()')
        # Playback remains user-controllable with reduced motion.
        phone.locator('#evo-demo-video').evaluate('v=>v.play()')
        phone.wait_for_function('document.querySelector("#evo-demo-video").currentTime>.1')
        phone.locator('[data-evo-view=experiment]').tap()
        phone.wait_for_function('!!LongChangEvolution.current()')
        assert not phone.evaluate('LongChangEvolution.current().isRunning()')
        phone.locator('#evo-stage').scroll_into_view_if_needed()
        point = phone.evaluate('LongChangEvolution.current().project("red_ball")')
        cdp = phone.context.new_cdp_session(phone)
        cdp.send('Input.dispatchTouchEvent', {'type':'touchStart','touchPoints':[point]})
        cdp.send('Input.dispatchTouchEvent', {'type':'touchMove','touchPoints':[dict(x=point['x']+30,y=point['y']-8)]})
        cdp.send('Input.dispatchTouchEvent', {'type':'touchEnd','touchPoints':[]})
        phone.wait_for_function('LongChangEvolution.current().getState().oracle.quietUntil>0')
        phone.locator('#evo-play').tap()
        phone.locator('#evolution').screenshot(path='/tmp/evolution-experiment-mobile.png')
        phone.route('**/data/evolution/mutate.json', lambda route:route.abort())
        phone.locator('#evo-tab-mutate').tap()
        phone.locator('#evo-stage').scroll_into_view_if_needed()
        expect(phone.locator('#evo-start')).to_have_text('Retry experiment')
        phone.unroute('**/data/evolution/mutate.json')
        phone.locator('#evo-start').tap()
        phone.wait_for_function('LongChangEvolution.current()?.getState().scene==="mutate"')
        phone.evaluate('LongChangEvolution.select("compose");LongChangEvolution.select("generate")')
        phone.wait_for_function('LongChangEvolution.current()?.getState().scene==="generate"')
        assert phone.locator('#evo-stage canvas.room-canvas').count()==1
        # Demo failures can be retried independently of the live world.
        phone.route('**/evolution-compose.mp4',lambda route:route.abort())
        phone.locator('[data-evo-view=demo]').tap(); phone.locator('#evo-tab-compose').tap()
        expect(phone.locator('#evo-demo-error')).to_be_visible()
        phone.unroute('**/evolution-compose.mp4')
        phone.locator('#evo-demo-retry').tap()
        phone.wait_for_function('document.querySelector("#evo-demo-video").currentTime>.1')
        phone.locator('#evolution').screenshot(path='/tmp/evolution-demo-mobile.png')
        phone.evaluate('window.scrollTo({top:0,behavior:"instant"})')
        phone.wait_for_function('document.querySelector("#evo-demo-video").paused')
        phone.locator('#evo-visual').scroll_into_view_if_needed()
        phone.wait_for_function('!document.querySelector("#evo-demo-video").paused')
        browser.close()
    assert not errors, errors
    print('PASS: 7 native/browser experiments, exact trace and design provenance, three Demo videos, independent Experiment state, free push/drag/touch, keyboard tabs, pause/reset, visibility/modal pause, reduced motion, retry, rapid switching and 320–1440 px layouts.')


if __name__ == '__main__':
    main()
