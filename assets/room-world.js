import * as T from './vendor/three/three.module.js';
import {RoomEnvironment} from './vendor/three/RoomEnvironment.js';
import {RoundedBoxGeometry} from './vendor/three/RoundedBoxGeometry.js';
import {OrbitControls} from './vendor/three/OrbitControls.js';
import {mergeGeometries} from './vendor/three/BufferGeometryUtils.js';
import loadMujoco from './vendor/mujoco/mujoco.js';

// Native MuJoCo resolves contacts and forces; Three.js renders its state.
export async function createRoom(stage,status) {
  const abort=new AbortController(),timeout=setTimeout(()=>abort.abort(),30000);
  let mj,model,data;
  try {
    const [binary,xml]=await Promise.all([
      fetch(new URL('./vendor/mujoco/mujoco.wasm',import.meta.url),{signal:abort.signal}).then(async r=>{
        if(!r.ok)throw Error('Physics download failed');
        const reader=r.body.getReader(),chunks=[];let size=0;
        while(true){const {done,value}=await reader.read();if(done)break;chunks.push(value);size+=value.length;status(`Loading interaction… ${Math.min(99,Math.round(size/10370402*100))}%`);}
        const bytes=new Uint8Array(size);let offset=0;for(const c of chunks){bytes.set(c,offset);offset+=c.length;}return bytes;
      }),
      fetch(new URL('../data/room.xml',import.meta.url),{signal:abort.signal}).then(r=>{if(!r.ok)throw Error('World unavailable');return r.text();})
    ]);
    mj=await loadMujoco({wasmBinary:binary});model=mj.MjModel.from_xml_string(xml);data=new mj.MjData(model);
  } finally {clearTimeout(timeout);}
  mj.mj_resetDataKeyframe(model,data,0);mj.mj_forward(model,data);
  const renderer=new T.WebGLRenderer({alpha:true,antialias:true,powerPreference:'high-performance'});
  const context=renderer.getContext(),debug=context.getExtension('WEBGL_debug_renderer_info');
  const softwareRenderer=debug&&/SwiftShader|llvmpipe|software/i.test(context.getParameter(debug.UNMASKED_RENDERER_WEBGL));
  renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.setClearColor(0xf8f9f6,0);
  renderer.shadowMap.enabled=true;renderer.shadowMap.type=T.PCFShadowMap;renderer.shadowMap.autoUpdate=false;renderer.shadowMap.needsUpdate=true;
  renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1.15;
  const canvas=renderer.domElement;canvas.className='room-canvas';canvas.tabIndex=0;
  canvas.setAttribute('aria-label','Push or drag objects; use arrow keys to push the selected object.');
  const scene=new T.Scene(),env=new RoomEnvironment(),pmrem=new T.PMREMGenerator(renderer);
  scene.environment=pmrem.fromScene(env,.04).texture;scene.environmentIntensity=.65;env.dispose();pmrem.dispose();
  const camera=new T.OrthographicCamera(-6,6,6,-6,.1,100);camera.up.set(0,0,1);camera.position.set(11.86,-14.134,14.882);camera.lookAt(0,0,2.9);
  scene.add(new T.HemisphereLight(0xe9f5ff,0xa1aaa9,1.6));
  const key=new T.DirectionalLight(0xfff2dc,3.3);key.position.set(-3,-4,10);key.castShadow=true;
  key.shadow.mapSize.set(1024,1024);Object.assign(key.shadow.camera,{left:-6,right:6,top:6,bottom:-6});key.shadow.normalBias=.018;key.shadow.bias=-.0002;key.shadow.radius=4;scene.add(key);
  const fill=new T.DirectionalLight(0xd5eaff,1.2);fill.position.set(5,2,7);scene.add(fill);
  const mat=(color,metalness=0,roughness=.3,clearcoat=.15)=>new T.MeshPhysicalMaterial({color,metalness,roughness,clearcoat,clearcoatRoughness:.18});
  const materials={metal:mat('#456475',.65),silver:mat('#c2cfd6',.75),ramp_mat:mat('#337a6b',.15),bob_mat:mat('#efa12e',.7,.24),red_enamel:mat('#c31e18',0,.18,.65),blue_enamel:mat('#154da0',0,.18,.65),base_trim:mat('#bfd6dd',.7),frame:mat('#6b9faa',.25,.2),front_frame:mat('#94bdc8',.15,.25)};
  // Clear panes need a restrained tint, without multiple full-screen PBR passes.
  materials.glass=new T.MeshBasicMaterial({color:0xb8d9df,transparent:true,opacity:.045,depthWrite:false,side:T.DoubleSide});
  const tile=document.createElement('canvas');tile.width=1024;tile.height=1024;const ctx=tile.getContext('2d');
  for(let y=0;y<8;y++)for(let x=0;x<8;x++){ctx.fillStyle=(x+y)%2?'#bfcfd9':'#ecf2f4';ctx.fillRect(x*128,y*128,128,128);ctx.strokeStyle='#c5d4dd';ctx.lineWidth=1.4;ctx.strokeRect(x*128,y*128,128,128);}
  const texture=new T.CanvasTexture(tile);texture.colorSpace=T.SRGBColorSpace;texture.anisotropy=renderer.capabilities.getMaxAnisotropy();materials.floor_mat=new T.MeshLambertMaterial({color:0xffffff,map:texture});
  const meshes=[],movable=[],geomIds={},groups=new Map(),matrix=new T.Matrix4(),bodyIds={};
  for(const name of ['red_ball','blue_ball','test_block','pendulum_arm','balance_arm']){const b=model.body(name);bodyIds[name]=b.id;b.delete();}
  const bodyMatrix=body=>{const q=data.xquat,p=new T.Vector3().fromArray(data.xpos,body*3);return new T.Matrix4().compose(p,new T.Quaternion(q[body*4+1],q[body*4+2],q[body*4+3],q[body*4]),new T.Vector3(1,1,1));};
  for(let i=0;i<model.ngeom;i++){
    const accessor=model.geom(i),name=accessor.name,s=Array.from(model.geom_size.slice(i*3,i*3+3));accessor.delete();geomIds[name]=i;
    const materialAccessor=model.mat(model.geom_matid[i]),materialName=materialAccessor.name;materialAccessor.delete();let geometry;
    if(model.geom_type[i]===6)geometry=new RoundedBoxGeometry(s[0]*2,s[1]*2,s[2]*2,2,Math.min(.025,Math.min(...s)*.22));
    else if(model.geom_type[i]===2)geometry=new T.SphereGeometry(s[0],40,24);
    else if(model.geom_type[i]===3){geometry=new T.CapsuleGeometry(s[0],s[1]*2,5,16);geometry.rotateX(Math.PI/2);}else continue;
    if(geometry.index)geometry=geometry.toNonIndexed();
    const r=data.geom_xmat,o=i*9,p=data.geom_xpos;
    matrix.set(r[o],r[o+1],r[o+2],p[i*3],r[o+3],r[o+4],r[o+5],p[i*3+1],r[o+6],r[o+7],r[o+8],p[i*3+2],0,0,0,1);
    const body=model.geom_bodyid[i],dynamic=model.body_dofnum[body]>0,glass=materialName==='glass';
    const cast=!glass&&!name.startsWith('corner_')&&!name.startsWith('edge_')&&!name.startsWith('floor');
    const local=dynamic?bodyMatrix(body).invert().multiply(matrix):matrix;
    geometry.applyMatrix4(local);
    const key=`${dynamic?body:0}:${materialName}:${cast}`;
    if(!groups.has(key))groups.set(key,{body:dynamic?body:0,material:materials[materialName]||materials.metal,glass,cast,geometries:[]});
    groups.get(key).geometries.push(geometry);
  }
  for(const group of groups.values()){
    const geometry=mergeGeometries(group.geometries,false);for(const g of group.geometries)g.dispose();
    const mesh=new T.Mesh(geometry,group.material);mesh.userData.body=group.body;mesh.castShadow=group.cast;mesh.receiveShadow=!group.glass;mesh.matrixAutoUpdate=false;
    if(group.glass)mesh.renderOrder=2;scene.add(mesh);meshes.push(mesh);if(group.body)movable.push(mesh);
  }
  let renderMs=0,physicsMs=0;
  function draw(){
    const drawStart=performance.now();
    const p=data.xpos,q=data.xquat;
    for(const mesh of movable){const b=mesh.userData.body;mesh.position.fromArray(p,b*3);mesh.quaternion.set(q[b*4+1],q[b*4+2],q[b*4+3],q[b*4]);mesh.updateMatrix();}
    if(softShadows)updateContactShadows();
    renderer.render(scene,camera);renderMs=performance.now()-drawStart;
  }
  let softShadows=false;
  const contactShadows=[];
  function bakeMatcaps(){
    // Cache the same polished materials into tiny normal-based lighting textures
    // on slower GPUs. Geometry and MuJoCo dynamics remain fully three-dimensional.
    const originalSize=renderer.getSize(new T.Vector2()),ratio=renderer.getPixelRatio(),clear=renderer.getClearColor(new T.Color()),alpha=renderer.getClearAlpha();
    const studio=new T.Scene();studio.environment=scene.environment;studio.environmentIntensity=scene.environmentIntensity;
    const inverse=camera.quaternion.clone().invert();
    for(const light of [key,fill,scene.children.find(o=>o.isHemisphereLight)]){const copy=light.clone();copy.castShadow=false;copy.position.applyQuaternion(inverse);studio.add(copy);}
    const photoCamera=new T.OrthographicCamera(-1,1,1,-1,.1,10);photoCamera.position.z=3;
    const sphere=new T.Mesh(new T.SphereGeometry(1,48,32));studio.add(sphere);const baked=new Map();
    renderer.setPixelRatio(1);renderer.setSize(128,128,false);renderer.setClearColor(0xffffff,1);
    for(const mesh of meshes){
      const material=mesh.material;if(!material.isMeshPhysicalMaterial&&!material.isMeshStandardMaterial)continue;
      if(!baked.has(material)){
        sphere.material=material;renderer.render(studio,photoCamera);
        const c=document.createElement('canvas');c.width=c.height=128;c.getContext('2d').drawImage(canvas,0,0);
        const map=new T.CanvasTexture(c);map.colorSpace=T.SRGBColorSpace;
        baked.set(material,new T.MeshMatcapMaterial({matcap:map,color:0xffffff,toneMapped:false}));
      }
      mesh.material=baked.get(material);
    }
    sphere.geometry.dispose();renderer.setPixelRatio(ratio);renderer.setSize(originalSize.x,originalSize.y,false);renderer.setClearColor(clear,alpha);
  }
  function useContactShadows(){
    if(softShadows)return;softShadows=true;
    for(const mesh of movable)mesh.castShadow=false;
    renderer.shadowMap.enabled=false;
    for(const mesh of meshes)mesh.receiveShadow=false;
    bakeMatcaps();
    const c=document.createElement('canvas');c.width=c.height=96;const context=c.getContext('2d'),gradient=context.createRadialGradient(48,48,2,48,48,47);
    gradient.addColorStop(0,'rgba(35,63,67,.42)');gradient.addColorStop(.4,'rgba(35,63,67,.22)');gradient.addColorStop(1,'rgba(35,63,67,0)');context.fillStyle=gradient;context.fillRect(0,0,96,96);
    const map=new T.CanvasTexture(c);
    for(const [name,radius] of [['blue_ball',.33],['red_ball',.28],['test_block',.3],['pendulum_bob',.25],['pendulum_base',.78],['balance_base',.7]]){
      const shadow=new T.Mesh(new T.PlaneGeometry(1,1),new T.MeshBasicMaterial({map,transparent:true,depthWrite:false,toneMapped:false}));shadow.renderOrder=1;scene.add(shadow);contactShadows.push({name,radius,shadow});
    }
    renderer.shadowMap.needsUpdate=true;
  }
  function updateContactShadows(){
    for(const {name,radius,shadow} of contactShadows){
      const p=name in geomIds?new T.Vector3().fromArray(data.geom_xpos,geomIds[name]*3):new T.Vector3().fromArray(data.xpos,bodyIds[name]*3),height=Math.max(0,p.z-radius);
      shadow.position.set(p.x+.24*height,p.y+.3*height,.009);const size=(radius*2.5+height*.38);shadow.scale.set(size,size,1);shadow.material.opacity=.8*Math.exp(-height*.9);
    }
  }
  const orbit=new OrbitControls(camera,canvas);orbit.target.set(0,0,2.9);orbit.update();orbit.saveState();orbit.enablePan=false;orbit.minZoom=.7;orbit.maxZoom=2;orbit.enableDamping=false;orbit.enabled=false;orbit.addEventListener('change',draw);
  const ray=new T.Raycaster(),pointer=new T.Vector2();let mode='push',drag=null,forces=[],frame=0,last=0,until=0,visible=true,active=false,selected='red_ball';
  const physicsStep=model.opt.timestep;
  let accumulated=0,frameAverage=16.7,qualitySamples=0,quietSince=null;
  const arrow=new T.ArrowHelper(new T.Vector3(0,1,0),new T.Vector3(),0,0x387f68,.22,.13);arrow.visible=false;scene.add(arrow);
  function setRay(e){const r=canvas.getBoundingClientRect();pointer.set((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1);ray.setFromCamera(pointer,camera);}
  function tick(now){
    frame=0;if(!visible||document.hidden)return;const elapsed=Math.max(0,now-last)||16.7;last=now;
    frameAverage=frameAverage*.85+elapsed*.15;
    if(++qualitySamples>=20){
      if(frameAverage>30&&renderer.getPixelRatio()>.65)renderer.setPixelRatio(Math.max(.65,renderer.getPixelRatio()*.8));
      else if(frameAverage>32&&!softShadows)useContactShadows();
      qualitySamples=0;
    }
    const physicsStart=performance.now();
    accumulated=Math.min(.05,accumulated+Math.min(.05,elapsed/1000));
    while(accumulated>=physicsStep){
      data.xfrc_applied.fill(0);forces=forces.filter(f=>data.time<f.end);
      for(const f of forces){const o=f.body*6;for(let k=0;k<3;k++)data.xfrc_applied[o+k]+=f.force[k];const center=new T.Vector3().fromArray(data.xpos,f.body*3),torque=f.point.clone().sub(center).cross(new T.Vector3(...f.force));for(let k=0;k<3;k++)data.xfrc_applied[o+3+k]+=torque.getComponent(k);}
      if(drag?.kind==='drag'){
        const b=drag.body,q=data.xquat,rotation=new T.Quaternion(q[b*4+1],q[b*4+2],q[b*4+3],q[b*4]);
        const offset=drag.localOffset.clone().applyQuaternion(rotation),point=new T.Vector3().fromArray(data.xpos,b*3).add(offset);
        const v=new T.Vector3().fromArray(data.cvel,b*6+3).add(new T.Vector3().fromArray(data.cvel,b*6).cross(offset));
        const f=drag.target.clone().sub(point).multiplyScalar(70).addScaledVector(v,-12);
        if(model.body_dofnum[b]===6)f.z+=model.body_mass[b]*9.81;
        f.clampLength(0,90);f.toArray(data.xfrc_applied,b*6);offset.cross(f).toArray(data.xfrc_applied,b*6+3);
      }
      mj.mj_step(model,data);
      accumulated-=physicsStep;
    }
    physicsMs=performance.now()-physicsStart;
    if(!softShadows)renderer.shadowMap.needsUpdate=true;draw();
    const moving=data.qvel.some(v=>Math.abs(v)>.01);
    if(moving||drag||forces.length)quietSince=null;else if(quietSince===null)quietSince=data.time;
    if(drag||forces.length||data.time<until||quietSince===null||data.time-quietSince<.5)frame=requestAnimationFrame(tick);else active=false;
  }
  function wake(seconds=12){active=true;quietSince=null;until=Math.max(until,data.time+seconds);if(!frame&&visible&&!document.hidden){last=performance.now();frame=requestAnimationFrame(tick);}}
  function push(body,impulse,point){const bid=typeof body==='number'?body:bodyIds[body];forces.push({body:bid,force:impulse.map(v=>v/.12),point:point||new T.Vector3().fromArray(data.xpos,bid*3),end:data.time+.12});wake();}
  const labels={red_ball:'Red ball',blue_ball:'Blue ball',test_block:'Block',pendulum_arm:'Pendulum',balance_arm:'Balance'};
  canvas.addEventListener('pointerdown',e=>{
    if(mode==='view')return;setRay(e);const hit=ray.intersectObjects(movable,false)[0];if(!hit)return;e.preventDefault();canvas.focus({preventScroll:true});const body=hit.object.userData.body;selected=Object.keys(bodyIds).find(n=>bodyIds[n]===body)||selected;canvas.setPointerCapture(e.pointerId);
    const plane=new T.Plane().setFromNormalAndCoplanarPoint(mode==='drag'?camera.getWorldDirection(new T.Vector3()):new T.Vector3(0,0,1),hit.point);
    const q=data.xquat,rotation=new T.Quaternion(q[body*4+1],q[body*4+2],q[body*4+3],q[body*4]);
    drag={kind:mode,pointer:e.pointerId,body,point:hit.point.clone(),target:hit.point.clone(),plane,localOffset:hit.point.clone().sub(new T.Vector3().fromArray(data.xpos,body*3)).applyQuaternion(rotation.invert()),startX:e.clientX,startY:e.clientY};
    status(`${labels[selected]} · ${mode==='push'?'release to push':'release to drop'}`);if(mode==='drag')wake(20);
  });
  canvas.addEventListener('pointermove',e=>{
    if(!drag||drag.pointer!==e.pointerId)return;setRay(e);const p=ray.ray.intersectPlane(drag.plane,new T.Vector3());if(!p)return;
    p.x=T.MathUtils.clamp(p.x,-3.7,3.7);p.y=T.MathUtils.clamp(p.y,-3.7,3.7);p.z=T.MathUtils.clamp(p.z,.15,5.4);drag.target=p;
    if(drag.kind==='push'){const d=p.clone().sub(drag.point);d.z=0;arrow.position.copy(drag.point);if(d.length()>.01){arrow.setDirection(d.clone().normalize());arrow.setLength(Math.min(d.length(),2.5),.22,.13);}arrow.visible=d.length()>.04;draw();}
  });
  canvas.addEventListener('pointerup',e=>{
    if(!drag||drag.pointer!==e.pointerId)return;
    if(drag.kind==='push'){const d=drag.target.clone().sub(drag.point);d.z=0;if(Math.hypot(e.clientX-drag.startX,e.clientY-drag.startY)<5)d.set(0,.7,0);d.multiplyScalar(3).clampLength(0,8);push(drag.body,d.toArray(),drag.point);}
    drag=null;arrow.visible=false;if(canvas.hasPointerCapture(e.pointerId))canvas.releasePointerCapture(e.pointerId);setMode(mode);draw();
  });
  canvas.addEventListener('pointercancel',()=>{drag=null;arrow.visible=false;draw();});
  canvas.addEventListener('keydown',e=>{if(e.key==='Escape'){reset();return;}const d={ArrowUp:[0,2,0],ArrowDown:[0,-2,0],ArrowLeft:[-2,0,0],ArrowRight:[2,0,0],' ':[0,0,3]};if(d[e.key]){e.preventDefault();push(selected,d[e.key]);}});
  function reset(){cancelAnimationFrame(frame);frame=0;active=false;quietSince=null;drag=null;forces=[];until=0;accumulated=0;arrow.visible=false;mj.mj_resetDataKeyframe(model,data,0);mj.mj_forward(model,data);renderer.shadowMap.needsUpdate=true;draw();setMode(mode);}
  function setMode(value){mode=value;orbit.enabled=value==='view';canvas.style.cursor=value==='view'?'grab':'crosshair';status(value==='view'?'Drag to rotate · scroll to zoom':value==='drag'?'Drag an object · release to drop':'Drag to push · tap to nudge');}
  function resize(){const r=stage.getBoundingClientRect(),half=5.8;camera.top=half;camera.bottom=-half;camera.left=-half*r.width/r.height;camera.right=half*r.width/r.height;camera.updateProjectionMatrix();renderer.setSize(r.width,r.height,false);draw();}
  new ResizeObserver(resize).observe(stage);
  new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;if(!visible){cancelAnimationFrame(frame);frame=0;}else if(active)wake(0);}).observe(stage);
  document.addEventListener('visibilitychange',()=>{if(document.hidden){cancelAnimationFrame(frame);frame=0;}else if(active)wake(0);});
  canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();status('Graphics paused. Reload to retry.');cancelAnimationFrame(frame);});
  if(softwareRenderer){renderer.setPixelRatio(Math.min(devicePixelRatio,1));useContactShadows();}
  stage.append(canvas);resize();setMode(mode);
  return {setMode,reset,push,getRenderInfo:()=>({calls:renderer.info.render.calls,triangles:renderer.info.render.triangles,pixelRatio:renderer.getPixelRatio(),frameMs:frameAverage,renderMs,physicsMs,softShadows}),getState:()=>({time:data.time,mode,selected,qpos:Array.from(data.qpos),positions:Object.fromEntries(Object.entries(bodyIds).map(([n,b])=>[n,Array.from(data.xpos.slice(b*3,b*3+3))])),contacts:data.ncon}),project:name=>{const p=(name in geomIds?new T.Vector3().fromArray(data.geom_xpos,geomIds[name]*3):new T.Vector3().fromArray(data.xpos,bodyIds[name]*3)).project(camera),r=stage.getBoundingClientRect();return {x:r.left+(p.x+1)*r.width/2,y:r.top+(1-p.y)*r.height/2};}};
}
