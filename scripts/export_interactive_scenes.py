"""Original MuJoCo models and explicit demo preparations for browser interaction."""
import hashlib,json
from pathlib import Path
from render_physics_demos import demonstration,SOURCE,SPECS
from paper_scenes import paper_scene_names

SITE=Path(__file__).resolve().parents[1]

def main():
    folder=SITE/'data/interactive-scenes';folder.mkdir(exist_ok=True)
    names,_=paper_scene_names()
    for definition in SPECS:
        id=definition['id'][:2];world,setup=demonstration(id)
        item=dict(id=id,name=names[id],xml=world.model_xml(),parameters=definition['state'],
                  initial_qpos=world.data.qpos.tolist(),initial_qvel=world.data.qvel.tolist(),
                  entities=definition['entities'],preparation=setup['initial_positions'],
                  source='scenes/base_15.json',source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                  program_sha256=hashlib.sha256(json.dumps(definition['program'],sort_keys=True).encode()).hexdigest(),
                  physics_bounds=[-6,6,-6,6,12])
        (folder/f'{id}.json').write_text(json.dumps(item,separators=(',',':'))+'\n')
    print('Exported 15 native models, source hashes, parameters and explicit initial preparations.')

if __name__=='__main__':main()
