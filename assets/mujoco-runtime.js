import loadMujoco from './vendor/mujoco/mujoco.js';

let runtime = null, progress = '';
const listeners = new Set();
function report(message) {
  if (message === progress) return;
  progress = message;
  for (const listener of listeners) listener(message);
}
async function load() {
  report('Loading interaction…');
  const response = await fetch(new URL('./vendor/mujoco/mujoco.wasm', import.meta.url), {signal:AbortSignal.timeout(30000)});
  if (!response.ok) throw Error('Physics download failed');
  let size = 0;
  const stream = response.body.pipeThrough(new TransformStream({
    transform(chunk, controller) {
      size += chunk.length;
      report(`Loading interaction… ${Math.min(99, Math.round(size / 10370402 * 100))}%`);
      controller.enqueue(chunk);
    },
  }));
  // Compile while downloading. The browser handles compilation asynchronously;
  // no second copy of the entire binary or isolation headers are required.
  const binary = new Response(stream, {headers:{'Content-Type':'application/wasm'}});
  const module = typeof WebAssembly.compileStreaming === 'function'
    ? await WebAssembly.compileStreaming(binary)
    : await WebAssembly.compile(await binary.arrayBuffer());
  return new Promise((resolve, reject) => {
    loadMujoco({instantiateWasm(imports, receive) {
      // Browsers restrict synchronous instantiation of large modules.
      WebAssembly.instantiate(module, imports).then(instance => receive(instance, module)).catch(reject);
      return {};
    }}).then(resolve, reject);
  });
}
export function getMujoco(status = () => {}) {
  listeners.add(status);
  if (progress) status(progress);
  if (!runtime) runtime = load().catch(error => { runtime = null; progress = ''; throw error; });
  return runtime.finally(() => listeners.delete(status));
}
