import loadMujoco from './vendor/mujoco/mujoco.js';

let runtime=null;
export function getMujoco(status=()=>{}) {
  if(!runtime)runtime=(async()=>{
    const response=await fetch(new URL('./vendor/mujoco/mujoco.wasm',import.meta.url),{signal:AbortSignal.timeout(30000)});
    if(!response.ok)throw Error('Physics download failed');
    const reader=response.body.getReader(),chunks=[];let size=0;
    while(true){const {done,value}=await reader.read();if(done)break;chunks.push(value);size+=value.length;status(`Loading interaction… ${Math.min(99,Math.round(size/10370402*100))}%`);}
    const bytes=new Uint8Array(size);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.length;}
    return loadMujoco({wasmBinary:bytes});
  })().catch(error=>{runtime=null;throw error;});
  return runtime;
}
