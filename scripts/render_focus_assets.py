"""Render static rooms and crisp spherical lighting for close-up playback."""
import json,sys,hashlib,fcntl,shutil
from pathlib import Path
import bpy
from mathutils import Vector
from blender_oracle import setup,studio


def main():
    job=json.loads(Path(sys.argv[1]).read_text());folder=Path(job['output']);folder.mkdir(parents=True,exist_ok=True)
    scene,balls,mats=setup(job)
    if job.get('hide_room_enclosure'):
        for obj in scene.objects:
            if obj.name.startswith(('Optical glass','Glass vertical edge','Glass top edge','Display plinth')):
                obj.hide_render=True
    bpy.context.view_layer.update()
    signature={}
    for obj in scene.objects:
        if obj.type in {'CAMERA','LIGHT'} or obj.name.startswith(('Display plinth','Porcelain floor','Optical glass','Glass vertical edge','Glass top edge')):
            item=dict(type=obj.type,matrix=[list(row) for row in obj.matrix_world])
            if obj.type=='MESH':item.update(bounds=[list(c) for c in obj.bound_box],materials=[m.name for m in obj.data.materials])
            if obj.type=='CAMERA':item.update(ortho_scale=obj.data.ortho_scale)
            if obj.type=='LIGHT':item.update(energy=obj.data.energy,color=list(obj.data.color),size=obj.data.size,size_y=obj.data.size_y)
            if job.get('hide_room_enclosure') and obj.name.startswith(('Optical glass','Glass vertical edge','Glass top edge','Display plinth')):
                item['hidden_in_demo']=obj.hide_render
            signature[obj.name]=item
    (folder/'room-signature.json').write_text(json.dumps(signature,sort_keys=True))
    mats['gray_enamel'].node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=studio.linear((.38,.47,.51))
    mats['yellow_tile'].node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=studio.linear((.96,.72,.12))
    scene.cycles.samples=job.get('samples',256);scene.cycles.adaptive_threshold=.008;scene.cycles.adaptive_min_samples=min(64,scene.cycles.samples)
    scene.render.film_transparent=True
    if job.get('sprites'):
        for obj in scene.objects:
            if obj.type=='MESH':obj.visible_camera=False
        sphere=next(iter(balls.values()));sphere.visible_camera=True;sphere.location=(0,0,1)
        direction=-Vector(job['camera']['forward']);scene.camera.location=Vector((0,0,1))+direction*30
        scene.camera.data.ortho_scale=.24;scene.render.resolution_x=scene.render.resolution_y=256
        for color in ['red','blue','green','gray']:
            path=folder/f'{color}.png'
            if path.exists():continue
            sphere.data.materials[0]=mats[color+'_enamel'];scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
    else:
        for sphere in balls.values():sphere.hide_render=True
        path=folder/'background.png'
        cache_key=[job['camera'],job['display_bounds'],job['fixtures'],job['width'],job['height'],job.get('enclosed',False),'focus-v2']
        if job.get('hide_room_enclosure'):cache_key.append('hidden-enclosure-v2')
        key=hashlib.sha256(json.dumps(cache_key,sort_keys=True).encode()).hexdigest()
        stamp=folder/'background-key.txt'
        if not path.exists() or not stamp.exists() or stamp.read_text()!=key:
            # Identical rooms share one Cycles render across scenes.
            cache=folder.parents[0]/'background-cache';cache.mkdir(exist_ok=True)
            if folder.name=='room':cache=folder.parents[1]/'background-cache';cache.mkdir(exist_ok=True)
            shared=cache/f'{key}.png'
            with (cache/f'{key}.lock').open('w') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX)
                if not shared.exists():scene.render.filepath=str(shared);bpy.ops.render.render(write_still=True)
                shutil.copyfile(shared,path)
                stamp.write_text(key)
    print('ASSET READY',folder,flush=True)


if __name__=='__main__':main()
