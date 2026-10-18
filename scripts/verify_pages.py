"""Exercise the prebuilt site under a GitHub Pages-style repository path."""
import argparse
from urllib.parse import urlsplit
from playwright.sync_api import expect, sync_playwright

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--url',required=True);args=parser.parse_args();url=args.url.rstrip('/')+'/'
 errors=[];bad=[];requests=[]
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader']);page=browser.new_page(viewport={'width':1366,'height':768})
  page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url));page.on('response',lambda r:bad.append((r.status,r.url)) if r.status>=400 else None)
  page.goto(url);page.wait_for_load_state('networkidle');page.evaluate('document.fonts.ready')
  assert page.locator('.site-header').count()==0 and page.locator('#hero-title').text_content()=='LongChang'
  assert page.locator('.hero-actions a').all_text_contents()==['Paper','Code','BibTeX']
  assert not page.evaluate('performance.getEntriesByType("resource").some(r=>/\\.(mp4|wasm)/.test(r.name))')
  logo=page.locator('.hero-logo');assert logo.bounding_box()['x']<page.locator('.title-accent').bounding_box()['x']
  logo.locator('.logo-eye').evaluate_all('els=>els.forEach(e=>e.getAnimations().forEach(a=>{a.pause();a.currentTime=4080;}))')
  blink=logo.locator('.logo-eye').evaluate_all('els=>els.map(e=>new DOMMatrix(getComputedStyle(e).transform).d)');assert len(blink)==2 and max(blink)<.3 and abs(blink[0]-blink[1])<.001
  logo.locator('.logo-eye').evaluate_all('els=>els.forEach(e=>e.getAnimations().forEach(a=>{a.currentTime=0;a.play();}))')
  budget=page.locator('[data-comparison=budget]');assert budget.get_attribute('data-primary-metric')=='L'
  assert budget.locator('p').inner_text()=='Mean turns used'
  assert budget.locator('.controlled-pair [data-metric="L"]').all_text_contents()==['42.2','41.4']
  page.locator('#scene-tab-10').click();page.wait_for_function('document.querySelector("#physics-video").readyState>=2&&!document.querySelector("#physics-video").paused');page.locator('#physics-play').click()
  page.locator('#physics-progress').evaluate('e=>{e.value=650;e.dispatchEvent(new Event("input",{bubbles:true}));}');page.wait_for_function('!document.querySelector("#physics-video").seeking')
  assert page.locator('#physics-video').evaluate('v=>v.currentSrc').startswith(url)
  page.evaluate('showWorld("07")');page.locator('[data-atlas-view=motion]').click();page.wait_for_function('window.SceneRoom?.getState().scene==="07"',timeout=60000)
  assert not page.evaluate('crossOriginIsolated'),'The runtime must also work without isolation headers.'
  page.locator('#scene-live-reset').click();page.locator('[data-scene-mode=drag]').click();point=page.evaluate('SceneRoom.project("gray_ball_1")')
  page.mouse.move(point['x'],point['y']);page.mouse.down();page.mouse.move(point['x'],point['y']-45,steps=10);page.wait_for_function('SceneRoom.getState().positions.gray_ball_1[2]>2');page.mouse.up()
  page.locator('[data-atlas-view=physics]').click();page.locator('#demo-rule').scroll_into_view_if_needed();page.wait_for_function('!document.querySelector("#oracle-chart-wrap").hidden');page.evaluate('LongChangAtlas.setParameter(3,{preview:true})');assert 'Red 2.43' in page.locator('#atlas-value').inner_text()
  page.evaluate('showDiscovery("07")');page.wait_for_function('document.querySelector("#success-video").readyState>=2&&!document.querySelector("#success-video").paused');assert page.locator('#exploration-dialog button:visible').count()==3;page.locator('#replay-play').click()
  page.locator('#replay-progress').evaluate('e=>{e.value=750;e.dispatchEvent(new Event("input",{bubbles:true}));}')
  page.wait_for_function('["success-video","comparison-video"].every(id=>{const v=document.getElementById(id);return v.readyState>=2&&!v.seeking&&v.currentTime>0&&v.paused;})')
  assert page.locator('#replay-progress').input_value()=='750'
  assert page.locator('#success-description').inner_text().strip()
  page.locator('#exploration-close').click()
  # The evolved models and gzip audit records must also work under a subpath.
  page.locator('[data-evo-view=experiment]').click()
  page.wait_for_function('!!window.LongChangEvolution.current()',timeout=60000)
  assert page.evaluate('LongChangEvolution.current().getState().scene')=='generate'
  page.locator('[data-evo-view=demo]').click()
  page.wait_for_function('document.querySelector("#evo-demo-video").readyState>=2')
  assert page.locator('#evo-demo-video').evaluate('v=>v.currentSrc').startswith(url)
  page.locator('#evo-demo-video').evaluate('v=>v.pause()')
  page.evaluate('showResultEvidence("GPT-6-Astra","07")')
  expect(page.locator('#evidence-content')).to_be_visible()
  page.locator('#evidence-full-tab').click()
  page.locator('[data-evidence-turn]').first.click()
  expect(page.locator('#evidence-turn-content')).to_be_visible(timeout=30000)
  assert page.locator('#evidence-turn-select option').count()>0
  page.keyboard.press('Escape')
  with page.expect_download() as download:
   page.locator('#evidence-record-download').click()
  assert download.value.failure() is None
  assert download.value.url.startswith(url)
  page.keyboard.press('Escape')
  assert len([r for r in requests if urlsplit(r).path.endswith('.wasm')])==1
  for width in [1440,1024,768,390,320]:
   page.set_viewport_size({'width':width,'height':900});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
  reduced=browser.new_page(reduced_motion='reduce');reduced.goto(url);assert reduced.locator('.logo-eye').first.evaluate('e=>getComputedStyle(e).animationName')=='none'
  browser.close()
 assert not errors,errors
 assert not bad,bad
 base=urlsplit(url)
 assert all(urlsplit(r).netloc!=base.netloc or r.startswith(url) for r in requests),[r for r in requests if urlsplit(r).netloc==base.netloc and not r.startswith(url)]
 print('PASS: static repository subpath, local fonts/assets, synchronized logo, budget emphasis, video seek, shared WASM without isolation headers, dragging, evolution, model controls, replay modal, gzip records, ZIP downloads and mobile layout. No backend requests or failed resources.')

if __name__=='__main__':main()
