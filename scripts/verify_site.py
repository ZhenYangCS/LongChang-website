"""Check portable links, anonymous exports and paper/result consistency."""
import csv
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import zipfile
from urllib.parse import urlsplit
from paper_scenes import paper_scene_names, paper_scene_laws

SITE=Path(__file__).resolve().parents[1]
ROOT=SITE.parent
data=json.loads((SITE/'data/paper.js').read_text().removeprefix('window.LONGCHANG = ').rstrip(';\n'))


class Links(HTMLParser):
    def __init__(self):
        super().__init__();self.links=[];self.ids=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if 'id' in attrs:self.ids.append(attrs['id'])
        for k in ['href','src','poster']:
            if k in attrs:self.links.append(attrs[k])


def main():
    names,_=paper_scene_names()
    assert {s['id']:s['name'] for s in data['scenes']}==names,'Scene labels must match the ACL paper'
    laws,_=paper_scene_laws()
    assert {s['id']:s['law'] for s in data['scenes']}==laws,'Law descriptions must match the ACL appendix'
    p=Links();p.feed((SITE/'index.html').read_text())
    assert len(p.ids)==len(set(p.ids)), 'Duplicate HTML IDs'
    for link in p.links:
        if link.startswith(('http:','https:')):continue
        if link.startswith('#'):
            assert link=='#' or link[1:] in p.ids,link
        else:
            local=urlsplit(link)
            assert (SITE/(local.path or 'index.html')).is_file(),link
            if not local.path and local.fragment:
                assert local.fragment in p.ids,link
    for scene in data['scenes']:assert (SITE/scene['image']).is_file(),scene['image']
    clips=json.loads((SITE/'data/replays.json').read_text())
    assert len(clips)==6
    for clip in clips:
        assert (SITE/f"assets/videos/{clip['id']}.mp4").stat().st_size>1000
        assert (SITE/f"assets/images/{clip['id']}.webp").is_file()
    discoveries=json.loads((SITE/'data/discoveries.js').read_text().removeprefix('window.DISCOVERIES = ').rstrip(';\n'))
    assert [d['id'] for d in discoveries]==['07','06','14','15']
    assert [d['repeat'] for d in discoveries]==[3,1,2,3]
    discovery_sources=json.loads((SITE/'data/discovery-provenance.json').read_text())
    with (ROOT/'ACL/materials/results/sources/gpt_6_1_sol_episodes.csv').open() as f:
        evaluated={r['episode_id']:r for r in csv.DictReader(f)}
    for d,source in zip(discoveries,discovery_sources):
        row=evaluated[d['episode_id']]
        assert row['success']==row['correct']==row['supported']=='True'
        assert d['budget']==100 and d['judge']=='GPT-6.1-Sol'
        assert row['session_sha256']==source['session_sha256']
        assert len(d['chapters'])==3
        for chapter in d['chapters']:
            assert (SITE/chapter['video']).stat().st_size>1000
            assert (SITE/chapter['poster']).is_file()
            assert chapter['start']<chapter['end']
    assert len(discoveries)==4
    css=(SITE/'assets/fonts/fonts.css').read_text()
    for font in re.findall(r'url\(([^)]+)\)',css):assert (SITE/'assets/fonts'/font).is_file()
    assert '+EOF' not in (SITE/'assets/style.css').read_text()
    with (SITE/'downloads/episodes.csv').open() as f:rows=list(csv.DictReader(f))
    assert len(rows)==540
    for m in data['models']:
        all_rows=[r for r in rows if r['model'].lower()==m['name'].lower()]
        altered=[r for r in all_rows if r['control']=='False']
        control=[r for r in all_rows if r['control']=='True']
        assert (len(altered),len(control))==(42,3)
        for key,field in [('D','success'),('C','correct'),('S','supported')]:
            assert round(sum(r[field]=='True' for r in altered)/42*100,1)==m[key],(m['name'],key)
        for r in altered:
            assert (r['success']=='True') == (r['correct']=='True' and r['supported']=='True')
        assert sum(r['success']=='False' for r in control)==m['R']
        def total(key):return sum(int(r[key]) for r in all_rows)
        expected={'L':round(total('turns_used')/45,1),
                  'ES':round(sum(r['early_done']=='True' for r in all_rows)/45*100,1),
                  'CS':sum(int(r['tools_built'])>0 for r in all_rows),
                  'AF':round(total('action_failure_turns')/total('turns_used')*100,1),
                  'CF':round(total('build_failure_turns')/total('build_turns')*100,1) if total('build_turns') else None}
        for key,value in expected.items():assert value==m[key],(m['name'],key,value,m[key])
        for scene,values in m['scenes'].items():
            selected=[r for r in altered if r['scene'].startswith(scene+'_')]
            assert len(selected)==3
            for key,field in [('D','success'),('C','correct'),('S','supported')]:assert values[key]==sum(r[field]=='True' for r in selected)
    controls=[r for r in rows if r['control']=='True']
    assert sum(r['success']=='False' for r in controls)==13
    provenance=json.loads((SITE/'data/provenance.json').read_text())
    for source,digest in provenance['sources'].items():assert hashlib.sha256((ROOT/source).read_bytes()).hexdigest()==digest,source
    for label,source in provenance.get('tables',{}).items():
        text=(ROOT/source['path']).read_text()
        if source['inline']:
            text=re.sub(r'(?<!\\)%[^\n]*','',text)
            text=next(block for block in re.findall(r'\\begin\{table\*?\}.*?\\end\{table\*?\}',text,re.S) if '\\label{'+label+'}' in block)
        assert hashlib.sha256(text.encode()).hexdigest()==source['sha256'],label
    with zipfile.ZipFile(SITE/'downloads/prompts.zip') as z:
        assert {'exploration.txt','report.txt','report_judge.txt'}.issubset(z.namelist())
    with zipfile.ZipFile(SITE/'downloads/longchang-source.zip') as z:
        assert {'LongChang/README.md','LongChang/longchang/run.py','LongChang/scenes/base_15.json'}.issubset(z.namelist())
        assert all('.git/' not in name and '__pycache__/' not in name for name in z.namelist())
    # Public data has no local machine paths or request credentials.
    for folder in ['data','downloads']:
        for path in (SITE/folder).glob('*'):
            if path.suffix not in {'.json','.js','.csv'}:continue
            text=path.read_text()
            assert '/root/' not in text,str(path)
            assert not re.search(r'(api_key|authorization|access_token)\s*["\']?\s*:',text,re.I),str(path)
    for filename in ['model-comparison','controlled-comparisons','scene-evolution']:
        for ext in ['svg','png']:assert (SITE/f'downloads/{filename}.{ext}').stat().st_size>1000
    for filename in ['longchang-15-worlds.mp4','longchang-motion-atlas.mp4']:
        assert (SITE/'downloads'/filename).stat().st_size>1000,filename
    with zipfile.ZipFile(SITE/'downloads/longchang-15-worlds-gifs.zip') as z:
        assert z.testzip() is None
        assert {f'scene-{i:02}.gif' for i in range(1,16)}.issubset(z.namelist())
    for i in range(1,16):
        path=SITE/f'downloads/animated-scenes/scene-{i:02}.gif'
        assert path.read_bytes().startswith(b'GIF89a'),path
    physics=json.loads((SITE/'data/physics.js').read_text().removeprefix('window.PHYSICS_DEMOS = ').rstrip(';\n'))
    assert {scene['id']:scene['name'] for scene in physics}==names
    for scene in physics:
        for key in ['video','poster','record']:assert (SITE/scene[key]).is_file(),scene[key]
        assert scene['scene_source_sha256']==hashlib.sha256((ROOT/scene['scene_source']).read_bytes()).hexdigest()
    for filename in ['longchang-original-physics.mp4','longchang-physics-demonstrations.zip']:
        assert (SITE/'downloads'/filename).stat().st_size>1000,filename
    print('PASS: local links, scene assets, fonts, source hashes and anonymous data exports.')
    print('PASS: all 540 labels, all nine model metrics, 168 model–scene results and 13/36 control rejections.')
    print('PASS: all 12 featured video chapters come from four verified C+S-successful Astra runs.')
    print('PASS: both motion films and all 15 animated scene figures are available.')
    print('PASS: all 15 original-physics demonstrations, source hashes and canonical ACL names match.')


if __name__=='__main__':main()
