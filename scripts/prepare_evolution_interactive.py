"""Export accepted evolution models and the exact frozen trace/design references."""
import hashlib
import json
import math
from pathlib import Path

from render_physics_demos import ROOT, SITE, World, load_scene, arrange
from prepare_evolution_demos import RUN, PLANS
from render_clear_scenes import interactive_camera
from tools import FORCE_LIMIT, MOVE_SPEED, GRIP_K, REACH_HEIGHT


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    folder = SITE / 'data/evolution'
    folder.mkdir(exist_ok=True)
    frozen_path = RUN / 'frozen_designs.json'
    frozen = json.loads(frozen_path.read_text())
    source = next(s for s in frozen['sources'] if s['id'] == 'S6')
    session_path = RUN / 'sources/S6/session.json'
    assert sha(session_path) == source['session_sha256']
    session = json.loads(session_path.read_text())
    candidate = frozen['weakness']['candidate']
    for quote in candidate['evidence'] + candidate['contradiction']:
        turn = next(t for t in session['turns'] if t['turn'] == quote['turn'])
        assert quote['quote'] in turn[quote['field']]
    trace = dict(source=source, frozen_designs_source=str(frozen_path.relative_to(ROOT)),
                 frozen_designs_sha256=sha(frozen_path), weakness=candidate,
                 scope='Original notes, actions and returned observations; simulation frames omitted.',
                 **{k: session[k] for k in ['episode_id', 'scene', 'model', 'budget', 'turns', 'report']})
    (folder / 'reference-trace.json').write_text(json.dumps(trace, ensure_ascii=False, indent=2) + '\n')
    # Share the complete-room view, including its scale, with the 15 Worlds.
    camera = interactive_camera()
    for key in ['generate', 'mutate', 'compose']:
        path = RUN / 'generation' / key / 'scene.json'
        definition = json.loads(path.read_text())['scenes'][0]
        world = World(load_scene(path, definition['id']))
        positions = PLANS[key]['positions']
        arrange(world, positions)
        item = dict(id=key, name=PLANS[key]['title'], xml=world.model_xml(),
                    parameters=definition['state'], entities=definition['entities'],
                    initial_qpos=world.data.qpos.tolist(), initial_qvel=world.data.qvel.tolist(),
                    preparation=positions, source=str(path.relative_to(ROOT)), source_sha256=sha(path),
                    program=definition['program'],
                    program_sha256=hashlib.sha256(json.dumps(definition['program'], sort_keys=True).encode()).hexdigest(),
                    grip=dict(force_limit=FORCE_LIMIT, move_speed=MOVE_SPEED, stiffness=GRIP_K, reach_height=REACH_HEIGHT),
                    camera=camera, physics_bounds=[-6, 6, -6, 6, 12])
        (folder / f'{key}.json').write_text(json.dumps(item, separators=(',', ':')) + '\n')
        case = next(c for c in frozen['cases'] if c['case']['operation'] == key)
        design = dict(source=str(frozen_path.relative_to(ROOT)), source_sha256=sha(frozen_path),
                      reference_sources=frozen['sources'], weakness=candidate, **case)
        (folder / f'{key}-design.json').write_text(json.dumps(design, ensure_ascii=False, indent=2) + '\n')
    demos = json.loads((SITE / 'data/evolution-demos.json').read_text())['demos']
    signals = {}
    for demo in demos:
        body = 'object_1' if demo['id'] == 'mutate' else 'red_ball'
        signals[demo['id']] = dict(duration=demo['simulation_duration'], samples=[
            [round(sample['time'], 4), round(math.hypot(*sample['objects'][body]['applied_force'][:2]), 5)]
            for sample in demo['samples']])
    (SITE / 'data/evolution-signals.json').write_text(json.dumps(signals, separators=(',', ':')) + '\n')
    print('Exported three native models, frozen designs, verified source trace and recorded force signals.')


if __name__ == '__main__':
    main()
