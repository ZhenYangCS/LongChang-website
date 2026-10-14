"""Measure browser presentation, not only the frame rate in the MP4 header."""
import argparse,json
from pathlib import Path
from playwright.sync_api import sync_playwright

MEASURE='''async(seconds)=>{
 const v=document.querySelector('#physics-video'),before=v.getVideoPlaybackQuality(),start=performance.now(),times=[],delays=[];
 let last,handle,done=false,stalls=0;
 const waiting=()=>stalls++;v.addEventListener('waiting',waiting);
 function frame(t,m){if(last)delays.push(t-last);last=t;times.push(m.mediaTime);if(!done)handle=v.requestVideoFrameCallback(frame);}
 handle=v.requestVideoFrameCallback(frame);await new Promise(r=>setTimeout(r,seconds*1000));done=true;v.cancelVideoFrameCallback(handle);v.removeEventListener('waiting',waiting);
 const q=v.getVideoPlaybackQuality(),elapsed=(performance.now()-start)/1000;
 delays.sort((a,b)=>a-b);return {seconds:elapsed,presented:times.length,presentation_fps:times.length/elapsed,decoded:q.totalVideoFrames-before.totalVideoFrames,dropped:q.droppedVideoFrames-before.droppedVideoFrames,stalls,p95_ms:delays[Math.floor(delays.length*.95)],max_ms:delays.at(-1),width:v.videoWidth,height:v.videoHeight,rate:v.playbackRate,source:v.currentSrc};
}'''
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8765');parser.add_argument('--output',default='/tmp/longchang-playback-report.json');args=parser.parse_args();report=[]
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader'])
  page=browser.new_page(viewport={'width':1366,'height':768});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto(args.url+'/#worlds');page.wait_for_load_state('networkidle')
  page.locator('#physics-speed').select_option('1')
  for scene,framing in [('07','detail'),('10','detail'),('13','detail'),('13','room')]:
   page.evaluate('(id)=>showWorld(id)',scene)
   if page.locator('#atlas-physics-view .physics-video-frame').get_attribute('data-framing')!=framing:page.locator('#physics-view').click()
   page.locator('#physics-reset').click();page.locator('#physics-play').click();page.wait_for_function('!document.querySelector("#physics-video").paused');page.wait_for_timeout(350)
   row=page.evaluate(MEASURE,4);row.update(scene=scene,framing=framing);report.append(row);print(json.dumps(row),flush=True)
   page.locator('#physics-play').click()
  # Default 4x must also present smoothly, including the new measured captions.
  page.locator('#physics-speed').select_option('4')
  for scene in ['05','09','10','11','14','15']:
   page.evaluate('(id)=>showWorld(id)',scene);page.locator('#physics-reset').click();page.locator('#physics-play').click();page.wait_for_function('!document.querySelector("#physics-video").paused');page.wait_for_timeout(250)
   row=page.evaluate(MEASURE,2.5);row.update(scene=scene,framing='detail');report.append(row);print(json.dumps(row),flush=True)
   page.locator('#physics-play').click()
  # The recorded plot stays stable while the independent model runs.
  page.locator('[data-atlas-view=physics]').click();page.locator('#demo-rule').scroll_into_view_if_needed();page.wait_for_function('document.querySelector("#oracle-cursor")!==null');page.evaluate('window.savedChartPath=document.querySelector("#oracle-chart path")');page.locator('#atlas-reset').click();page.locator('#atlas-play').click();page.wait_for_timeout(500)
  assert page.evaluate('window.savedChartPath===document.querySelector("#oracle-chart path")')
  browser.close();assert not errors,errors
 Path(args.output).write_text(json.dumps(report,indent=2)+'\n')
 assert all(r['stalls']==0 and r['dropped']<=max(2,r['decoded']*.02) for r in report),report
 print('PASS: no playback stalls, under 2% decoder drops, and a stable measurement chart. Browser presentation timings saved separately.')
if __name__=='__main__':main()
