"""Small first-paint scene index; load measurement arrays only on demand."""
import json,base64,io
from pathlib import Path
from PIL import Image

SITE=Path(__file__).resolve().parents[1]
def write(path,text):
    temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(text);temp.replace(path)
def main():
    entries=json.loads((SITE/'data/physics.js').read_text().removeprefix('window.PHYSICS_DEMOS = ').rstrip(';\n'))
    folder=SITE/'data/scene-details';folder.mkdir(exist_ok=True)
    index=[]
    for entry in entries:
        id=entry['id'];write(folder/f'{id}.json',json.dumps(entry,separators=(',',':')))
        item={k:entry[k] for k in ['id','name','video','poster','studio_poster','duration','presentation','video_sha256','record','gif','preview_time','time_map','simulation_duration'] if k in entry}
        item['download_video']=entry.get('download_video',entry['video'])
        for key in ['detail_video','detail_video_sha256','detail_poster','detail_dimensions','detail_crop','context_poster']:
            if key in entry:item[key]=entry[key]
        preview=Image.open(SITE/entry['studio_poster']).convert('RGBA');preview.thumbnail((200,134))
        background=Image.new('RGBA',preview.size,'#f5f8f7');background.alpha_composite(preview)
        buffer=io.BytesIO();background.convert('RGB').save(buffer,format='WEBP',quality=48)
        item['preview']='data:image/webp;base64,'+base64.b64encode(buffer.getvalue()).decode()
        if entry.get('detail_poster'):
            im=Image.open(SITE/entry['detail_poster']).convert('RGB');im.thumbnail((240,120));buffer=io.BytesIO();im.save(buffer,format='WEBP',quality=62)
            item['detail_preview']='data:image/webp;base64,'+base64.b64encode(buffer.getvalue()).decode()
        item['details']=f'data/scene-details/{id}.json';item['phases']=[]
        last=None
        for i,sample in enumerate(entry['timeline']):
            state=sample.get('simple_state','')
            if state!=last:item['phases'].append([i/entry['fps'],state]);last=state
        index.append(item)
    write(SITE/'data/scene-index.js','window.SCENE_INDEX = '+json.dumps(index,separators=(',',':'))+';\n')
    print('Published compact index:',(SITE/'data/scene-index.js').stat().st_size,'bytes')
if __name__=='__main__':main()
