"""Render interactive poses in the exact editable Figure 1 Blender scene."""
import argparse
import json
from pathlib import Path
import time
import bpy
from mathutils import Matrix,Vector
from bpy_extras.object_utils import world_to_camera_view


def main():
    parser=argparse.ArgumentParser();parser.add_argument('job');args=parser.parse_args()
    job=json.loads(Path(args.job).read_text());bpy.ops.wm.open_mainfile(filepath=job['blend'])
    scene=bpy.context.scene;scene.cycles.samples=job['samples'];scene.cycles.adaptive_min_samples=32
    scene.cycles.adaptive_threshold=.02;scene.cycles.use_denoising=True;scene.render.use_persistent_data=True
    scene.render.threads_mode='FIXED';scene.render.threads=job['threads']
    scene.render.resolution_x=job['width'];scene.render.resolution_y=job['height'];scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
    out=Path(job['output']);out.mkdir(exist_ok=True)
    frames=[];crop=job['crop']
    # A static silhouette clips the video's background to the glass-room image.
    outline=[]
    for obj in bpy.data.objects:
        if obj.type=='MESH' and obj.name.startswith(('floor_base','wall_','glass_ceiling')):
            for corner in obj.bound_box:
                q=world_to_camera_view(scene,scene.camera,obj.matrix_world@Vector(corner))
                outline.append(((q.x-crop[0])/(crop[2]-crop[0]),(1-q.y-crop[1])/(crop[3]-crop[1])))
    points=sorted(set(outline))
    def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lower=[];upper=[]
    for point in points:
        while len(lower)>=2 and cross(lower[-2],lower[-1],point)<=0:lower.pop()
        lower.append(point)
    for point in reversed(points):
        while len(upper)>=2 and cross(upper[-2],upper[-1],point)<=0:upper.pop()
        upper.append(point)
    (out/'outline.json').write_text(json.dumps(lower[:-1]+upper[:-1])+'\n')
    for index,frame in enumerate(job['frames']):
        for name,pose in frame['poses'].items():
            transform=Matrix(pose['rotation']).to_4x4();transform.translation=Vector(pose['position'])
            bpy.data.objects[name].matrix_world=transform
        bpy.context.view_layer.update()
        target=bpy.data.objects[job['target']].matrix_world.translation
        point=world_to_camera_view(scene,scene.camera,target)
        frames.append(dict(value=frame['value'],x=(point.x-crop[0])/(crop[2]-crop[0]),y=(1-point.y-crop[1])/(crop[3]-crop[1])))
        path=out/f'{index:03}.png'
        if not path.exists():
            start=time.time();scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
            print(f"ROOM {job['id']} {index+1}/{len(job['frames'])} {time.time()-start:.1f}s",flush=True)
    (out/'projection.json').write_text(json.dumps(frames)+'\n')


if __name__=='__main__':main()
