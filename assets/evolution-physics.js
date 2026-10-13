import {createSceneSimulation} from './scene-physics.js';

// The accepted evolution programs, applied before the shared MuJoCo step.
// Object identity, inclusive pad boundaries and independent copy queues match
// generation/{generate,mutate,compose}/scene.json in the frozen run.
export async function createEvolutionSimulation(config, status) {
  const base = await createSceneSimulation(config, status);
  const {data, bodies, model} = base, p = config.parameters, kind = config.id;
  const red = bodies[kind === 'mutate' ? 'object_1' : 'red_ball'];
  const blue = bodies[kind === 'mutate' ? 'object_2' : 'blue_ball'];
  const hush = p.suppression_duration ?? p.HUSH;
  let quietUntil = 0, pending = [];
  const inPad = () => {
    const x = data.qpos[blue.q], y = data.qpos[blue.q + 1];
    return x >= 2.5 && x <= 3.5 && y >= 2.5 && y <= 3.5;
  };
  function rule() {
    if (data.time >= quietUntil) {
      if (kind === 'generate') {
        const dx = data.qpos[red.q] - data.qpos[blue.q];
        const dy = data.qpos[red.q + 1] - data.qpos[blue.q + 1];
        const distance = Math.hypot(dx, dy);
        if (distance > 0) for (const [k, delta] of [dx, dy].entries()) {
          data.xfrc_applied[red.id * 6 + k] += red.mass * p.acceleration * delta / distance;
          data.xfrc_applied[blue.id * 6 + k] -= blue.mass * p.acceleration * delta / distance;
        }
      } else if (kind !== 'mutate' || !inPad()) {
        data.xfrc_applied[red.id * 6 + 1] += red.mass * (p.DRIFT ?? p.drift_acceleration);
      }
    }
    const due = pending.filter(event => event.time <= data.time);
    if (due.length) {
      data.qvel.set(due.at(-1).velocity, bodies[p.recipient_name].d);
      pending = pending.filter(event => event.time > data.time);
    }
  }
  return {
    ...base,
    reset() { base.reset(); quietUntil = 0; pending = []; },
    step(external = false) {
      if (!external) { data.xfrc_applied.fill(0); data.qfrc_applied.fill(0); }
      rule(); base.step(true);
    },
    launch(name, impulse) {
      base.launch(name, impulse);
      if (!impulse.some(value => value !== 0)) return;
      quietUntil = data.time + hush;
      if (kind === 'compose' && name === p.source_name) {
        pending.push({time: data.time + p.copy_delay, velocity: Array.from(data.qvel.subarray(red.d, red.d + 3))});
      }
    },
    info() {
      const blocked = kind === 'mutate' && inPad();
      return {...base.info(), quietUntil, pending: pending.map(event => event.time),
        blocked, forceActive: data.time >= quietUntil && !blocked};
    },
    rule,
  };
}
