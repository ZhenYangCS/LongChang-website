"""Validate compact replays against their original successful experiments."""
import argparse,json,hashlib
from pathlib import Path
import imageio_ffmpeg
from playwright.sync_api import sync_playwright

SITE=Path(__file__).resolve().parents[1]
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8765/');args=parser.parse_args()
 films=json.loads((SITE/'data/discovery-films.js').read_text().removeprefix('window.DISCOVERY_FILMS = ').rstrip(';\n'))
 sources=json.loads((SITE/'data/discoveries.js').read_text().removeprefix('window.DISCOVERIES = ').rstrip(';\n'));by_id={s['id']:s for s in sources}
 for film in films:
  source=by_id[film['id']];assert film['episode_id']==source['episode_id'] and all(source['verdict'].values())
  assert [s['source'] for s in film['segments']]==[s['video'] for s in source['chapters']]
  assert hashlib.sha256((SITE/film['video']).read_bytes()).hexdigest()==film['sha256']
  reader=imageio_ffmpeg.read_frames(str(SITE/film['video']));meta=next(reader);reader.close();assert abs(meta['duration']-film['duration'])<.08
 errors=[]
 with sync_playwright() as p:
  b=p.chromium.launch(headless=True,args=['--no-sandbox']);page=b.new_page(viewport={'width':1366,'height':768});page.on('pageerror',lambda e:errors.append(str(e)));page.goto(args.url);page.wait_for_load_state('networkidle')
  assert page.locator('#success-video').get_attribute('src') is None
  for film in films:
   page.evaluate('(id)=>showDiscovery(id)',film['id']);page.wait_for_function('document.querySelector("#success-video").readyState>=2&&!document.querySelector("#success-video").paused')
   assert page.locator('#discovery-title').inner_text()==film['name']
   assert page.locator('#exploration-dialog button:visible').count()==3
   page.locator('#replay-play').click()
   for segment in film['segments']:
    t=(segment['start']+segment['end'])/2
    page.locator('#replay-progress').evaluate('(e,v)=>{e.value=v;e.dispatchEvent(new Event("input",{bubbles:true}));}',t/film['duration']*1000)
    page.wait_for_function('!document.querySelector("#success-video").seeking')
    assert page.locator('#success-description').inner_text()==segment['caption']
   page.locator('#replay-fullscreen').click();page.wait_for_function('!!document.fullscreenElement');assert page.locator('#success-description').is_visible();page.locator('#replay-fullscreen').click();page.wait_for_function('!document.fullscreenElement')
   page.locator('#exploration-close').click();page.wait_for_function('document.querySelector("#success-video").paused&&!document.querySelector("#success-video").getAttribute("src")')
  page.set_viewport_size({'width':320,'height':740});page.evaluate('showDiscovery("07")');page.wait_for_function('document.querySelector("#success-video").readyState>=2&&!document.querySelector("#success-video").paused');assert page.locator('#exploration-dialog').evaluate('e=>e.scrollWidth<=e.clientWidth');assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');page.keyboard.press('Escape');assert not page.locator('#exploration-dialog').is_visible();b.close()
 assert not errors,errors
 print('PASS: four source-verified films, all twelve captions, autoplay/pause/seek/fullscreen, three-button interface, mobile fit and clean close.')

if __name__=='__main__':main()
