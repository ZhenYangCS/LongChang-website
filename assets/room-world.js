import * as T from './vendor/three/three.module.js';
import {RoomEnvironment} from './vendor/three/RoomEnvironment.js';
import {RoundedBoxGeometry} from './vendor/three/RoundedBoxGeometry.js';
import {OrbitControls} from './vendor/three/OrbitControls.js';
import {mergeGeometries} from './vendor/three/BufferGeometryUtils.js';
import {getMujoco} from './mujoco-runtime.js';


export async function createRoom(stage,status,options={}) {
  const simulation=options.simulation||null,live=Boolean(simulation);let mj,model,data,disposed=false;
  if(live)({mj,model,data}=simulation);
  else{
    const [runtime,response]=await Promise.all([getMujoco(status),fetch(new URL('../data/room.xml',import.meta.url),{signal:AbortSignal.timeout(30000)})]);
    if(!response.ok)throw Error('World unavailable');mj=runtime;model=mj.MjModel.from_xml_string(await response.text());data=new mj.MjData(model);mj.mj_resetDataKeyframe(model,data,0);
  }
  mj.mj_forward(model,data);
  const renderer=new T.WebGLRenderer({alpha:true,antialias:true,powerPreference:'high-performance'});
  const context=renderer.getContext(),debug=context.getExtension('WEBGL_debug_renderer_info');
  const softwareRenderer=debug&&/SwiftShader|llvmpipe|software/i.test(context.getParameter(debug.UNMASKED_RENDERER_WEBGL));
  const targetPixelRatio=Math.min(devicePixelRatio,softwareRenderer?1:2);
  renderer.setPixelRatio(targetPixelRatio);renderer.setClearColor(0xf8f9f6,0);
  renderer.shadowMap.enabled=true;renderer.shadowMap.type=T.PCFSoftShadowMap;renderer.shadowMap.autoUpdate=false;renderer.shadowMap.needsUpdate=true;
  renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1.15;
  const canvas=renderer.domElement;canvas.className='room-canvas';canvas.tabIndex=0;
  canvas.setAttribute('aria-label','Push or drag objects; hold Ctrl or Command while scrolling to zoom. Use arrow keys to push the selected object.');
  // Leave ordinary wheel events to the page. OrbitControls receives deliberate
  // modifier gestures, trackpad pinches and wheel input inside fullscreen only.
  canvas.addEventListener('wheel',event=>{
    if(!event.ctrlKey&&!event.metaKey&&!document.fullscreenElement?.contains(canvas))event.stopImmediatePropagation();
  },{capture:true,passive:true});
  const scene=new T.Scene(),env=new RoomEnvironment(),pmrem=new T.PMREMGenerator(renderer);
  scene.environment=pmrem.fromScene(env,.04).texture;scene.environmentIntensity=.65;env.dispose();pmrem.dispose();
  const ceiling=live?simulation.config.physics_bounds[4]:5.8,roomCenter=live?ceiling/2:2.9;
  const camera=new T.OrthographicCamera(-6,6,6,-6,.1,100);camera.up.set(0,0,1);
  const lookTarget=live?new T.Vector3().fromArray(simulation.config.camera.position).addScaledVector(new T.Vector3().fromArray(simulation.config.camera.forward),30):new T.Vector3(0,0,roomCenter);
  if(live)camera.position.fromArray(simulation.config.camera.position);else camera.position.set(11.86,-14.134,14.882);camera.lookAt(lookTarget);
  scene.add(new T.HemisphereLight(0xe9f5ff,0xa1aaa9,1.6));
  const key=new T.DirectionalLight(0xfff2dc,3.3);key.position.set(-3,-4,10);key.castShadow=true;
  const shadowSize=softwareRenderer?1024:2048;
  key.shadow.mapSize.set(shadowSize,shadowSize);Object.assign(key.shadow.camera,{left:-6,right:6,top:6,bottom:-6});key.shadow.normalBias=.018;key.shadow.bias=-.0002;key.shadow.radius=4;scene.add(key);
  const fill=new T.DirectionalLight(0xd5eaff,1.2);fill.position.set(5,2,7);scene.add(fill);
  const mat=(color,metalness=0,roughness=.3,clearcoat=.15)=>new T.MeshPhysicalMaterial({color,metalness,roughness,clearcoat,clearcoatRoughness:.18});
  const materials={metal:mat('#456475',.65),silver:mat('#c2cfd6',.75),ramp_mat:mat('#337a6b',.15),bob_mat:mat('#efa12e',.7,.24),red_enamel:mat('#c31e18',0,.18,.65),blue_enamel:mat('#154da0',0,.18,.65),base_trim:mat('#bfd6dd',.7),frame:mat('#6b9faa',.25,.2),front_frame:mat('#94bdc8',.15,.25)};
  Object.assign(materials,{green_enamel:mat('#268452',0,.22,.5),gray_enamel:mat('#506978',.05,.23),yellow_enamel:mat('#dfb840'),brown_enamel:mat('#926942'),red_tile:new T.MeshLambertMaterial({color:'#ce786c'}),blue_tile:new T.MeshLambertMaterial({color:'#749bb8'}),yellow_tile:new T.MeshLambertMaterial({color:'#e0bd52'}),gray_tile:new T.MeshLambertMaterial({color:'#9daeb0'})});
  const palette={red:[.9,.1,.1],blue:[.1,.1,.9],green:[.1,.8,.2],yellow:[.9,.9,.1],brown:[.6,.4,.2],gray:[.55,.55,.55]};
  function geomColor(g){const c=model.geom_rgba.subarray(g*4,g*4+3);return Object.keys(palette).sort((a,b)=>Math.hypot(...palette[a].map((v,k)=>v-c[k]))-Math.hypot(...palette[b].map((v,k)=>v-c[k])))[0];}
  const bakedMaterials=new Map();

  materials.glass=new T.MeshBasicMaterial({color:0xb8d9df,transparent:true,opacity:.045,depthWrite:false,side:T.DoubleSide});
  const tile=document.createElement('canvas');tile.width=1024;tile.height=1024;const ctx=tile.getContext('2d');
  for(let y=0;y<8;y++)for(let x=0;x<8;x++){ctx.fillStyle=(x+y)%2?'#bfcfd9':'#ecf2f4';ctx.fillRect(x*128,y*128,128,128);ctx.strokeStyle='#c5d4dd';ctx.lineWidth=1.4;ctx.strokeRect(x*128,y*128,128,128);}
  const texture=new T.CanvasTexture(tile);texture.colorSpace=T.SRGBColorSpace;texture.anisotropy=renderer.capabilities.getMaxAnisotropy();materials.floor_mat=new T.MeshLambertMaterial({color:0xffffff,map:texture});
  const meshes=[],movable=[],pickGeoms=[],geomIds={},groups=new Map(),matrix=new T.Matrix4(),bodyIds={};
  const pickHistory=[];
  for(let i=1;i<model.nbody;i++){if(model.body_dofnum[i]<=0)continue;const b=model.body(i);bodyIds[b.name]=i;b.delete();}
  const bodyMatrix=body=>{const q=data.xquat,p=new T.Vector3().fromArray(data.xpos,body*3);return new T.Matrix4().compose(p,new T.Quaternion(q[body*4+1],q[body*4+2],q[body*4+3],q[body*4]),new T.Vector3(1,1,1));};
  for(let i=0;i<model.ngeom;i++){
    const accessor=model.geom(i),name=accessor.name,s=Array.from(model.geom_size.slice(i*3,i*3+3));accessor.delete();geomIds[name]=i;
    if(live&&(name.startsWith('wall_')||name==='ceiling'))continue;
    let materialName;const matid=model.geom_matid[i];
    if(matid>=0){const accessor=model.mat(matid);materialName=accessor.name;accessor.delete();}
    else materialName=name==='floor'?'floor_mat':geomColor(i)+(model.geom_bodyid[i]>0?'_enamel':'_tile');
    let geometry;
    if(model.geom_type[i]===0)geometry=new T.BoxGeometry(12,12,.034);
    else if(model.geom_type[i]===6)geometry=new RoundedBoxGeometry(s[0]*2,s[1]*2,s[2]*2,2,Math.min(.025,Math.min(...s)*.22));
    else if(model.geom_type[i]===2)geometry=new T.SphereGeometry(s[0],40,24);
    else if(model.geom_type[i]===3){geometry=new T.CapsuleGeometry(s[0],s[1]*2,5,16);geometry.rotateX(Math.PI/2);}else continue;
    if(geometry.index)geometry=geometry.toNonIndexed();
    const r=data.geom_xmat,o=i*9,p=data.geom_xpos;
    matrix.set(r[o],r[o+1],r[o+2],p[i*3],r[o+3],r[o+4],r[o+5],p[i*3+1],r[o+6],r[o+7],r[o+8],p[i*3+2],0,0,0,1);
    if(live&&name==='floor')matrix.elements[14]=-.017;
    const body=model.geom_bodyid[i],dynamic=model.body_dofnum[body]>0,glass=materialName==='glass';
    if(dynamic)pickGeoms.push({geom:i,body,radius:s[0]});
    const cast=!glass&&!name.startsWith('corner_')&&!name.startsWith('edge_')&&!name.startsWith('floor');
    const local=dynamic?bodyMatrix(body).invert().multiply(matrix):matrix;
    geometry.applyMatrix4(local);
    const key=`${dynamic?body:0}:${materialName}:${cast}`;
    if(!groups.has(key))groups.set(key,{body:dynamic?body:0,material:materials[materialName]||materials.metal,glass,cast,colorSource:live&&dynamic?i:null,geometries:[]});
    groups.get(key).geometries.push(geometry);
  }
  for(const group of groups.values()){
    const geometry=mergeGeometries(group.geometries,false);for(const g of group.geometries)g.dispose();
    const mesh=new T.Mesh(geometry,group.material);mesh.userData.body=group.body;mesh.userData.colorSource=group.colorSource;mesh.castShadow=group.cast;mesh.receiveShadow=!group.glass;mesh.matrixAutoUpdate=false;
    if(group.glass)mesh.renderOrder=2;scene.add(mesh);meshes.push(mesh);if(group.body)movable.push(mesh);
  }
  if(live){

    const add=(geometry,material)=>{const m=new T.Mesh(geometry,material);scene.add(m);meshes.push(m);return m;};
    const base=add(new T.BoxGeometry(12.08,12.08,.15),materials.metal);base.position.z=-.095;
    const panes=[],rails=[],z=ceiling;
    for(const sign of [-1,1]){
      panes.push(new T.BoxGeometry(.024,12.024,z).translate(sign*6.012,0,z/2),new T.BoxGeometry(12.024,.024,z).translate(0,sign*6.012,z/2));
      rails.push(new T.BoxGeometry(.0104,12,.0104).translate(sign*6,0,z),new T.BoxGeometry(12,.0104,.0104).translate(0,sign*6,z));
      for(const other of [-1,1])rails.push(new T.BoxGeometry(.016,.016,z).translate(sign*6,other*6,z/2));
    }
    const glass=add(mergeGeometries(panes),materials.glass);glass.renderOrder=2;add(mergeGeometries(rails),materials.frame);
    const roof=add(new T.BoxGeometry(12,12,.024),new T.MeshBasicMaterial({color:0xb8dce5,transparent:true,opacity:.09,depthWrite:false,side:T.DoubleSide}));roof.name='Native ceiling glass';roof.position.z=z+.012;roof.renderOrder=2;

    const edgePoints=[];
    for(const x of [-6,6])for(const y of [-6,6])edgePoints.push(new T.Vector3(x,y,0),new T.Vector3(x,y,z));
    for(const height of [0,z])for(const side of [-6,6])edgePoints.push(new T.Vector3(-6,side,height),new T.Vector3(6,side,height),new T.Vector3(side,-6,height),new T.Vector3(side,6,height));
    const outline=new T.LineSegments(new T.BufferGeometry().setFromPoints(edgePoints),new T.LineBasicMaterial({color:0x8aabb6,transparent:true,opacity:.65,depthWrite:false}));outline.renderOrder=3;scene.add(outline);
    for(const g of [...panes,...rails])g.dispose();
  }
  let renderMs=0,physicsMs=0;
  function draw(){
    if(disposed)return;const drawStart=performance.now();
    const p=data.xpos,q=data.xquat;
    for(const mesh of movable){const b=mesh.userData.body;mesh.position.fromArray(p,b*3);mesh.quaternion.set(q[b*4+1],q[b*4+2],q[b*4+3],q[b*4]);mesh.updateMatrix();if(live&&mesh.userData.colorSource!==null){const material=materials[geomColor(mesh.userData.colorSource)+'_enamel'];mesh.material=bakedMaterials.get(material)||material;}}
    if(softShadows)updateContactShadows();
    renderer.render(scene,camera);rememberPickPositions();updateMarker();renderMs=performance.now()-drawStart;options.onFrame?.(data.time);
  }
  let softShadows=false;
  const contactShadows=[];
  function bakeMatcaps(){


    const originalSize=renderer.getSize(new T.Vector2()),ratio=renderer.getPixelRatio(),clear=renderer.getClearColor(new T.Color()),alpha=renderer.getClearAlpha();
    const studio=new T.Scene();studio.environment=scene.environment;studio.environmentIntensity=scene.environmentIntensity;
    const inverse=camera.quaternion.clone().invert();
    for(const light of [key,fill,scene.children.find(o=>o.isHemisphereLight)]){const copy=light.clone();copy.castShadow=false;copy.position.applyQuaternion(inverse);studio.add(copy);}
    const photoCamera=new T.OrthographicCamera(-1,1,1,-1,.1,10);photoCamera.position.z=3;
    const sphere=new T.Mesh(new T.SphereGeometry(1,48,32));studio.add(sphere);const baked=bakedMaterials;
    renderer.setPixelRatio(1);renderer.setSize(256,256,false);renderer.setClearColor(0xffffff,1);
    for(const mesh of meshes){
      const material=mesh.material;if(!material.isMeshPhysicalMaterial&&!material.isMeshStandardMaterial)continue;
      if(!baked.has(material)){
        sphere.material=material;renderer.render(studio,photoCamera);
        const c=document.createElement('canvas');c.width=c.height=256;c.getContext('2d').drawImage(canvas,0,0);
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
    const shadowObjects=live?Object.values(simulation.bodies).map(b=>[b.name,model.geom_size[b.g*3]]):[['blue_ball',.33],['red_ball',.28],['test_block',.3],['pendulum_bob',.25],['pendulum_base',.78],['balance_base',.7]];
    for(const [name,radius] of shadowObjects){
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
  const orbit=new OrbitControls(camera,canvas);orbit.target.copy(lookTarget);orbit.update();orbit.saveState();orbit.enablePan=false;orbit.minZoom=.7;orbit.maxZoom=live?5:2;orbit.enableDamping=false;orbit.enabled=false;if(live)orbit.maxPolarAngle=Math.PI/2-.05;orbit.addEventListener('change',()=>{pickHistory.length=0;draw();});
  const ray=new T.Raycaster(),pointer=new T.Vector2();let mode='push',drag=null,forces=[],frame=0,last=0,until=0,visible=true,active=false,selected=bodyIds.red_ball?'red_ball':Object.keys(bodyIds)[0];
  orbit.zoomToCursor=live;
  const pointers=new Set();
  const marker=document.createElement('span');marker.className='room-grab-marker';marker.setAttribute('aria-hidden','true');marker.hidden=true;stage.append(marker);let hovered=null,hoverPointer=null,hoverFrame=0;
  function markHit(hit){
    if(!hit){hovered=null;marker.hidden=true;cancelAnimationFrame(hoverFrame);hoverFrame=0;return;}
    const body=hit.object.userData.body,q=data.xquat,rotation=new T.Quaternion(q[body*4+1],q[body*4+2],q[body*4+3],q[body*4]);
    hovered={body,offset:hit.point.clone().sub(new T.Vector3().fromArray(data.xpos,body*3)).applyQuaternion(rotation.invert())};
    marker.hidden=false;updateMarker();
  }
  function updateMarker(){
    if(!hovered)return;const b=hovered.body,q=data.xquat,rotation=new T.Quaternion(q[b*4+1],q[b*4+2],q[b*4+3],q[b*4]);
    const p=hovered.offset.clone().applyQuaternion(rotation).add(new T.Vector3().fromArray(data.xpos,b*3)).project(camera),r=canvas.getBoundingClientRect();
    marker.style.transform=`translate(${(p.x+1)*r.width/2}px,${(1-p.y)*r.height/2}px) translate(-50%,-50%)`;
  }
  const physicsStep=model.opt.timestep;let playbackRate=options.speed??(live?4:1);
  let accumulated=0,frameAverage=16.7,qualitySamples=0,stableSamples=0,quietSince=null;
  const arrow=new T.ArrowHelper(new T.Vector3(0,1,0),new T.Vector3(),0,0x387f68,.22,.13);arrow.visible=false;scene.add(arrow);
  function setRay(e){const r=canvas.getBoundingClientRect();pointer.set((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1);ray.setFromCamera(pointer,camera);}
  const projectedTargets=()=>pickGeoms.map(({geom})=>new T.Vector3().fromArray(data.geom_xpos,geom*3).project(camera));
  function rememberPickPositions(){
    const now=performance.now();
    while(pickHistory.length&&now-pickHistory[0].time>120)pickHistory.shift();
    if(!pickHistory.length||now-pickHistory.at(-1).time>=8)pickHistory.push({time:now,points:projectedTargets()});
  }
  function pick(e,recent=false){
    setRay(e);const direct=ray.intersectObjects(movable,false)[0];if(direct)return direct;
    // Small balls remain easy to grab at full-room scale and on touch screens.
    const r=canvas.getBoundingClientRect(),scale=r.height/(camera.top-camera.bottom)*camera.zoom;
    let hit=null,nearest=Infinity;
    const consider=(points,age)=>points.forEach((p,i)=>{
      if(p.z < -1 || p.z > 1)return;
      const {geom,body,radius}=pickGeoms[i];
      const distance=Math.hypot(r.left+(p.x+1)*r.width/2-e.clientX,r.top+(1-p.y)*r.height/2-e.clientY);
      const reach=Math.max(e.pointerType==='touch'?28:22,Math.min(18,radius*scale)+6),score=distance+age*.08;
      if(distance<reach&&score<nearest){nearest=score;hit={object:movable.find(m=>m.userData.body===body),point:new T.Vector3().fromArray(data.geom_xpos,geom*3)};}
    });
    consider(projectedTargets(),0);
    // At 4x a small ball can leave the clicked pixels between frames. Honour
    // the last 120 ms of displayed positions, without rewinding the physics.
    if(recent){const now=performance.now();for(const snapshot of pickHistory){const age=now-snapshot.time;if(age<=120)consider(snapshot.points,age);}}
    return hit;
  }
  function tick(now){
    frame=0;if(disposed||!active||!visible||document.hidden)return;const elapsed=Math.max(0,now-last)||16.7;last=now;
    frameAverage=frameAverage*.85+elapsed*.15;
    if(++qualitySamples>=20){
      if(frameAverage>30){
        stableSamples=0;
        if(!softShadows)useContactShadows();
        else if(renderer.getPixelRatio()>.75)renderer.setPixelRatio(Math.max(.75,renderer.getPixelRatio()*.8));
      }else if(frameAverage<20){
        stableSamples+=qualitySamples;
        if(stableSamples>=120&&renderer.getPixelRatio()<targetPixelRatio){renderer.setPixelRatio(Math.min(targetPixelRatio,renderer.getPixelRatio()+.15));stableSamples=0;}
      }else stableSamples=0;
      qualitySamples=0;
    }
    const physicsStart=performance.now();
    accumulated=Math.min(.05*playbackRate,accumulated+Math.min(.05,elapsed/1000)*playbackRate);
    while(accumulated>=physicsStep){
      data.xfrc_applied.fill(0);data.qfrc_applied.fill(0);forces=forces.filter(f=>data.time<f.end);
      for(const f of forces){const o=f.body*6;for(let k=0;k<3;k++)data.xfrc_applied[o+k]+=f.force[k];const center=new T.Vector3().fromArray(data.xpos,f.body*3),torque=f.point.clone().sub(center).cross(new T.Vector3(...f.force));for(let k=0;k<3;k++)data.xfrc_applied[o+3+k]+=torque.getComponent(k);}
      if(drag?.kind==='drag'&&!live){
        const b=drag.body;
        if(model.body_dofnum[b]===6){
          // Grip free bodies at their centre, without adding accidental spin.
          // A critically damped, mass-scaled hand follows promptly and settles.
          const mass=model.body_mass[b],center=new T.Vector3().fromArray(data.xpos,b*3),v=new T.Vector3().fromArray(data.qvel,model.body_dofadr[b]);
          const f=drag.target.clone().sub(drag.centerOffset).sub(center).multiplyScalar(400*mass).addScaledVector(v,-40*mass).addScaledVector(new T.Vector3().fromArray(model.opt.gravity),-mass);
          f.clampLength(0,100*mass).toArray(data.xfrc_applied,b*6);
        }else{
          const q=data.xquat,rotation=new T.Quaternion(q[b*4+1],q[b*4+2],q[b*4+3],q[b*4]);
          const offset=drag.localOffset.clone().applyQuaternion(rotation),point=new T.Vector3().fromArray(data.xpos,b*3).add(offset);
          const v=new T.Vector3().fromArray(data.cvel,b*6+3).add(new T.Vector3().fromArray(data.cvel,b*6).cross(offset));
          const f=drag.target.clone().sub(point).multiplyScalar(70).addScaledVector(v,-12).clampLength(0,90);
          f.toArray(data.xfrc_applied,b*6);offset.cross(f).toArray(data.xfrc_applied,b*6+3);
        }
      }
      if(live)simulation.step(true);else mj.mj_step(model,data);
      accumulated-=physicsStep;
    }
    physicsMs=performance.now()-physicsStart;
    if(!softShadows)renderer.shadowMap.needsUpdate=true;draw();
    const moving=data.qvel.some(v=>Math.abs(v)>.01);
    if(moving||drag||forces.length)quietSince=null;else if(quietSince===null)quietSince=data.time;
    if((live&&active)||drag||forces.length||data.time<until||quietSince===null||data.time-quietSince<.5)frame=requestAnimationFrame(tick);else active=false;
  }
  function wake(seconds=12){if(disposed)return;active=true;quietSince=null;until=Math.max(until,data.time+seconds);if(!frame&&visible&&!document.hidden){last=performance.now();frame=requestAnimationFrame(tick);}}
  let lastPush=null,pushSequence=0;
  const recordPush=(name,impulse)=>{lastPush={body:name,impulse:Array.from(impulse),time:data.time,sequence:++pushSequence};};
  function push(body,impulse,point){const bid=typeof body==='number'?body:bodyIds[body];if(live){const name=Object.keys(bodyIds).find(n=>bodyIds[n]===bid);if(simulation.info().held===name){status('Release the object to push it.');return;}simulation.launch(name,impulse);recordPush(name,impulse);options.onInteraction?.();wake();draw();return;}forces.push({body:bid,force:impulse.map(v=>v/.12),point:point||new T.Vector3().fromArray(data.xpos,bid*3),end:data.time+.12});recordPush(Object.keys(bodyIds).find(n=>bodyIds[n]===bid),impulse);wake();}
  const labels={red_ball:'Red ball',blue_ball:'Blue ball',test_block:'Block',pendulum_arm:'Pendulum',balance_arm:'Balance'};
  function releaseDrag(){const pointer=drag?.pointer;drag=null;simulation?.releaseGrip();arrow.visible=false;markHit(null);marker.classList.remove('is-held');canvas.style.cursor=mode==='view'?'grab':'default';if(pointer!==undefined&&canvas.hasPointerCapture(pointer))canvas.releasePointerCapture(pointer);}
  function beginInteraction(e,{capture=true}={}){
    pointers.add(e.pointerId);if(pointers.size>1){releaseDrag();return;}if(e.button!==0||mode==='view')return;
    const hit=pick(e,true);if(!hit){status('Choose a ball or a movable part.');return;}
    e.preventDefault?.();canvas.focus({preventScroll:true});const body=hit.object.userData.body;selected=Object.keys(bodyIds).find(n=>bodyIds[n]===body)||selected;if(capture)canvas.setPointerCapture(e.pointerId);
    const plane=new T.Plane().setFromNormalAndCoplanarPoint(mode==='drag'?camera.getWorldDirection(new T.Vector3()):new T.Vector3(0,0,1),hit.point);
    const q=data.xquat,rotation=new T.Quaternion(q[body*4+1],q[body*4+2],q[body*4+3],q[body*4]);
    drag={kind:mode,pointer:e.pointerId,body,point:hit.point.clone(),target:hit.point.clone(),plane,centerOffset:hit.point.clone().sub(new T.Vector3().fromArray(data.xpos,body*3)),localOffset:hit.point.clone().sub(new T.Vector3().fromArray(data.xpos,body*3)).applyQuaternion(rotation.invert()),startX:e.clientX,startY:e.clientY};
    if(mode==='drag'&&model.body_dofnum[body]===6){
      const center=new T.Vector3().fromArray(data.xpos,body*3),screen=center.clone().project(camera),higher=center.clone().add(new T.Vector3(0,0,1)).project(camera),height=canvas.getBoundingClientRect().height;
      drag.lift={center,right:new T.Vector3(1,0,0).applyQuaternion(camera.quaternion),pixelsPerUnit:height/(camera.top-camera.bottom)*camera.zoom,pixelsPerZ:Math.max(1,Math.abs(higher.y-screen.y)*height/2)};
      drag.floorPlane=new T.Plane().setFromNormalAndCoplanarPoint(new T.Vector3(0,0,1),hit.point);
    }
    if(live&&mode==='drag'){const center=new T.Vector3().fromArray(data.xpos,body*3);drag.centerOffset=hit.point.clone().sub(center);simulation.setGrip(selected,center.toArray());}
    markHit(hit);marker.classList.add('is-held');canvas.style.cursor='grabbing';
    status(`${labels[selected]||selected.replaceAll('_',' ')} · ${mode==='push'?'release to push':'release to drop'}`);if(mode==='drag'){options.onInteraction?.();wake(20);}
    return true;
  }
  function moveInteraction(e){
    if(!drag){
      if(mode!=='view'&&e.pointerType!=='touch'){
        hoverPointer=e;
        if(!hoverFrame)hoverFrame=requestAnimationFrame(()=>{hoverFrame=0;if(disposed||drag||mode==='view')return;const hit=pick(hoverPointer);markHit(hit);canvas.style.cursor=hit?'grab':'default';});
      }
      return;
    }
    if(drag.pointer!==e.pointerId)return;setRay(e);let p;
    if(drag.lift&&!e.shiftKey){
      const lift=drag.lift,center=lift.center.clone().addScaledVector(lift.right,(e.clientX-drag.startX)/lift.pixelsPerUnit);
      center.z-=(e.clientY-drag.startY)/lift.pixelsPerZ;
      p=center.add(drag.point.clone().sub(lift.center));
    }else p=ray.ray.intersectPlane(drag.lift?drag.floorPlane:drag.plane,new T.Vector3());
    if(!p)return;
    // A push target describes a direction, so it may extend beyond a wall.
    // Clamping that aim point could reverse or erase a near-wall push.
    if(!live&&drag.kind==='drag'){p.x=T.MathUtils.clamp(p.x,-3.7,3.7);p.y=T.MathUtils.clamp(p.y,-3.7,3.7);p.z=T.MathUtils.clamp(p.z,.15,5.4);}drag.target=p;
    if(live&&drag.kind==='drag'){const target=p.clone().sub(drag.centerOffset),clamped=simulation.clampGripTarget(selected,target.toArray(),ceiling);simulation.setGrip(selected,clamped);}
    if(drag.kind==='push'){const d=p.clone().sub(drag.point);d.z=0;arrow.position.copy(drag.point);if(d.length()>.01){arrow.setDirection(d.clone().normalize());arrow.setLength(Math.min(d.length(),2.5),.22,.13);}arrow.visible=d.length()>.04;draw();}
  }
  canvas.addEventListener('pointerdown',beginInteraction);
  canvas.addEventListener('pointermove',moveInteraction);
  canvas.addEventListener('pointerleave',()=>{if(!drag)markHit(null);});
  function endInteraction(e){
    pointers.delete(e.pointerId);if(!drag||drag.pointer!==e.pointerId)return;
    // A quick flick can end beyond the last delivered pointermove.
    moveInteraction(e);
    if(drag.kind==='push'){const d=drag.target.clone().sub(drag.point);d.z=0;if(Math.hypot(e.clientX-drag.startX,e.clientY-drag.startY)<5)d.set(0,.7,0);d.multiplyScalar(3).clampLength(0,8);push(drag.body,d.toArray(),drag.point);}
    releaseDrag();setMode(mode);draw();
  }
  function applyPushGesture(start,end){
    if(disposed||mode!=='push'||drag)return false;
    if(!beginInteraction(start,{capture:false})){pointers.delete(start.pointerId);return false;}
    endInteraction(end);return true;
  }
  canvas.addEventListener('pointerup',endInteraction);
  canvas.addEventListener('pointercancel',e=>{pointers.delete(e.pointerId);releaseDrag();draw();});
  canvas.addEventListener('lostpointercapture',e=>{pointers.delete(e.pointerId);if(drag?.pointer===e.pointerId){releaseDrag();draw();}});
  const clearPointer=e=>{pointers.delete(e.pointerId);if(drag?.pointer===e.pointerId){releaseDrag();draw();}};
  document.addEventListener('pointerup',clearPointer);document.addEventListener('pointercancel',clearPointer);
  const blur=()=>{pointers.clear();releaseDrag();};window.addEventListener('blur',blur);
  canvas.addEventListener('keydown',e=>{if(e.key==='Escape'){reset();return;}const d={ArrowUp:[0,2,0],ArrowDown:[0,-2,0],ArrowLeft:[-2,0,0],ArrowRight:[2,0,0],' ':[0,0,3]};if(d[e.key]){e.preventDefault();push(selected,d[e.key]);}});
  function reset(){lastPush=null;pushSequence=0;cancelAnimationFrame(frame);frame=0;active=false;quietSince=null;releaseDrag();pickHistory.length=0;forces=[];until=0;accumulated=0;arrow.visible=false;if(live)simulation.reset();else{mj.mj_resetDataKeyframe(model,data,0);mj.mj_forward(model,data);}renderer.shadowMap.needsUpdate=true;draw();setMode(mode);}
  function setMode(value){
    if(value!==mode)releaseDrag();mode=value;
    orbit.enabled=true;orbit.enableRotate=value==='view';orbit.enablePan=live&&value==='view';canvas.style.cursor=value==='view'?'grab':'default';
    const touch=matchMedia('(pointer:coarse)').matches,zoom=touch?'pinch to zoom':document.fullscreenElement?.contains(canvas)?'scroll to zoom':'Ctrl/⌘ + scroll to zoom';
    canvas.title=touch?'Pinch to zoom':document.fullscreenElement?.contains(canvas)?'Scroll to zoom':'Ctrl/⌘ + scroll to zoom';
    const instructions={push:'Drag, then release to push.',drag:'Drag up to lift; release to drop.',view:`Drag to rotate · ${zoom}`};
    status(live?instructions[value]:value==='view'?`Drag to rotate · ${zoom}`:value==='drag'?(touch?'Drag up to lift · release to drop':'Drag up to lift · Shift-drag to slide'):'Drag to push · tap to nudge');
  }
  function resize(){
    if(disposed)return;const r=stage.getBoundingClientRect();if(!r.width||!r.height)return;pickHistory.length=0;let half=5.8;
    if(live)half=simulation.config.camera.span/2*Math.max(1,1.5/(r.width/r.height));
    camera.top=half;camera.bottom=-half;camera.left=-half*r.width/r.height;camera.right=half*r.width/r.height;camera.updateProjectionMatrix();renderer.setSize(r.width,r.height,false);draw();
  }
  const resizeObserver=new ResizeObserver(resize);resizeObserver.observe(stage);
  const visibilityObserver=new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;if(!visible){cancelAnimationFrame(frame);frame=0;}else if(active)wake(0);});visibilityObserver.observe(stage);
  const visibility=()=>{if(document.hidden){cancelAnimationFrame(frame);frame=0;pointers.clear();releaseDrag();}else if(active)wake(0);};document.addEventListener('visibilitychange',visibility);
  const fullscreen=()=>setMode(mode);document.addEventListener('fullscreenchange',fullscreen);
  canvas.addEventListener('webglcontextlost',e=>{if(disposed)return;e.preventDefault();status('Graphics paused. Reload to retry.');cancelAnimationFrame(frame);});
  if(softwareRenderer){renderer.setPixelRatio(Math.min(devicePixelRatio,1));useContactShadows();}
  function pause(){active=false;cancelAnimationFrame(frame);frame=0;releaseDrag();}
  function destroy(){
    pause();disposed=true;resizeObserver.disconnect();visibilityObserver.disconnect();document.removeEventListener('visibilitychange',visibility);document.removeEventListener('fullscreenchange',fullscreen);document.removeEventListener('pointerup',clearPointer);document.removeEventListener('pointercancel',clearPointer);window.removeEventListener('blur',blur);orbit.dispose();marker.remove();
    const geometries=new Set(),mats=new Set(Object.values(materials)),textures=new Set([texture,scene.environment]);
    scene.traverse(o=>{if(o.geometry)geometries.add(o.geometry);if(o.material)mats.add(o.material);});for(const m of bakedMaterials.values())mats.add(m);
    for(const m of mats){for(const v of Object.values(m))if(v?.isTexture)textures.add(v);m.dispose();}for(const g of geometries)g.dispose();for(const t of textures)t?.dispose();
    renderer.dispose();renderer.forceContextLoss();canvas.remove();if(live)simulation.destroy();else{data.delete();model.delete();}
  }
  stage.append(canvas);resize();setMode(mode);
  return {setMode,reset,push,pause,beginInteraction,moveInteraction,applyPushGesture,setSpeed(value){if([.5,1,2,4].includes(value))playbackRate=value;},play:()=>wake(),isRunning:()=>active,destroy,getRenderInfo:()=>({calls:renderer.info.render.calls,triangles:renderer.info.render.triangles,pixelRatio:renderer.getPixelRatio(),frameMs:frameAverage,renderMs,physicsMs,softShadows,room:live?{bounds:simulation.config.physics_bounds,camera:simulation.config.camera,roofBottom:new T.Box3().setFromObject(scene.getObjectByName('Native ceiling glass')).min.z}:null}),getState:()=>({time:data.time,lastPush,rate:playbackRate,mode,selected,scene:simulation?.config.id,oracle:simulation?.info(),qvel:Array.from(data.qvel),colors:live?Object.fromEntries(Object.values(simulation.bodies).map(b=>[b.name,Array.from(model.geom_rgba.subarray(b.g*4,b.g*4+4))])):{},qpos:Array.from(data.qpos),positions:Object.fromEntries(Object.entries(bodyIds).map(([n,b])=>[n,Array.from(data.xpos.slice(b*3,b*3+3))])),contacts:data.ncon}),project:name=>{const p=(Array.isArray(name)?new T.Vector3().fromArray(name):name in geomIds?new T.Vector3().fromArray(data.geom_xpos,geomIds[name]*3):new T.Vector3().fromArray(data.xpos,bodyIds[name]*3)).project(camera),r=stage.getBoundingClientRect();return {x:r.left+(p.x+1)*r.width/2,y:r.top+(1-p.y)*r.height/2};}};
}
