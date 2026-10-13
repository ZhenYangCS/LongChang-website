/* Fifteen explanatory experiments. Native scene geometry remains available
 * through the Original scene tab. These diagrams isolate each altered law;
 * they are not MuJoCo trajectories or evidence of model performance.
 */
(() => {
  'use strict';
  const $ = selector => document.querySelector(selector);
  const motion = window.LongChangMotion;
  const {base, point, points, line, text, polygon, ball, tile, rebound} = motion.draw;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const uid = 'atlas';
  const configs = {
    '01': {trigger:'Drop matched balls onto the gray tile and the ordinary floor.', label:'Release height', range:[1, 3, .1], initial:2, unit:'bricks', note:'Matched qualitative drops. Ordinary contact response is simplified; the tile adds no physical effect.'},
    '02': {trigger:'Place two free spheres near each other, then let go.', label:'Pair of spheres', options:[['red-red','Red + red'],['red-blue','Red + blue'],['blue-blue','Blue + blue']], initial:'red-red', note:'Inverse-square attraction before contact, with equal unit masses. Ordinary contact and friction are omitted.'},
    '03': {trigger:'Compare a light red ball (mass 1) with a heavy blue ball (mass 4).', label:'Experiment', options:[['drop','Drop from equal height'],['speed','Equal upward speeds'],['impulse','Equal upward impulses']], initial:'drop', note:'Vertical flight uses a = g√(1/m). Contact is shown as stopping at the floor; rebound is omitted.'},
    '04': {trigger:'Repeat the same upward launch at different phases of the gravity cycle.', label:'Launch phase', options:[['0','0 counts · baseline, rising'],['1.5','1.5 counts · strongest gravity'],['4.5','4.5 counts · weakest gravity']], initial:'0', note:'Flight integrates the published sinusoidal gravity. The waveform spans one 6-count cycle; contact is simplified.'},
    '05': {trigger:'Launch the same unit-mass ball above or below the speed threshold.', label:'Launch speed', range:[1, 5, .1], initial:4, unit:'bricks/count', note:'Only the added braking force is integrated. Ordinary friction is omitted to isolate the 2.5 threshold.'},
    '06': {trigger:'Launch a ball in different directions and follow the curvature.', label:'Launch direction', options:[['0','East →'],['90','North ↑'],['180','West ←'],['270','South ↓']], initial:'0', note:'Unit-mass, constant-speed illustration of the sideways force. Ordinary friction is omitted.'},
    '07': {trigger:'Release identical balls over the red and blue tiles.', label:'Release height', range:[1, 3, .1], initial:2, unit:'bricks', note:'Idealized vertical rebounds using e = 0.90 and e = 0.15. Rebound height is e² times release height.'},
    '08': {trigger:'Increase the launch impulse and compare the resulting speed.', label:'Launch impulse', range:[.5, 12, .5], initial:3, unit:'unit mass', note:'The launch speed is computed from the published momentum–velocity law for unit mass. Subsequent forces are omitted.'},
    '09': {trigger:'Send a ball through the gray tile’s horizontal footprint.', label:'Trajectory', options:[['through','Through the tile'],['beside','Beside the tile'],['above','Above the tile']], initial:'through', note:'Boundary multipliers are isolated. Gravity and friction are omitted; real exit speed also depends on intervening losses.'},
    '10': {trigger:'Place a ball at rest inside or outside the yellow region.', label:'Starting position', options:[['inside','At rest · inside the region'],['outside','At rest · outside the region'],['above','At rest · above the region']], initial:'inside', note:'Qualitative illustration of active driving in a vertical column. Ordinary motion and per-step gain are simplified.'},
    '11': {trigger:'Bring two experiment balls into contact, then let them separate.', label:'Collision partner', options:[['ball','Another experiment ball'],['wall','A wall']], initial:'ball', note:'Schematic collision: ×1.8 applies to each participant’s remaining velocity at separation, not to the incoming velocity.'},
    '12': {trigger:'Bring two free spheres into contact while tracking their identities.', label:'Contact sequence', options:[['repeat','Separate and make contact again'],['hold','Hold the same contact']], initial:'repeat', note:'Contact sequence is staged to isolate color exchange. A and B label persistent object identities.'},
    '13': {trigger:'Repeat separate ball–ball contacts and count the events.', label:'Contact sequence', options:[['repeat','Three separate ball contacts'],['hold','One sustained ball contact'],['wall','Three wall contacts']], initial:'repeat', note:'Staged contact events; every third qualifying event sets upward velocity to 4. Floor, wall and apparatus contacts do not count.'},
    '14': {trigger:'Launch red, then watch green twelve counts later.', label:'After launching red', options:[['free','Let red move freely'],['hold','Hold red just after launch'],['moving','Give green a northward velocity']], initial:'free', note:'The 12-count schedule and velocity replacement are preserved. Ordinary slowing and the diagram scale are simplified.'},
    '15': {trigger:'Observe red’s northward drive, then act on either ball.', label:'Intervention at count 3', options:[['blue','Nonzero push on blue'],['red','Nonzero push on red'],['zero','Zero-impulse push']], initial:'blue', note:'Extra-force contribution only. The nonzero command pauses it for 10 counts; ordinary post-push motion is omitted.'}
  };
  let id = '01', value = configs[id].initial, time = 0, playing = false, touring = false;
  let visible = false, frame = 0, previous = 0, lastDraw = 0, exportMode = false, view = window.SCENE_INDEX?.length ? 'physics' : 'motion';
  let initialPreview = false;
  const duration = 8;

  const sphere = (x, y, z, color, label = '') => ball(uid, x, y, Math.max(0, z), color, label);
  const arrow = (a, b, color = '#3b837b') => line(a, b, color, `stroke-width="2" marker-end="url(#${uid}-arrow)"`);
  const trace = (a, b, color = '#b6c8be') => line(a, b, color, 'stroke-dasharray="3 5" stroke-width="1.2"');
  const annotation = (x, y, str, color = '#668079') => text(x, y, str, `font-size="10" fill="${color}"`);
  function badge(title, reading, x = 425, y = 60) {
    return `<rect x="${x}" y="${y}" width="150" height="86" rx="10" fill="#fff" stroke="#dce5dc"/>` + text(x + 16, y + 23, title, 'font-size="8" letter-spacing=".9"') + text(x + 16, y + 61, reading, 'font-size="28" fill="#3c7b69" font-family="Newsreader, Georgia, serif"');
  }
  function wavePath(fn, width = 190, height = 55, x = 90, y = 64, from = 0, to = 6) {
    const pts = Array.from({length: 100}, (_, i) => [x + width * i / 99, y + height * (1 - fn(from + (to - from) * i / 99))]);
    return `<polyline points="${points(pts)}" stroke="#719b80" fill="none" stroke-width="2"/>`;
  }

  function experiment(sceneId, s, control) {
    let art = '', state = '', reading = '', observation = '';
    const n = Number(control);
    if (sceneId === '01' || sceneId === '07') {
      const special = sceneId === '07', height = n, t = Math.max(0, s - .7) * .31;
      art += tile(1.65, 3.55, special ? '#e8aa98' : '#bdc7c3', '#98aaa1');
      if (special) art += tile(4.35, 2.45, '#9db9db', '#6b8cab');
      [special ? .9 : .55, special ? .15 : .55].forEach((e, i) => {
        const x = i ? 4.35 : 1.65, y = i ? 2.45 : 3.55;
        art += trace(point(x, y), point(x, y, height));
        art += sphere(x, y, rebound(height, e, t) + .06, 'stone', i ? 'B' : 'A');
      });
      art += annotation(171, 336, special ? 'RED · e = 0.90' : 'GRAY TILE');
      art += annotation(398, 352, special ? 'BLUE · e = 0.15' : 'ORDINARY FLOOR');
      state = special ? 'SURFACE-DEPENDENT REBOUND' : 'ORDINARY CONTROL';
      reading = special ? `${(height * .81).toFixed(2)} / ${(height * .0225).toFixed(3)} bricks` : 'No extra effect';
      observation = special ? 'The same release produces very different rebounds. Changing height preserves the surface-dependent ratios.' : 'Both drops behave the same. A visually distinct tile is not evidence of a new physical law.';
    } else if (sceneId === '02') {
      let separation = 3.4, speed = 0;
      const attracts = control === 'red-red', t = Math.max(0, s - .7) * .23;
      if (attracts) for (let step = 0; step < Math.floor(t * 240) && separation > .6; step++) {
        speed += 40 / (separation * separation) / 240;
        separation = Math.max(.6, separation - speed / 240);
      }
      const a = 3 - separation / 2, b = 3 + separation / 2;
      art += trace(point(1.2, 3), point(4.8, 3));
      art += sphere(a, 3, .05, control === 'blue-blue' ? 'blue' : 'red');
      art += sphere(b, 3, .05, attracts ? 'red' : 'blue');
      if (attracts && separation > .8) { art += arrow(point(a + .35, 3, .3), point(a + .85, 3, .3)); art += arrow(point(b - .35, 3, .3), point(b - .85, 3, .3)); }
      art += badge('PAIRWISE ATTRACTION', attracts ? 'F = 20 / r²' : 'F = 0');
      state = attracts ? 'RED–RED ATTRACTION' : 'NO EXTRA ATTRACTION';
      reading = attracts ? 'Color selects the pair' : 'Blue is inert';
      observation = attracts ? 'The red pair accelerates toward each other as the distance decreases. Try replacing either one with blue.' : 'The altered force does not act on this pair. Blue neither attracts nor is attracted.';
    } else if (sceneId === '03') {
      const t = Math.max(0, s - .5) * .19;
      const velocities = control === 'drop' ? [0, 0] : control === 'speed' ? [4, 4] : [4, 1];
      [1, 4].forEach((mass, i) => {
        const acceleration = 9.81 / Math.sqrt(mass), z = Math.max(0, 1.8 + velocities[i] * t - .5 * acceleration * t * t);
        const x = i ? 4.3 : 1.7, y = i ? 2.5 : 3.5;
        art += trace(point(x, y), point(x, y, 2.8));
        art += sphere(x, y, z, i ? 'blue' : 'red');
        const pos = point(x, y); art += annotation(pos[0] - 35, pos[1] + 36, `MASS ${mass} · ${i ? 'g / 2' : 'g'}`);
      });
      art += badge('FALLING ACCELERATION', 'g √(1 / m)');
      state = control === 'drop' ? 'EQUAL RELEASE HEIGHT' : control === 'speed' ? 'EQUAL INITIAL SPEEDS' : 'EQUAL IMPULSES';
      reading = 'Heavy blue: half the acceleration';
      observation = control === 'impulse' ? 'Equal impulses launch the heavy ball four times slower. Equal impulse and equal speed are different experiments.' : control === 'speed' ? 'With equal upward speeds, blue rises higher and stays airborne longer because its downward acceleration is smaller.' : 'The heavy blue ball falls more slowly. Its mass is four times greater, and its downward acceleration is half as large.';
    } else if (sceneId === '04') {
      const t = Math.max(0, s - .5) * .2, phase = n, w = Math.PI / 3, g = 9.81, a = .3;
      const z = 1 + 4.5 * t - .5 * g * t * t + g * a / w * ((Math.sin(w * (phase + t)) - Math.sin(w * phase)) / w - t * Math.cos(w * phase));
      const ratio = 1 + a * Math.sin(w * (phase + t));
      art += trace(point(3, 3), point(3, 3, 2.8)) + sphere(3, 3, Math.max(0, z), 'red');
      art += wavePath(v => (1 + Math.sin(Math.PI * v / 3)) / 2);
      const px = 90 + ((phase + t) % 6) / 6 * 190, py = 64 + 55 * (1 - (ratio - .7) / .6);
      art += `<circle cx="${px}" cy="${py}" r="4" fill="#d4846d"/>` + annotation(90, 140, 'ONE GRAVITY CYCLE · 6 COUNTS');
      art += badge('CURRENT GRAVITY', `${ratio.toFixed(2)} g₀`);
      state = 'SAME LAUNCH · DIFFERENT TIME'; reading = '0.7 g₀ ↔ 1.3 g₀';
      observation = 'The launch is identical; the phase is different. Gravity varies continuously during the flight, not just at release.';
    } else if (sceneId === '05') {
      const t = Math.max(0, s - .5) * .12, excess = Math.max(0, n - 2.5);
      const speed = n > 2.5 ? 2.5 + excess * Math.exp(-8 * t) : n;
      const travel = n > 2.5 ? 2.5 * t + excess * (1 - Math.exp(-8 * t)) / 8 : n * t;
      art += trace(point(.8, 3), point(5.6, 3)) + sphere(.8 + travel, 3, .04, 'red');
      art += arrow(point(.8 + travel, 3, .25), point(.8 + travel + speed * .24, 3, .25));
      art += badge('CURRENT SPEED', `${speed.toFixed(2)}`);
      art += annotation(148, 340, 'EXTRA BRAKING ONLY ABOVE 2.5');
      state = n > 2.5 ? 'ADDED BRAKING ACTIVE' : 'BELOW THE THRESHOLD'; reading = 'v꜀ = 2.5 bricks/count';
      observation = n > 2.5 ? 'A faster launch activates the extra brake. The braking force shrinks as speed approaches the threshold.' : 'No extra brake is triggered. Ordinary physics still applies below the threshold.';
    } else if (sceneId === '06') {
      const t = Math.max(0, s - .5) * .58, a = n * Math.PI / 180, w = 1.2, r = 1.05;
      const at = u => [3 + r * (Math.cos(a) * Math.sin(w * u) + Math.sin(a) * (1 - Math.cos(w * u))), 3 + r * (-Math.sin(a) * Math.sin(w * u) - Math.cos(a) * (Math.cos(w * u) - 1))];
      const position = at(t), path = Array.from({length:80}, (_, i) => point(...at(t * i / 79)));
      art += trace(point(3, 3), point(3 + 2.3 * Math.cos(a), 3 - 2.3 * Math.sin(a)));
      art += `<polyline points="${points(path)}" fill="none" stroke="#ce927b" stroke-width="2.5"/>`;
      art += sphere(...position, .04, 'red');
      art += arrow(point(...position, .25), point(position[0] + .7 * Math.cos(a - w * t), position[1] - .7 * Math.sin(a - w * t), .25));
      art += badge('RELATIVE TO MOTION', 'Always right');
      state = 'CLOCKWISE CURVATURE'; reading = 'aₓ = 1.2vᵧ · aᵧ = −1.2vₓ';
      observation = 'Changing the launch direction rotates the trajectory. The extra force turns with the velocity and does no work.';
    } else if (sceneId === '08') {
      const speed = p => 2 * p / (1 + Math.sqrt(1 + 4 * (p / 2.2) ** 2)), v = speed(n);
      const x = .8 + v * Math.max(0, s - .5) * .23;
      art += sphere(x, 3.1, .04, 'blue') + trace(point(.8, 3.1), point(5.4, 3.1));
      art += wavePath(p => speed(p) / 2.2, 210, 75, 95, 54, 0, 12);
      art += line([95, 54], [305, 54], '#b8cabc', 'stroke-dasharray="3 5"');
      art += `<circle cx="${95 + n / 12 * 210}" cy="${54 + 75 * (1 - v / 2.2)}" r="4" fill="#638ab4"/>`;
      art += annotation(95, 149, 'MORE IMPULSE → DIMINISHING SPEED GAINS');
      art += badge('LAUNCH SPEED', v.toFixed(3));
      state = 'A SPEED CEILING'; reading = 'Always below 2.2 bricks/count';
      observation = 'Increase the impulse. Momentum keeps increasing, but velocity approaches 2.2 without reaching it.';
    } else if (sceneId === '09') {
      const t = Math.max(0, s - .5), crossing = control !== 'beside';
      const x = crossing ? t < 1 ? 1 + t : t < 6 ? 2 + .4 * (t - 1) : 4 + (t - 6) : Math.min(5.7, 1 + t);
      const inside = crossing && x >= 2 && x < 4, exited = crossing && x >= 4;
      art += tile(3, 3, '#bac5c1', '#9eafa5');
      art += trace(point(.7, control === 'beside' ? 4.9 : 3), point(5.8, control === 'beside' ? 4.9 : 3));
      art += sphere(x, control === 'beside' ? 4.9 : 3, control === 'above' ? 1.2 : .09, 'red');
      if (control === 'above') art += trace(point(x, 3), point(x, 3, 1.2));
      art += badge('BOUNDARY RULE', inside ? 'v ← 0.4 v' : exited ? 'v ← v / 0.4' : 'No crossing');
      state = inside ? 'INSIDE THE FOOTPRINT' : exited ? 'EXIT MULTIPLIER APPLIED' : 'OUTSIDE THE REGION'; reading = control === 'above' ? 'Height does not disable it' : 'Entry ×0.4 · exit ÷0.4';
      observation = control === 'beside' ? 'The route avoids the footprint, so neither boundary multiplier is triggered.' : 'Velocity changes at the boundaries, even above the tile. The real world still applies friction and gravity between crossings.';
    } else if (sceneId === '10') {
      const outside = control === 'outside', u = Math.max(0, s - .6);
      const x = outside ? .9 : Math.min(5.65, 2.2 + .09 * u + .062 * u * u), active = !outside && x < 4.5;
      art += polygon([[2, 2.05], [4.5, 2.05], [4.5, 3.95], [2, 3.95]].map(p => point(...p)), '#ebd696', 'stroke="#c7b575"');
      art += sphere(x, 3, control === 'above' ? 1.05 : .07, 'red');
      if (active) art += arrow(point(x, 3, .25 + (control === 'above' ? 1 : 0)), point(x + .7, 3, .25 + (control === 'above' ? 1 : 0)));
      art += annotation(226, 348, 'YELLOW REGION · ACTIVE ENERGY INPUT', '#a08a49');
      art += badge('EXTRA DRIVING', active ? 'Active' : 'Inactive');
      state = outside ? 'AT REST OUTSIDE' : active ? 'DRIVING IN THE FOOTPRINT' : 'OUTSIDE · DRIVING ENDS'; reading = 'Low-speed seed points east';
      observation = outside ? 'At rest outside the region, the ball receives no active seed or amplification.' : 'Inside the footprint, a resting ball gets an eastward seed, then active amplification. The rule also acts above the tile.';
    } else if (sceneId === '11') {
      const wall = control === 'wall', contact = 2.8, after = Math.max(0, s - 3.5);
      const a = s < contact ? 1.2 + s * .5 : wall ? 2.6 - after * .3 : 2.6 - after * .12;
      art += sphere(a, 3, .06, 'red');
      if (wall) art += polygon([point(3.05, 2.2), point(3.05, 3.8), point(3.05, 3.8, 1.2), point(3.05, 2.2, 1.2)], '#c3d0c7', 'stroke="#9fae9f"');
      else { art += sphere(3.2 + Math.min(2.4, after * .48), 3, .06, 'blue'); art += sphere(4.6, 1.4, .06, 'green'); art += annotation(433, 267, 'GREEN · UNINVOLVED'); }
      if (after > 0 && !wall) art += arrow(point(3.2 + Math.min(2.4, after * .48), 3, .28), point(3.2 + Math.min(2.4, after * .48) + .7, 3, .28));
      art += badge('ON SEPARATION', wall ? 'No boost' : s > 3.5 ? 'v ← 1.8 v' : 'Not yet');
      state = wall ? 'WALL CONTACT' : s < contact ? 'APPROACHING' : s < 3.5 ? 'IN CONTACT' : 'CONTACT HAS ENDED'; reading = 'Only the participating balls';
      observation = wall ? 'A wall collision does not trigger the programmed speed gain.' : 'The boost happens when ball–ball contact ends. Both participants’ remaining velocities are multiplied; green is unaffected.';
    } else if (sceneId === '12' || sceneId === '13') {
      const colors = sceneId === '12', hold = control === 'hold', wall = control === 'wall';
      const starts = colors ? [1.5, 5.5] : [1.5, 3.5, 5.5];
      const count = wall ? 0 : hold ? Number(s >= 1.5) : starts.filter(t => s >= t).length;
      let distance = 1.4;
      if (hold) distance = s < 1.5 ? 1.4 - s * .74 : .29;
      else for (const start of starts) distance = Math.min(distance, .29 + Math.abs(s - start) * .65);
      distance = Math.max(.29, distance);
      const kickT = Math.max(0, s - 5.5) * .32, z = !colors && count === 3 ? Math.max(0, 4 * kickT - 4.905 * kickT ** 2) : 0;
      const swapped = colors && count % 2 === 1;
      art += sphere(3 - distance, 3, z + .05, swapped ? 'blue' : 'red', 'A');
      if (!wall) art += sphere(3 + distance, 3, z + .05, swapped ? 'red' : 'blue', 'B');
      else art += polygon([point(3, 2.1), point(3, 3.9), point(3, 3.9, 1.1), point(3, 2.1, 1.1)], '#cad5cb', 'stroke="#a5b5a5"');
      art += badge('QUALIFYING CONTACTS', String(count));
      if (!colors) for (let i = 1; i <= 3; i++) art += `<circle cx="${180 + i * 42}" cy="352" r="12" fill="${count >= i ? '#79a184' : '#e2eade'}"/>` + text(180 + i * 42, 356, String(i), `text-anchor="middle" fill="${count >= i ? 'white' : '#90a48e'}"`);
      state = colors ? count ? 'COLOR EXCHANGE AT CONTACT START' : 'OBJECT IDENTITIES: A AND B' : count === 3 ? 'THIRD CONTACT · UPWARD KICK' : 'COUNT DISTINCT CONTACT EVENTS';
      reading = colors ? 'Identity stays · color changes' : `${count} / 3 qualifying contacts`;
      observation = wall ? 'Wall contacts do not count toward the third-contact jump.' : hold ? 'One sustained contact counts once. Holding contact does not repeatedly trigger the rule.' : colors ? 'A and B keep their identities. Their colors swap once when a new contact begins, then swap back at the next contact.' : 'The first two contacts do not trigger a jump. On the third distinct ball–ball contact, both balls receive an upward kick.';
    } else if (sceneId === '14') {
      const t = s * 2, travel = u => { const v = clamp(u, 0, 3); return 1.5 * v - .25 * v * v; };
      const rx = 1.1 + travel(control === 'hold' ? Math.min(t, .35) : t), gx = 1.1 + travel(t - 12);
      const gy = control === 'moving' ? 4.3 - clamp(t - 8, 0, 4) * .16 : 4.3;
      art += trace(point(.8, 1.8), point(5.5, 1.8)) + trace(point(.8, 4.3), point(5.5, 4.3));
      art += sphere(rx, 1.8, .05, 'red') + sphere(gx, gy, .05, 'green');
      if (control === 'hold' && t > .35) { const [x, y] = point(rx, 1.8); art += `<rect x="${x - 21}" y="${y - 35}" width="42" height="45" rx="7" stroke="#98b6a4" fill="none" stroke-dasharray="3 4"/>`; }
      if (t >= 12) art += arrow(point(gx, gy, .25), point(gx + .75, gy, .25));
      art += badge(t < 12 ? 'COUNTS UNTIL ECHO' : 'VELOCITY REPLACED', t < 12 ? (12 - t).toFixed(1) : 'At 12 counts');
      state = t < 12 ? 'VELOCITY STORED AT LAUNCH' : 'GREEN TAKES THE STORED VELOCITY'; reading = 'A delayed event, not a replay';
      observation = control === 'hold' ? 'Stopping red does not cancel the scheduled transfer. Green still takes the stored velocity twelve counts after launch.' : control === 'moving' ? 'Green’s northward motion is replaced by the stored eastward velocity. The transfer does not add the two velocities.' : 'Red can stop before green starts. The delay separates the cause and effect into different observations.';
    } else if (sceneId === '15') {
      const t = s * 2, zero = control === 'zero', active = zero || t < 3 || t >= 13;
      const travel = zero ? .007 * t * t : t < 3 ? .007 * t * t : .063 + Math.max(0, t - 13) ** 2 * .035;
      const y = 4.3 - travel;
      art += trace(point(2.2, 4.7), point(2.2, .9)) + annotation(385, 151, 'NORTH');
      art += sphere(2.2, y, .05, 'red') + sphere(4.5, 3.6, .05, 'blue');
      if (active) art += arrow(point(2.2, y, .25), point(2.2, y - .85, .25));
      if (t >= 3 && t < 5) {
        const p = control === 'red' ? point(2.2, y) : point(4.5, 3.6);
        art += `<ellipse cx="${p[0]}" cy="${p[1]}" rx="${22 + (t - 3) * 9}" ry="${10 + (t - 3) * 4}" fill="none" stroke="#7ca3bf" opacity="${1 - (t - 3) / 2}"/>`;
      }
      art += badge(active ? 'NORTHWARD FORCE' : 'COUNTS UNTIL RETURN', active ? 'Active ↑' : (13 - t).toFixed(1), 89, 70);
      state = zero ? 'ZERO IMPULSE · NO PAUSE' : t < 3 ? 'EXTRA FORCE ACTIVE' : t < 13 ? `PUSH ${String(control).toUpperCase()} · FORCE PAUSED` : 'TEN COUNTS LATER · FORCE RETURNS';
      reading = 'Any nonzero push restarts the pause';
      observation = zero ? 'A zero-impulse push does not suppress the extra force. This control distinguishes an action command from a physical launch.' : `A push on ${control} pauses red’s extra force for ten counts. Acting on a different movable object can suppress red’s behavior.`;
    }
    return {svg:base(uid) + art + '</g>', state, reading, observation};
  }

  function updateText(selector, content) { if ($(selector).textContent !== content) $(selector).textContent = content; }
  function render() {
    const result = experiment(id, time, value);
    $('#atlas-canvas').innerHTML = result.svg;
    updateText('#atlas-state-label', result.state);
    updateText('#atlas-value', result.reading);
    if(view === 'motion') updateText('#atlas-observation', result.observation);
    $('#atlas-play').textContent = playing ? 'II' : '▶';
    $('#atlas-play').setAttribute('aria-label', `${playing ? 'Pause' : 'Play'} scene illustration`);
    $('#atlas-progress').value = Math.round(time * 100);
    updateText('#atlas-time', `${time.toFixed(1)} / 8.0 s`);
    if(view !== 'physics') {
      $('#atlas-tour').setAttribute('aria-pressed', String(touring));
      $('#atlas-tour').textContent = touring ? 'II Pause scene tour' : '▶ Play all 15 scenes';
    }
  }
  function setView(next) {
    view = next;
    $('#atlas-motion-view').hidden = view !== 'motion';
    $('#atlas-initial-view').hidden = view !== 'initial';
    $('#atlas-physics-view').hidden = view !== 'physics';
    $('.atlas-detail').dataset.view = view;
    $('.atlas-playback').hidden = view !== 'motion';
    $('#atlas-trigger-text').textContent = configs[id].trigger;
    $('#atlas-model-note').textContent = configs[id].note;
    render();
    document.querySelectorAll('[data-atlas-view]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.atlasView === view)));
    document.dispatchEvent(new CustomEvent('longchang:atlas-view',{detail:{view,id}}));
    syncClock();
  }
  function setup(scene, autoplay = true) {
    id = scene.id; value = configs[id].initial; time = 0;
    const config = configs[id];
    $('#atlas-trigger-text').textContent = config.trigger;
    $('#atlas-model-note').textContent = config.note;
    $('#atlas-position').textContent = `${id} / 15`;
    $('#atlas-canvas').setAttribute('aria-label', `${scene.name}. Idealized interactive illustration of the published law.`);
    const options = config.options?.map(([v, label]) => `<option value="${v}">${label}</option>`).join('');
    $('#atlas-controls').innerHTML = `<label for="atlas-parameter">${config.label}</label>` + (options ? `<select id="atlas-parameter">${options}</select>` : `<div class="atlas-range"><input id="atlas-parameter" type="range" min="${config.range[0]}" max="${config.range[1]}" step="${config.range[2]}" value="${value}"><output for="atlas-parameter" id="atlas-parameter-value">${Number(value).toFixed(1)} ${config.unit}</output></div>`);
    $('#atlas-parameter').value = value;
    $('#atlas-parameter').addEventListener(config.options ? 'change' : 'input', event => {
      value = config.range ? Number(event.target.value) : event.target.value;
      if (config.range) $('#atlas-parameter-value').textContent = `${Number(value).toFixed(1)} ${config.unit}`;
      touring = false; time = 0; playing = true; setView('motion'); render(); syncClock();
    });
    $('#atlas-evidence').hidden = !['06','07','14','15'].includes(id);
    playing = autoplay && !reduced.matches;
    setView(view); render(); syncClock();
  }
  function running() { return !exportMode && !document.hidden && !$('#motion-dialog').open && visible && playing && view === 'motion'; }
  function tick(now) {
    frame = 0;
    if (!running()) return;
    time += Math.min(.08, (now - previous) / 1000); previous = now;
    if (time >= duration) {
      if (touring) { window.showWorld(String(Number(id) % 15 + 1).padStart(2, '0')); playing = true; time = 0; }
      else { time = duration; playing = false; }
    }
    if (now - lastDraw > 32 || !playing) { render(); lastDraw = now; }
    if (running() && !frame) frame = requestAnimationFrame(tick);
  }
  function syncClock() { cancelAnimationFrame(frame); frame = 0; if (running()) { previous = performance.now(); frame = requestAnimationFrame(tick); } }
  document.addEventListener('longchang:scene', event => setup(event.detail));
  // The original scene thumbnails connect the illustrations to the paper.
  document.querySelectorAll('#scene-picker button').forEach(button => {
    const scene = window.LONGCHANG.scenes.find(s => s.id === button.dataset.scene);
    button.innerHTML = `<span class="scene-choice-number">${scene.id}</span><strong class="scene-choice-name">${scene.name}</strong><img class="scene-choice-symbol" src="assets/table1/scene-${scene.id}.svg" width="106" height="36" loading="lazy" decoding="async" alt="" aria-hidden="true">`;
    button.addEventListener('click', () => { touring = false; render(); if(view==='physics')window.LongChangPhysics?.play(); });
  });
  const mobilePicker=$('#scene-mobile-select');
  mobilePicker.innerHTML=window.LONGCHANG.scenes.map(s=>`<option value="${s.id}">${s.id} · ${s.name}</option>`).join('');
  mobilePicker.addEventListener('change',()=>{window.showWorld(mobilePicker.value);if(view==='physics')window.LongChangPhysics?.play();});
  document.addEventListener('longchang:scene',event=>{mobilePicker.value=event.detail.id;});
  $('#atlas-play').addEventListener('click', () => { if (time >= duration) time = 0; playing = !playing; if (!playing) touring = false; render(); syncClock(); });
  $('#atlas-reset').addEventListener('click', () => { time = 0; playing = false; touring = false; render(); syncClock(); });
  $('#atlas-progress').addEventListener('input', event => { time = Number(event.target.value) / 100; playing = false; touring = false; render(); syncClock(); });
  $('#atlas-tour').addEventListener('click', () => {
    if(view === 'physics' && window.LongChangPhysics) { window.LongChangPhysics.toggleTour(); return; }
    touring = !touring;
    if (touring) { setView('motion'); window.showWorld('01'); playing = true; }
    else playing = false;
    render(); syncClock();
  });
  function changeScene(direction) { touring = false; window.showWorld(String((Number(id) - 1 + direction + 15) % 15 + 1).padStart(2, '0')); }
  $('#atlas-prev').addEventListener('click', () => changeScene(-1));
  $('#atlas-next').addEventListener('click', () => changeScene(1));
  $('#atlas-evidence').addEventListener('click', event => { event.preventDefault(); playing = false; touring = false; render(); syncClock(); window.showDiscovery(id); });
  document.querySelectorAll('[data-atlas-view]').forEach(button => button.addEventListener('click', () => setView(button.dataset.atlasView)));
  new IntersectionObserver(entries => {
    visible = entries[0].isIntersecting;
    if (visible && !initialPreview && !reduced.matches) { initialPreview = true; playing = true; render(); }
    syncClock();
  }, {threshold:.05}).observe($('.atlas-detail'));
  document.addEventListener('visibilitychange', syncClock);
  document.addEventListener('longchang:presentation-open', syncClock);
  $('#motion-dialog').addEventListener('close', syncClock);
  reduced.addEventListener('change', event => { if (event.matches) { playing = false; touring = false; render(); syncClock(); } });
  const requested = new URLSearchParams(location.search).get('scene');
  window.showWorld(configs[requested] ? requested : '07');

  window.LongChangAtlas = Object.freeze({
    duration, setView, currentScene:()=>id,
    renderFrame(sceneId, seconds, option) {
      exportMode = true; cancelAnimationFrame(frame);
      if (sceneId !== id) window.showWorld(sceneId);
      if (option !== undefined) { value = option; $('#atlas-parameter').value = option; }
      time = clamp(seconds, 0, duration); playing = false; touring = false;
      document.body.classList.add('atlas-export'); setView('motion'); render();
    }
  });
})();
