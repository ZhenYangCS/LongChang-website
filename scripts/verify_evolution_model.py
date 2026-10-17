"""Check the Demo explanation, law boundaries, independence and aligned layout."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from playwright.sync_api import expect, sync_playwright

SITE = Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8765');args=parser.parse_args()
    manifest=json.loads((SITE/'data/evolution-demos.json').read_text())
    signals=json.loads((SITE/'data/evolution-signals.json').read_text())
    media=json.loads((SITE/'data/evolution-media.js').read_text().split('=',1)[1].rstrip(';\n'))
    for demo in manifest['demos']:
        for kind in ['video','poster']:
            version=hashlib.sha256((SITE/demo[kind]).read_bytes()).hexdigest()[:12]
            assert media[demo['id']][kind]==f'{demo[kind]}?v={version}'
        body='object_1' if demo['id']=='mutate' else 'red_ball'
        expected=[[round(s['time'],4),round(math.hypot(*s['objects'][body]['applied_force'][:2]),5)] for s in demo['samples']]
        assert signals[demo['id']]['samples']==expected
        assert signals[demo['id']]['duration']==demo['simulation_duration']
    errors=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(args=['--no-sandbox','--enable-unsafe-swiftshader'])
        page=browser.new_page(viewport={'width':1440,'height':1100},reduced_motion='reduce')
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(args.url+'/#evolution',wait_until='domcontentloaded')
        assert page.locator('#evo-explanation').count()==1
        assert page.locator('script[src="assets/evolution-model.js"]').count()==1
        assert page.evaluate('[...document.querySelectorAll("[id]")].filter(e=>e.id.startsWith("evo-")).every((e,i,a)=>a.findIndex(n=>n.id===e.id)===i)')
        expect(page.locator('#evo-explanation')).to_be_visible()
        video=page.locator('#evo-demo-video')
        page.locator('#evo-detail').scroll_into_view_if_needed()
        page.wait_for_function('document.querySelector("#evo-demo-video").readyState>=2')
        video.evaluate('v=>v.pause()')
        def seek(seconds):
            page.locator('#evo-model-progress').evaluate('(e,t)=>{e.value=t*10;e.dispatchEvent(new Event("input",{bubbles:true}));}',seconds)
            return page.evaluate('LongChangEvolution.modelState()')
        for key,options in [('generate',['once','repeat']),('mutate',['inside','outside']),('compose',['none','later'])]:
            page.locator('#evo-tab-'+key).click()
            page.wait_for_function('(k)=>LongChangEvolution.modelState().id===k',arg=key)
            page.wait_for_function('document.querySelector("#evo-demo-video").readyState>=2')
            video.evaluate('v=>v.pause()')
            before=video.evaluate('v=>({src:v.currentSrc,time:v.currentTime,paused:v.paused})')
            assert before['src'].endswith(media[key]['video'])
            assert video.get_attribute('poster')==media[key]['poster']
            assert page.locator('#evo-model-formula math').count()>=1
            for value in options:
                page.locator(f'#evo-model-settings input[type=radio][value="{value}"]').check()
                if key=='generate':
                    assert not seek(9.9)['active']
                    assert seek(10)['active']==(value=='once')
                    assert seek(20)['active']==(value=='once')
                elif key=='mutate':
                    assert not seek(9.9)['active']
                    assert seek(10)['active']==(value=='outside')
                    assert seek(20)['blocked']==(value=='inside')
                else:
                    assert not seek(11.9)['copied']
                    state=seek(12)
                    assert state['copied'] and state['active']==(value=='none')
                    assert seek(18)['active']
                    assert seek(13)['quietUntil']==(18 if value=='later' else 10)
                assert video.evaluate('v=>({src:v.currentSrc,time:v.currentTime,paused:v.paused})')==before
            page.locator('#evo-model-play').click()
            old=page.evaluate('LongChangEvolution.modelState().time')
            page.wait_for_function('(old)=>LongChangEvolution.modelState().time>old',arg=old)
            page.locator('#evo-model-play').click()
            page.locator('#evo-model-reset').click()
            assert page.evaluate('LongChangEvolution.modelState().time')==0
            assert video.evaluate('v=>({src:v.currentSrc,time:v.currentTime,paused:v.paused})')==before
        # The chart is the saved movie data and is unchanged by model controls.
        page.locator('.evo-demo-data').scroll_into_view_if_needed()
        page.wait_for_function('!!document.querySelector("#evo-demo-chart .evo-recorded-series")')
        path=page.locator('.evo-recorded-series').get_attribute('d')
        page.locator('#evo-model-settings input[type=radio][value=none]').check()
        seek(13)
        assert page.locator('.evo-recorded-series').get_attribute('d')==path
        page.locator('#evo-model-fullscreen').click()
        page.wait_for_function('document.fullscreenElement?.id==="evo-explanation"')
        expect(page.locator('#evo-model-settings .model-choice-grid')).to_be_visible()
        page.locator('#evo-model-fullscreen').click()
        page.wait_for_function('!document.fullscreenElement')
        # The additional Demo panel hides for Experiment; neither state overwrites the other.
        snapshot=page.evaluate('LongChangEvolution.modelState()')
        page.locator('[data-evo-view=experiment]').click()
        expect(page.locator('#evo-explanation')).to_be_hidden()
        page.wait_for_function('!!LongChangEvolution.current()')
        assert page.evaluate('LongChangEvolution.current().getState().time')==0
        page.locator('[data-evo-view=demo]').click()
        assert page.evaluate('LongChangEvolution.modelState()')==snapshot
        # Column tops and bottoms match through desktop/tablet breakpoints.
        for width,height in [(1920,1080),(1440,1000),(1366,768),(1280,720),(1100,800),(1024,768),(801,900)]:
            page.set_viewport_size({'width':width,'height':height})
            for view in ['demo','experiment']:
                page.locator(f'[data-evo-view={view}]').click()
                ids=['#evo-detail','#evo-explanation'] if view=='demo' else ['#evo-detail']
                if width>=1100:ids.insert(0,'#evolution .scene-index')
                rects=page.evaluate('(ids)=>ids.map(id=>{const r=document.querySelector(id).getBoundingClientRect();return [r.top,r.bottom]})',ids)
                assert max(r[0] for r in rects)-min(r[0] for r in rects)<1,(width,view,rects)
                assert max(r[1] for r in rects)-min(r[1] for r in rects)<1,(width,view,rects)
        for width in [800,600,390,320]:
            page.set_viewport_size({'width':width,'height':900})
            for view in ['demo','experiment']:
                page.locator(f'[data-evo-view={view}]').click()
                assert page.locator('#evolution').evaluate('e=>e.scrollWidth<=innerWidth'),(width,view)
        page.set_viewport_size({'width':1440,'height':1000});page.locator('[data-evo-view=demo]').click()
        page.locator('#evo-explanation').evaluate('e=>e.scrollTop=0')
        page.locator('#evolution').screenshot(path='/tmp/evolution-explain-verified-desktop.png')
        page.set_viewport_size({'width':390,'height':844});page.locator('#evolution').screenshot(path='/tmp/evolution-explain-verified-mobile.png')
        browser.close()
    assert not errors,errors
    print('PASS: model conditions and 10/12/18-second boundaries, video/state independence, exact recorded signals, fullscreen, single mount, equal desktop/tablet columns and 320–800 px mobile layouts.')


if __name__=='__main__':main()
