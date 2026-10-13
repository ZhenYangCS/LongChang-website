"""Join the verified recorded experiments into one short film per discovery."""
import argparse,hashlib,json,subprocess,tempfile
from pathlib import Path
import imageio_ffmpeg

SITE=Path(__file__).resolve().parents[1]
COPY={
 '07':('The same ball rebounds higher on red than on blue.',[
  'Launch on red: a strong rebound.',
  'Repeat on blue: a much smaller rebound.',
  'Move the same ball to red: the strong rebound returns.']),
 '06':('The sideways force turns with the ball’s motion.',[
  'An eastward push curves south.',
  'A northward push curves east.',
  'An airborne throw matches the predicted deflection.']),
 '14':('Green takes red’s saved launch velocity after 12 seconds, even if red is stopped.',[
  'Green starts moving about 12 seconds after red is pushed.',
  'Hold red still; green still responds later.',
  'Green’s northward velocity is replaced by the saved eastward velocity.']),
 '15':('A push on either ball pauses red’s northward force for about 10 seconds.',[
  'Red still moves north on a raised platform.',
  'After a push, red’s northward drive returns at about 10 seconds.',
  'Push distant blue; red pauses and restarts on the same timer.'])
}

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--ffmpeg',default=imageio_ffmpeg.get_ffmpeg_exe());args=parser.parse_args()
 entries=json.loads((SITE/'data/discoveries.js').read_text().removeprefix('window.DISCOVERIES = ').rstrip(';\n'));films=[]
 folder=SITE/'assets/videos/discoveries';folder.mkdir(exist_ok=True)
 for entry in entries:
  elapsed=0;segments=[];listing=[];dimensions=None
  for chapter,caption in zip(entry['chapters'],COPY[entry['id']][1]):
   path=SITE/chapter['video'];reader=imageio_ffmpeg.read_frames(str(path));meta=next(reader);reader.close()
   signature=(meta['size'],meta['fps']);assert dimensions in [None,signature];dimensions=signature
   segments.append(dict(start=elapsed,end=elapsed+meta['duration'],caption=caption,source=chapter['video']))
   elapsed+=meta['duration'];listing.append("file '"+str(path)+"'")
  target=folder/f'scene-{entry["id"]}.mp4'
  with tempfile.TemporaryDirectory() as temp:
   manifest=Path(temp)/'clips.txt';manifest.write_text('\n'.join(listing)+'\n')
   subprocess.run([args.ffmpeg,'-y','-hide_banner','-loglevel','error','-f','concat','-safe','0','-i',str(manifest),'-c','copy','-movflags','+faststart',str(target)],check=True)
  films.append(dict(id=entry['id'],name=entry['name'],model=entry['model'],repeat=entry['repeat'],episode_id=entry['episode_id'],video=str(target.relative_to(SITE)),poster=entry['chapters'][0]['poster'],duration=elapsed,segments=segments,finding=COPY[entry['id']][0],sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
  print(entry['id'],elapsed,'seconds',flush=True)
 (SITE/'data/discovery-films.js').write_text('window.DISCOVERY_FILMS = '+json.dumps(films,ensure_ascii=False,separators=(',',':'))+';\n')

if __name__=='__main__':main()
