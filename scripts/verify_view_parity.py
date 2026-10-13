"""Compare actual browser projection with the camera used to render the movie."""
import argparse,json
from pathlib import Path
from playwright.sync_api import sync_playwright

SITE=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8765');args=parser.parse_args()
    shared=json.loads((SITE/'data/shared-room.json').read_text());assert shared['bounds']==[-6,6,-6,6,12] and shared['enclosed']
    for i in range(1,16):
        config=json.loads((SITE/f'data/interactive-scenes/{i:02}.json').read_text())
        assert config['camera']==shared['camera'] and config['physics_bounds']==shared['bounds']
    points=[[x,y,z] for x in [-6,6] for y in [-6,6] for z in [0,12]]+[[0,0,0],[-2.5,0,1.5],[2.5,0,1.5]]
    camera=shared['camera'];max_error=0
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader']);page=browser.new_page();page.goto(args.url+'/#worlds');page.wait_for_load_state('networkidle')
        assert page.locator('#physics-speed').input_value()==page.locator('#scene-live-speed').input_value()=='4'
        for width,height in [(1366,768),(1280,720),(390,844)]:
            page.set_viewport_size({'width':width,'height':height})
            page.locator('[data-atlas-view=physics]').click();
            if page.locator('.physics-video-frame').get_attribute('data-framing')=='detail':page.locator('#scene-zoom-reset').click()
            page.locator('.physics-video-frame').scroll_into_view_if_needed();page.wait_for_timeout(100)
            movie=page.locator('.physics-media').bounding_box();stage=page.locator('.physics-video-frame').bounding_box()
            page.locator('[data-atlas-view=motion]').click();page.wait_for_function('!!window.SceneRoom');page.locator('#scene-live-reset').click();page.wait_for_timeout(100)
            live=page.locator('#scene-live-stage').bounding_box();actual=page.evaluate('(points)=>points.map(p=>SceneRoom.project(p))',points)
            assert abs(stage['height']-live['height'])<1
            for point,screen in zip(points,actual):
                delta=[v-c for v,c in zip(point,camera['position'])]
                u=.5+sum(a*b for a,b in zip(delta,camera['right']))/(camera['span']*1.5)
                v=.5-sum(a*b for a,b in zip(delta,camera['up']))/camera['span']
                # Scroll position can change on a phone; compare within each frame.
                x=movie['x']-stage['x']+u*movie['width'];y=movie['y']-stage['y']+v*movie['height']
                error=max(abs(screen['x']-live['x']-x),abs(screen['y']-live['y']-y));max_error=max(max_error,error)
            assert max_error<1,(width,height,max_error)
        page.set_viewport_size({'width':1366,'height':768});page.locator('[data-atlas-view=physics]').click();page.locator('#physics-fullscreen').click();page.wait_for_function('!!document.fullscreenElement');movie_height=page.locator('.physics-video-frame').bounding_box()['height'];page.locator('#physics-fullscreen').click()
        page.locator('[data-atlas-view=motion]').click();page.locator('#scene-live-fullscreen').click();page.wait_for_function('!!document.fullscreenElement');assert abs(page.locator('#scene-live-stage').bounding_box()['height']-movie_height)<1
        browser.close()
    print(f'PASS: Watch and Try it share all 15 room dimensions and cameras when viewing the whole room; projection differs by at most {max_error:.4f} px across desktop/mobile sizes; fullscreen heights match; defaults are 4×.')

if __name__=='__main__':main()
