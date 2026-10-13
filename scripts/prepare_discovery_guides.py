"""Project archived object positions through each recorded clip's camera."""
import hashlib
import json

import mujoco
import numpy as np

from prepare_discoveries import BASE, CASES, SITE, frame_camera, load_replay


def main():
    guides = {}
    for case in CASES:
        source = BASE / case['scene'] / 'gpt-6-astra' / f"r{case['repeat']}" / 'T0/replay.bin'
        record = load_replay(source)
        models = {item['version']: mujoco.MjModel.from_xml_string(item['xml'])
                  for item in record['model_versions']}
        for index, chapter in enumerate(case['chapters']):
            frames = sorted((frame for frame in record['state_frames'] if frame['turn'] in chapter['turns']),
                            key=lambda frame: frame['time'])
            camera = frame_camera(record, frames, chapter['targets'], case['id'], index)
            azimuth, elevation = np.deg2rad([camera['azimuth'], camera['elevation']])
            right = np.array([np.sin(azimuth), -np.cos(azimuth), 0])
            up = np.array([-np.cos(azimuth)*np.sin(elevation), -np.sin(azimuth)*np.sin(elevation), np.cos(elevation)])
            scale = 992/camera['vertical_span']
            start, end = frames[0]['time'], frames[-1]['time']
            duration = min(10, max(4, end-start))
            times = np.array([frame['time'] for frame in frames])
            sampled = [frames[int(np.abs(times-time).argmin())]
                       for time in np.linspace(start, end, round(duration*24))]
            tracks = []
            for name in chapter['targets']:
                points = []
                radius = 0
                for frame in sampled:
                    model = models[frame['version']]
                    body = model.body(name).id
                    offset = model.jnt_qposadr[model.body_jntadr[body]]
                    delta = np.array(frame['qpos'][offset:offset+3])-camera['lookat']
                    points.append([round(800+delta@right*scale, 2), round(496-delta@up*scale, 2)])
                    radius = max(radius, float(model.geom_size[model.body_geomadr[body]][0])*scale)
                label = {'red_ball': 'Red', 'green_ball': 'Green', 'blue_ball': 'Blue'}.get(name, 'Test ball')
                color = {'red_ball': '#9d3d32', 'green_ball': '#27734d', 'blue_ball': '#345d9c'}.get(name, '#28645e')
                tracks.append(dict(name=name, label=label, color=color, radius=round(radius, 2), points=points))
            video = f'assets/videos/success-{case["id"]}-{index+1}.mp4'
            guides[video] = dict(
                start=start, end=end, fps=24, camera=camera, tracks=tracks,
                video_sha256=hashlib.sha256((SITE/video).read_bytes()).hexdigest(),
                replay_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    target = SITE/'data/discovery-guides.json'
    target.write_text(json.dumps(guides, separators=(',', ':'))+'\n')
    print(f'Projected {len(guides)} recorded clips; {target.stat().st_size:,} bytes.')


if __name__ == '__main__':
    main()
