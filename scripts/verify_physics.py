"""Check native demonstration records and their actual browser playback."""
import argparse
import json
import math
from pathlib import Path

from playwright.sync_api import sync_playwright
from paper_scenes import paper_scene_names

SITE=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8765')
    args=parser.parse_args()
    demos=json.loads((SITE/'data/physics.js').read_text().removeprefix('window.PHYSICS_DEMOS = ').rstrip(';\n'))
    names,_=paper_scene_names()
    assert {d['id']:d['name'] for d in demos}==names
    records={d['id']:json.loads((SITE/d['record']).read_text()) for d in demos}
    def samples(number):return records[f'{number:02}']['samples']
    def obj(sample,name):return sample['objects'][name]
    def nearest(number,time):return min(samples(number),key=lambda s:abs(s['time']-time))
    def velocity(sample,name):return math.sqrt(sum(x*x for x in obj(sample,name)['velocity']))
    for s in samples(1):
        assert abs(obj(s,'red_ball')['position'][2]-obj(s,'blue_ball')['position'][2])<1e-8
    assert obj(samples(2)[-1],'red_ball_1')['position'][0]>-.2
    assert all(abs(obj(s,'blue_ball_1')['position'][0]+.8)<1e-8 for s in samples(2))
    assert obj(nearest(3,.64),'red_ball')['position'][2]<.15
    assert obj(nearest(3,.64),'blue_ball')['position'][2]>.5
    max_red=max(obj(s,'red_ball')['position'][2] for s in samples(4))
    max_blue=max(obj(s,'blue_ball')['position'][2] for s in samples(4))
    assert max_blue>max_red*1.5
    assert velocity(nearest(5,.2),'red_ball')<4
    assert obj(samples(6)[-1],'red_ball')['position'][1]<-1
    assert max(obj(s,'gray_ball_1')['position'][2] for s in samples(7) if s['time']>.65)>.8
    assert max(obj(s,'gray_ball_2')['position'][2] for s in samples(7) if s['time']>.65)<.2
    assert max(velocity(s,name) for s in samples(8) for name in ['red_ball','blue_ball'])<2.2
    assert obj(samples(9)[-1],'red_ball')['position'][0]>3.5
    assert velocity(nearest(9,1.28),'red_ball')>velocity(nearest(9,1.24),'red_ball')*2
    assert obj(samples(10)[-1],'red_ball')['position'][0]>2
    assert abs(obj(samples(10)[-1],'blue_ball')['position'][0]+.5)<1e-8
    assert records['11']['contacts'][0]['kind']=='contact_start'
    assert records['11']['contacts'][1]['kind']=='contact_end'
    assert velocity(nearest(11,.24),'blue_ball')>velocity(nearest(11,.22),'blue_ball')*1.5
    assert all(velocity(s,'green_ball')<.01 for s in samples(11))
    color=lambda n,t,name:obj(nearest(n,t),name)['color']
    assert color(12,0,'ball_1')!=color(12,.4,'ball_1')
    assert color(12,0,'ball_1')==color(12,2.2,'ball_1')
    assert len([e for e in records['13']['contacts'] if e['kind']=='contact_start'])==3
    assert max(obj(s,'red_ball')['position'][2] for s in samples(13) if s['time']<3)<.3
    assert max(obj(s,'red_ball')['position'][2] for s in samples(13) if s['time']>3.3)>.8
    assert max(abs(obj(s,'green_ball')['velocity'][0]) for s in samples(14) if s['time']<12)<1e-6
    assert obj(nearest(14,12.1),'green_ball')['velocity'][0]>2
    assert abs(obj(nearest(14,11),'red_ball')['velocity'][0])<1e-6
    assert obj(nearest(15,1.8),'red_ball')['velocity'][1]>.2
    assert abs(obj(nearest(15,10),'red_ball')['velocity'][1])<.02
    assert obj(nearest(15,13),'red_ball')['velocity'][1]>.2

    errors=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1440,'height':1000},reduced_motion='reduce')
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(args.url);page.evaluate('document.fonts.ready')
        assert page.locator('[data-atlas-view="physics"]').get_attribute('aria-pressed')=='true'
        video=page.locator('#physics-video')
        for d in demos:
            page.locator('#scene-tab-'+d['id']).click()
            video.scroll_into_view_if_needed()
            page.wait_for_function('document.querySelector("#physics-video").readyState>=2')
            assert page.locator('#scene-name').inner_text()==names[d['id']]
            assert page.locator('#physics-error').is_hidden()
            page.locator('#physics-play').click();page.wait_for_timeout(150)
            assert video.evaluate('(v)=>v.currentTime>0')
            page.locator('#physics-play').click()
            before=video.evaluate('(v)=>v.currentTime')
            page.wait_for_timeout(100)
            assert video.evaluate('(v)=>v.currentTime')==before
            page.locator('#physics-progress').evaluate('(e)=>{e.value=650;e.dispatchEvent(new Event("input",{bubbles:true}));}')
            page.wait_for_function('Math.abs(document.querySelector("#physics-video").currentTime/document.querySelector("#physics-video").duration-.65)<.02')
            assert page.locator('#physics-values strong').count()==2
            page.locator('[data-atlas-view="motion"]').click()
            assert page.locator('#atlas-canvas').is_visible() and video.is_hidden()
            assert video.evaluate('(v)=>v.paused')
            page.locator('[data-atlas-view="initial"]').click()
            assert page.locator('#scene-image').is_visible()
            page.locator('[data-atlas-view="physics"]').click()
            assert video.is_visible()
            response=page.request.get(args.url+'/'+d['video'],headers={'Range':'bytes=100-199'})
            assert response.status==206 and len(response.body())==100
        page.locator('#atlas-tour').click()
        assert page.locator('#scene-name').inner_text()==names['01']
        page.wait_for_function('document.querySelector("#physics-video").readyState>=2')
        video.evaluate('(v)=>v.currentTime=v.duration-.12')
        page.wait_for_function('document.querySelector("#scene-tab-02").getAttribute("aria-selected")==="true"')
        page.locator('#atlas-tour').click()
        assert video.evaluate('(v)=>v.paused')
        for width in [1440,1024,768,390,360,320]:
            page.set_viewport_size({'width':width,'height':900})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
        assert not errors,errors
        browser.close()
    print('PASS: all 15 canonical names, native physical triggers, contact history and delay records.')
    print('PASS: all native videos play, pause and seek; three views, tours, ranges and mobile layout work.')


if __name__=='__main__':main()
