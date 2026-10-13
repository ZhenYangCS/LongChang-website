"""Render recorded states for the project page; never step the physics.

Requires the repository's MuJoCo environment. Pass an ffmpeg executable with
--ffmpeg to encode the six selected clips. Existing outputs are skipped.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

os.environ.setdefault("MUJOCO_GL", "egl")
SITE = Path(__file__).resolve().parents[1]
ROOT = SITE.parent
sys.path[:0] = [str(ROOT / "longchang"), str(ROOT / "ACL/materials/_shared")]
import mujoco
import numpy as np
from PIL import Image
from world import load_replay
from rendering import presentation_xml


def styled(xml, width, height, camera=None):
    import xml.etree.ElementTree as ET
    root = ET.fromstring(presentation_xml(xml, width, height, camera=camera))
    root.find("./visual/headlight").attrib.update(ambient=".36 .36 .36", diffuse=".23 .23 .23", specular=".35 .35 .35")
    root.find('./visual/quality').attrib.update(shadowsize="4096", offsamples="4", numslices="100", numstacks="60")
    root.find('.//texture[@name="paper_grid"]').attrib.update(rgb1=".89 .93 .93", rgb2=".80 .86 .88")
    root.find('.//material[@name="paper_floor"]').attrib.update(specular=".08", shininess=".2", emission=".05")
    root.find('.//light[@name="paper_key"]').attrib.update(diffuse=".24 .24 .24", specular=".15 .15 .15")
    # A soft back wall provides spatial context for the wall-contact clip.
    for g in root.iter('geom'):
        if g.get('name') == 'wall_n': g.set('rgba', '.90 .95 .96 1')
    return ET.tostring(root, encoding="unicode")


class RecordedRenderer:
    def __init__(self, record, camera, size=(960, 560), detail_shadows=False):
        self.record = record
        self.camera = mujoco.MjvCamera()
        self.camera.lookat[:] = camera["lookat"]
        self.camera.distance = camera["distance"]
        self.camera.azimuth = camera.get("azimuth", 115)
        self.camera.elevation = camera.get("elevation", -35)
        self.size = size
        self.camera_spec = camera
        self.detail_shadows = detail_shadows
        self.version = None
        self.renderer = None
        self.options = mujoco.MjvOption()
        self.options.sitegroup[:] = 0

    def render(self, frame):
        if self.version != frame['version']:
            if self.renderer: self.renderer.close()
            xml = next(v['xml'] for v in self.record['model_versions'] if v['version'] == frame['version'])
            self.model = mujoco.MjModel.from_xml_string(styled(xml, *self.size, self.camera_spec))
            if self.detail_shadows and self.camera_spec.get('orthographic'):
                # The default shadow map spans the entire workshop. Focus its
                # display bounds on this close-up before allocating the context.
                self.model.stat.center[:] = self.camera_spec['lookat']
                self.model.stat.extent = max(3, self.camera_spec['vertical_span'] * 2)
            self.data = mujoco.MjData(self.model)
            self.renderer = mujoco.Renderer(self.model, self.size[1], self.size[0])
            self.version = frame['version']
        mujoco.mj_setState(self.model, self.data, np.asarray(frame['state']), mujoco.mjtState(self.record['state_spec']))
        mujoco.mj_forward(self.model, self.data)
        self.renderer.update_scene(self.data, self.camera, self.options)
        # Display transform only. Geometry, state and native material colors
        # remain those of the archive.
        linear = self.renderer.render().astype(np.float32) / 255
        srgb = np.where(linear <= .0031308, linear * 12.92, 1.055 * linear ** (1 / 2.4) - .055)
        return np.clip(srgb * 255, 0, 255).astype(np.uint8)

    def close(self):
        if self.renderer: self.renderer.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ffmpeg', required=True)
    ap.add_argument('--only', nargs='*')
    ap.add_argument('--force', action='store_true', help='Regenerate existing media')
    args = ap.parse_args()
    base = ROOT / 'runs/main-15-20260930-022640-2180080'
    paths = {
        'astra': base / '15_launch_suppressed_drift/gpt-6-astra/r2/T0/replay.bin',
        'gemini': base / '15_launch_suppressed_drift/gemini-3.7-flash/r1/T0/replay.bin',
    }
    records = {k: load_replay(v) for k, v in paths.items()}
    ev = json.loads((ROOT / 'ACL/materials/cases/sources/evidence.json').read_text())
    blue_camera = ev['replay_views']['q_blue_test']['camera']
    blue_camera['distance'] = 3.0
    clips = [
        ('astra-notice', 'astra', 37.102, 39.102, dict(lookat=[-1.9,-2.9,.08],distance=2.5), [24]),
        ('astra-investigate', 'astra', 46.222, 58.1, dict(lookat=[-2.38,5.1,.12],distance=3.7,azimuth=160,elevation=-40), [28,29,30]),
        ('astra-test', 'astra', 78.582, 90.582, blue_camera, [35]),
        ('gemini-notice', 'gemini', 2.8, 10.12, dict(lookat=[0,5.25,.13],distance=3.7,azimuth=155,elevation=-32), [2]),
        ('gemini-investigate', 'gemini', 20.24, 22.24, dict(lookat=[0,5.85,.62],distance=3.7,azimuth=105,elevation=-25), [5,6]),
        ('gemini-test', 'gemini', 41.356, 44.356, dict(lookat=[2.55,5.78,.12],distance=4.3,azimuth=105,elevation=-30), [13,14]),
    ]
    manifest = []
    for name, source, start, end, camera, turns in clips:
        dest = SITE / f'assets/videos/{name}.mp4'
        duration = min(12, max(4, end-start))
        manifest.append(dict(id=name, source=str(paths[source].relative_to(ROOT)),
                             start=start, end=end, duration=duration, turns=turns,
                             camera=camera, mode='Nearest recorded state; no simulation or pose interpolation.'))
        if (dest.exists() and not args.force) or (args.only and name not in args.only): continue
        record = records[source]
        fs = sorted([f for f in record['state_frames'] if f['turn'] in turns], key=lambda f:f['time'])
        times = np.asarray([f['time'] for f in fs])
        renderer = RecordedRenderer(record, camera)
        fps = 20
        cmd = [args.ffmpeg, '-loglevel','error','-y','-f','rawvideo','-vcodec','rawvideo',
               '-pix_fmt','rgb24','-s','960x560','-r',str(fps),'-i','-', '-an','-c:v','libx264',
               '-preset','fast','-crf','22','-pix_fmt','yuv420p','-movflags','+faststart',str(dest)]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for n, t in enumerate(np.linspace(start,end,round(duration*fps))):
            frame = fs[int(np.abs(times-t).argmin())]
            pixels = renderer.render(frame)
            if n == 0:
                Image.fromarray(pixels).save(SITE / f'assets/images/{name}.webp', quality=87)
            proc.stdin.write(pixels.tobytes())
        proc.stdin.close()
        assert proc.wait() == 0
        renderer.close()
        print(f'Rendered {name}: {duration:.1f}s', flush=True)
    (SITE / 'data/replays.json').write_text(json.dumps(manifest,indent=2)+'\n')
    # Initial-state views of every scene, recovered from the same main experiment.
    if args.only: return
    for directory in sorted(base.iterdir()):
        if not directory.name[:2].isdigit(): continue
        name = 'scene-' + directory.name[:2]
        dest = SITE / f'assets/images/{name}.webp'
        if dest.exists() and not args.force: continue
        record = load_replay(directory / 'gpt-6-astra/r1/T0/replay.bin')
        frame = record['state_frames'][0]
        spec = record['scene_spec']
        points = []
        for entity in spec['entities']:
            if entity['kind'] not in ('body','fixture'): continue
            size = entity.get('size',[.1])
            extent = np.asarray(size if len(size)==3 else [max(size)]*3)
            for sx in [-1,1]:
                for sy in [-1,1]:
                    for sz in [-1,1]:
                        points.append(np.asarray(entity['position'])+extent*[sx,sy,sz])
        positions = np.asarray(points)
        # Orthographic framing keeps all original object positions while using
        # the available image area. No object is enlarged or relocated.
        az, el = np.deg2rad([115, -55])
        right = np.asarray([-np.sin(az), np.cos(az), 0])
        up = np.asarray([np.cos(az)*np.sin(el), np.sin(az)*np.sin(el), np.cos(el)])
        u, v = positions @ right, positions @ up
        horizontal = float(np.ptp(u)) + .7
        vertical = float(np.ptp(v)) + .7
        span = max(1.8, vertical, horizontal / (1000/600)) * 1.1
        xy = np.linalg.solve(np.asarray([right[:2],up[:2]]),[(u.min()+u.max())/2,(v.min()+v.max())/2])
        center = np.asarray([*xy,0.0])
        cam = dict(lookat=center.tolist(),distance=15,azimuth=115,elevation=-55,
                   orthographic=True,vertical_span=span)
        renderer = RecordedRenderer(record,cam,(1000,600))
        Image.fromarray(renderer.render(frame)).save(dest,quality=87)
        renderer.close()
        print(f'Rendered {name}',flush=True)


if __name__ == '__main__': main()
