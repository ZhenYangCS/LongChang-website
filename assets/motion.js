



(() => {
  'use strict';
  const $ = selector => document.querySelector(selector);
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  const clamp = (value, low, high) => Math.max(low, Math.min(high, value));
  const fixed = value => Number(value).toFixed(2);
  const duration = 12;
  const scenes = [
    {
      id: '07', short: 'Bounce', field: 'Surface restitution',
      title: 'Same objects. Different outcomes.',
      intro: 'Does a bounce belong to the ball, or to the surface beneath it?',
      equation: 'Red: e = 0.90  /  Blue: e = 0.15',
      note: 'Idealized vertical motion · rebound height = e² × release height',
      phases: [
        [0, '01 / OBSERVE', 'Release two identical balls from the same height.'],
        [1.6, '02 / COMPARE', 'The red surface returns 81% of the height. Blue returns just 2.25%.'],
        [6, '03 / INTERVENE', 'Swap the balls. Keep the surfaces.'],
        [7.5, '04 / INFER', 'The difference follows the surface, not the identity of the ball.']
      ]
    },
    {
      id: '06', short: 'Deflect', field: 'Clockwise deflection',
      title: 'A force that turns with motion.',
      intro: 'A launch points one way. The trajectory tells a different story.',
      equation: 'aₓ = 1.2vᵧ  /  aᵧ = −1.2vₓ',
      note: 'Side-force contribution only · ordinary friction is omitted',
      phases: [
        [0, '01 / LAUNCH', 'Give the ball an initial velocity. Predict a straight path.'],
        [2.5, '02 / OBSERVE', 'The trajectory turns clockwise. The force stays perpendicular to motion.'],
        [6, '03 / EXPLAIN', 'The force follows the velocity direction, not a fixed compass direction.'],
        [9, '04 / INFER', 'This side force changes the direction of motion without changing its speed.']
      ]
    },
    {
      id: '14', short: 'Echo', field: 'Delayed velocity transfer',
      title: 'The cause comes first. The motion comes later.',
      intro: 'Red has already stopped when green begins to move. Coincidence?',
      equation: 'vgreen(t + 12) ← vred(t⁺)',
      note: '12-count delay is preserved · ordinary slowing is simplified',
      phases: [
        [0, '01 / INTERVENE', 'Launch red. Its post-command velocity is stored.'],
        [3, '02 / WAIT', 'Red slows to a stop. Green remains still. The scheduled event persists.'],
        [8.5, '03 / OBSERVE', 'Twelve counts after the launch, green takes the stored velocity.'],
        [10, '04 / INFER', 'The rule replaces green’s velocity. It does not replay red’s path.']
      ]
    },
    {
      id: '15', short: 'Pause', field: 'Launch-suppressed drift',
      title: 'An experiment can hide the phenomenon.',
      intro: 'Red drifts north on its own. A push on blue can make that extra force disappear.',
      equation: 'Nonzero push → pause for 10 counts',
      note: 'Extra-force mechanism only · ordinary motion is simplified',
      phases: [
        [0, '01 / OBSERVE', 'An extra northward force acts on red.'],
        [3 / 1.8, '02 / INTERVENE', 'Push blue. Red’s extra force pauses for ten counts.'],
        [7 / 1.8, '03 / RESET', 'Push blue again. The ten-count interval starts over.'],
        [10 / 1.8, '04 / CONTROL', 'A zero-impulse push leaves the countdown unchanged.'],
        [17 / 1.8, '05 / WAIT', 'Wait without another push. Red’s northward force returns.']
      ]
    }
  ];

  scenes.forEach(scene => {
    const canonical = window.LONGCHANG.scenes.find(item => item.id === scene.id);
    scene.storyTitle = scene.title;
    scene.title = canonical.name;
    scene.short = canonical.name;
    scene.field = canonical.name;
  });
  const phaseAt = (scene, seconds) => scene.phases.filter(phase => phase[0] <= seconds).at(-1);


  const point = (x, y, z = 0) => [320 + (x - y) * 43, 112 + (x + y) * 22 - z * 62];
  const points = vertices => vertices.map(v => v.map(fixed).join(',')).join(' ');
  const line = (a, b, color = '#b4c9c4', extra = '') => `<path d="M${a.map(fixed).join(' ')}L${b.map(fixed).join(' ')}" stroke="${color}" fill="none" ${extra}/>`;
  const text = (x, y, value, extra = '') => `<text x="${x}" y="${y}" ${extra}>${value}</text>`;
  const polygon = (vertices, fill, extra = '') => `<polygon points="${points(vertices)}" fill="${fill}" ${extra}/>`;

  function base(uid) {
    const gradients = [['stone', '#f9fbfc', '#9cabb4', '#526976'], ['red', '#ffe0d2', '#df856e', '#b35543'], ['blue', '#dfecff', '#799cc8', '#466c9f'], ['green', '#dff4e5', '#88b99b', '#427d67']];
    let svg = `<defs><linearGradient id="${uid}-floor" x1="0" y1="0" x2=".7" y2="1"><stop stop-color="#f9fbf9"/><stop offset="1" stop-color="#e8efeb"/></linearGradient><linearGradient id="${uid}-edge"><stop stop-color="#b4c9bf"/><stop offset="1" stop-color="#d4e0d9"/></linearGradient>`;
    gradients.forEach(([name, a, b, c]) => {
      svg += `<radialGradient id="${uid}-${name}" cx="30%" cy="23%" r="78%"><stop stop-color="${a}"/><stop offset=".38" stop-color="${b}"/><stop offset="1" stop-color="${c}"/></radialGradient>`;
    });
    svg += `<marker id="${uid}-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M1 1 9 5 1 9" fill="none" stroke="#3b837b" stroke-width="1.6"/></marker></defs>`;
    svg += `<g font-family="DM Sans, Arial, sans-serif" font-size="10" fill="#668079">`;
    svg += '<ellipse cx="321" cy="347" rx="214" ry="52" fill="#244b40" opacity=".035"/>';
    svg += polygon([point(0, 6), point(6, 6), point(6, 0), point(6, 0, -.13), point(6, 6, -.13), point(0, 6, -.13)], `url(#${uid}-edge)`);
    svg += polygon([point(0, 0), point(6, 0), point(6, 6), point(0, 6)], `url(#${uid}-floor)`, 'stroke="#cbdad2" stroke-width="1.1"');
    for (let i = 1; i < 6; i++) {
      svg += line(point(i, 0), point(i, 6), '#dce5df', 'stroke-width=".8"');
      svg += line(point(0, i), point(6, i), '#dce5df', 'stroke-width=".8"');
    }
    svg += line([70, 374], [97, 388], '#9ab2a7');
    svg += line([70, 374], [43, 388], '#9ab2a7');
    svg += line([70, 374], [70, 343], '#9ab2a7');
    svg += text(103, 395, 'x', 'font-size="9"') + text(32, 395, 'y', 'font-size="9"') + text(67, 336, 'z', 'font-size="9"');
    return svg;
  }

  function ball(uid, x, y, z, color, label = '') {
    const [sx, sy] = point(x, y), [bx, by] = point(x, y, z);
    return `<ellipse cx="${sx}" cy="${sy + 2}" rx="${15 + z * 2}" ry="${5 + z}" fill="#25483e" opacity="${.14 / (1 + z)}"/><circle cx="${bx}" cy="${by - 13}" r="14" fill="url(#${uid}-${color})"/><circle cx="${bx - 4}" cy="${by - 18}" r="3.5" fill="white" opacity=".22"/>` + (label ? text(bx, by - 9, label, 'text-anchor="middle" font-size="9" font-weight="600" fill="#fff"') : '');
  }

  function tile(x, y, color, edge) {
    const v = [[x - 1, y - .82], [x + 1, y - .82], [x + 1, y + .82], [x - 1, y + .82]];
    return polygon(v.map(p => point(...p)), edge) + polygon(v.map(p => point(...p, .065)), color, 'stroke="white" stroke-opacity=".65" stroke-width=".8"');
  }

  function rebound(height, restitution, time) {
    const g = 9.81, fall = Math.sqrt(2 * height / g);
    if (time <= fall) return height - .5 * g * time * time;
    let remaining = time - fall, velocity = restitution * Math.sqrt(2 * g * height);
    while (velocity > .004 && remaining > 2 * velocity / g) {
      remaining -= 2 * velocity / g;
      velocity *= restitution;
    }
    return velocity > .004 ? Math.max(0, velocity * remaining - .5 * g * remaining ** 2) : 0;
  }

  function bounce(uid, seconds) {
    const swapped = seconds >= 6;
    const t = Math.max(0, seconds - (swapped ? 7.5 : 1.6)) * .52;
    let svg = tile(1.65, 3.55, '#e8aa98', '#ba7d6a') + tile(4.35, 2.45, '#9db9db', '#6b8cab');
    [[1.65, 3.55, .9, 'red'], [4.35, 2.45, .15, 'blue']].forEach(([x, y, e], i) => {
      const z = rebound(2, e, t), [px, py] = point(x, y, 2);
      svg += line(point(x, y), point(x, y, 2), '#9eafa9', 'stroke-dasharray="2 5"');
      svg += line([px - 21, py - 13], [px + 21, py - 13], '#96aaa3', 'stroke-width="1"');
      svg += ball(uid, x, y, z + .07, 'stone', i === Number(swapped) ? 'A' : 'B');
      svg += text(px, py - 29, 'h₀ = 2.0', 'text-anchor="middle" font-size="10"');
    });
    svg += text(175, 334, 'RED SURFACE', 'fill="#ad6653" font-size="9" letter-spacing="1.4"');
    svg += text(175, 358, '81%', 'fill="#ac6656" font-size="25" font-family="Newsreader, Georgia, serif"');
    svg += text(225, 357, 'rebound height', 'font-size="9"');
    svg += text(391, 351, 'BLUE SURFACE', 'fill="#567da9" font-size="9" letter-spacing="1.4"');
    svg += text(391, 375, '2.25%', 'fill="#567da9" font-size="25" font-family="Newsreader, Georgia, serif"');
    svg += text(460, 374, 'rebound height', 'font-size="9"');
    return svg;
  }

  function curve(uid, seconds) {
    const t = clamp((seconds - .9) / 10.2, 0, 1) * 4.8, w = 1.2;
    const at = time => [2.3 + 1.38 * Math.sin(w * time), 2.05 + 1.38 * (1 - Math.cos(w * time))];
    const path = Array.from({length: 90}, (_, i) => point(...at(t * i / 89), .03));
    const [x, y] = at(t), here = point(x, y, .23);
    let svg = line(point(...at(0), .02), point(5.7, 2.05, .02), '#9faeaa', 'stroke-dasharray="5 6" stroke-width="1.3"');
    svg += `<polyline points="${points(path)}" stroke="#cc7c65" fill="none" stroke-width="2.7" stroke-linecap="round"/>`;
    svg += ball(uid, x, y, .05, 'red');
    svg += line(here, point(x + .95 * Math.cos(w * t), y + .95 * Math.sin(w * t), .23), '#3b837b', `stroke-width="2" marker-end="url(#${uid}-arrow)"`);
    svg += line(here, point(x - .74 * Math.sin(w * t), y + .74 * Math.cos(w * t), .23), '#8aa69c', `stroke-width="1.8" marker-end="url(#${uid}-arrow)"`);
    svg += text(439, 200, 'No side force', 'font-size="10"') + text(182, 339, 'CLOCKWISE DEFLECTION', 'letter-spacing="1.5" font-size="9" fill="#ad6653"');
    svg += '<rect x="425" y="64" width="134" height="74" rx="10" fill="#fff" stroke="#dae4dc"/>';
    svg += text(443, 86, 'PERPENDICULAR FORCE', 'font-size="8" letter-spacing=".8"');
    svg += text(442, 116, 'a ⟂ v', 'font-family="Newsreader, Georgia, serif" font-size="28" fill="#306e66"');
    return svg;
  }

  function echo(uid, seconds) {
    const t = Math.max(0, (seconds - 1) * 1.6);
    const travel = time => { const u = clamp(time, 0, 3); return 1.7 * u - (1.7 / 6) * u ** 2; };
    let svg = '';
    [1.6, 4.2].forEach(y => { svg += line(point(.7, y), point(5.6, y), '#b2c8bf', 'stroke-width="1.2" stroke-dasharray="3 6"'); });
    const redX = 1.1 + travel(t), greenX = 1.1 + travel(t - 12);
    svg += line(point(1.1, 1.6), point(redX, 1.6), '#d89984', 'stroke-width="2"');
    if (t >= 12) svg += line(point(1.1, 4.2), point(greenX, 4.2), '#76a68b', 'stroke-width="2"');
    svg += ball(uid, redX, 1.6, .04, 'red') + ball(uid, greenX, 4.2, .04, 'green');
    svg += text(401, 207, t < 3 ? 'RED · LAUNCH' : 'RED · AT REST', 'font-size="9" letter-spacing="1" fill="#b5725d"');
    svg += text(185, 328, t < 12 ? 'GREEN · WAITING' : 'GREEN · VELOCITY COPIED', 'font-size="9" letter-spacing="1" fill="#53876b"');
    svg += '<rect x="425" y="58" width="140" height="96" rx="12" fill="#fff" stroke="#d8e5db"/>';
    svg += text(443, 81, t < 12 ? 'SCHEDULED TRANSFER' : 'VELOCITY REPLACED', 'font-size="8" letter-spacing=".7"');
    svg += text(442, 120, t < 12 ? fixed(12 - t) : '12.00', 'font-size="36" font-family="Newsreader, Georgia, serif" fill="#377d70"');
    svg += text(444, 141, t < 12 ? 'counts remaining' : 'counts after launch', 'font-size="9"');
    if (t >= 12) svg += line(point(greenX, 4.2, .22), point(greenX + .7, 4.2, .22), '#3b837b', `stroke-width="2" marker-end="url(#${uid}-arrow)"`);
    return svg;
  }

  function drift(uid, seconds) {
    const t = seconds * 1.8, active = t < 3 || t >= 17;
    const redY = 4.5 - Math.min(t, 3) * .14 - Math.max(0, t - 17) ** 2 * .055;
    const blueX = 4.15 + clamp((t - 3) * .3, 0, .4) + clamp((t - 7) * .3, 0, .4);
    let svg = line(point(2.25, 4.9), point(2.25, .9), '#a9c4b6', `stroke-width="1.4" stroke-dasharray="4 5" marker-end="url(#${uid}-arrow)"`);
    svg += text(395, 153, 'NORTH', 'font-size="9" letter-spacing="1.6"');
    svg += ball(uid, 2.25, redY, .04, 'red') + ball(uid, blueX, 3.65, .04, 'blue');
    if (active) svg += line(point(2.25, redY, .22), point(2.25, redY - .9, .22), '#3b837b', `stroke-width="2.5" marker-end="url(#${uid}-arrow)"`);
    const sincePush = t - (t >= 10 ? 10 : t >= 7 ? 7 : 3);
    if (sincePush >= 0 && sincePush < 1.4) {
      const [x, y] = point(blueX, 3.65);
      svg += `<ellipse cx="${x}" cy="${y}" rx="${22 + sincePush * 18}" ry="${10 + sincePush * 9}" fill="none" stroke="#6d95be" stroke-width="1.5" opacity="${1 - sincePush / 1.4}"/>`;
    }
    svg += '<rect x="88" y="71" width="158" height="106" rx="12" fill="#fff" stroke="#d8e5db"/>';
    svg += text(106, 95, active ? 'NORTHWARD FORCE ON' : 'EXTRA FORCE PAUSED', 'font-size="8" letter-spacing=".8"');
    svg += text(106, 136, active ? '↑' : fixed((t < 7 ? 13 : 17) - t), 'font-size="38" font-family="Newsreader, Georgia, serif" fill="#377d70"');
    svg += text(107, 161, active ? 'a = 1.5 bricks / count²' : 'counts until return', 'font-size="9"');
    svg += text(390, 340, t < 3 ? 'BLUE' : t < 7 ? 'NONZERO PUSH' : t < 10 ? 'PUSH AGAIN' : t < 17 ? 'ZERO PUSH · NO RESET' : 'WAIT WITHOUT PUSHING', 'text-anchor="middle" font-size="9" letter-spacing=".7" fill="#5b83ad"');
    return svg;
  }

  function render(index, seconds, uid) {
    const time = clamp(seconds, 0, duration - .001);
    return base(uid) + [bounce, curve, echo, drift][index](uid, time) + '</g>';
  }



  const dialog = $('#motion-dialog');
  const hero = $('#hero-motion');
  let heroTime = 0, presentationTime = 0;
  let heroPlaying = !reducedMotion.matches, presentationPlaying = false;
  let heroVisible = false, frame = 0, previousTime = 0, lastDraw = 0;
  let lastHeroScene = -1, lastPresentationScene = -1, lastFocus;
  let exportMode = false;
  const total = scenes.length * duration;
  const stateAt = time => {
    const safe = clamp(time, 0, total - .001), index = Math.floor(safe / duration);
    return {index, seconds: safe - index * duration, scene: scenes[index]};
  };
  function setText(selector, value) {
    const node = $(selector);
    if (node.textContent !== value) node.textContent = value;
  }
  function renderHero() {
    const {index, seconds, scene} = stateAt(heroTime);
    hero.innerHTML = render(index, seconds, 'hero');
    if (lastHeroScene !== index) {
      setText('#hero-scene-index', `SCENE ${scene.id}`);
      setText('#hero-motion-kicker', `0${index + 1} / ${scene.field.toUpperCase()}`);
      setText('#hero-motion-title', scene.title);
      hero.setAttribute('aria-label', `${scene.title} Idealized law illustration.`);
      lastHeroScene = index;
    }
    setText('#hero-motion-caption', phaseAt(scene, seconds)[2]);
    $('#hero-motion-selector').querySelectorAll('button').forEach((button, i) => {
      button.setAttribute('aria-pressed', String(index === i));
      button.style.setProperty('--progress', index === i ? `${seconds / duration * 100}%` : '0%');
    });
    $('#hero-motion-toggle').textContent = heroPlaying ? 'II' : '▶';
    $('#hero-motion-toggle').setAttribute('aria-label', `${heroPlaying ? 'Pause' : 'Play'} overview animation`);
  }
  function renderPresentation() {
    const {index, seconds, scene} = stateAt(presentationTime), phase = phaseAt(scene, seconds);
    $('#presentation-canvas').innerHTML = render(index, seconds, 'presentation');
    if (lastPresentationScene !== index) {
      setText('#presentation-scene', `SCENE ${scene.id} / ${scene.field.toUpperCase()}`);
      setText('#presentation-kicker', `0${index + 1} / ${scene.field}`);
      setText('#presentation-title', scene.title);
      setText('#presentation-intro', scene.intro);
      setText('#presentation-equation', scene.equation);
      setText('#presentation-note', scene.note);
      $('#presentation-canvas').setAttribute('aria-label', `${scene.title} Idealized law illustration.`);
      lastPresentationScene = index;
    }
    setText('#presentation-phase', phase[1]);
    setText('#presentation-caption', phase[2]);
    $('#presentation-chapters').querySelectorAll('button').forEach((button, i) => {
      button.setAttribute('aria-pressed', String(index === i));
      button.style.setProperty('--progress', index === i ? `${seconds / duration * 100}%` : '0%');
    });
    $('#presentation-progress').value = Math.round(presentationTime * 10);
    setText('#presentation-time', `00:${String(Math.floor(presentationTime)).padStart(2, '0')} / 00:48`);
    $('#presentation-play').textContent = presentationPlaying ? 'II' : '▶';
    $('#presentation-play').setAttribute('aria-label', `${presentationPlaying ? 'Pause' : 'Play'} motion atlas`);
  }
  function running() {
    return !exportMode && !document.hidden && (dialog.open ? presentationPlaying : heroPlaying && heroVisible);
  }
  function tick(now) {
    frame = 0;
    if (!running()) return;
    const delta = Math.min((now - previousTime) / 1000, .08);
    previousTime = now;
    if (dialog.open) presentationTime = (presentationTime + delta) % total;
    else heroTime = (heroTime + delta) % total;
    if (now - lastDraw >= 32) {
      if (dialog.open) renderPresentation(); else renderHero();
      lastDraw = now;
    }
    frame = requestAnimationFrame(tick);
  }
  function syncClock() {
    cancelAnimationFrame(frame);
    frame = 0;
    if (running()) { previousTime = performance.now(); frame = requestAnimationFrame(tick); }
  }
  function chapterButtons(selector, choose) {
    $(selector).innerHTML = scenes.map((scene, index) => `<button type="button" data-motion-index="${index}" aria-pressed="${index === 0}"><span>0${index + 1}</span>${scene.short}<i></i></button>`).join('');
    $(selector).querySelectorAll('button').forEach((button, index) => button.addEventListener('click', () => choose(index)));
  }
  chapterButtons('#hero-motion-selector', index => { heroTime = index * duration; renderHero(); });
  chapterButtons('#presentation-chapters', index => { presentationTime = index * duration; renderPresentation(); });
  $('#hero-motion-toggle').addEventListener('click', () => { heroPlaying = !heroPlaying; renderHero(); syncClock(); });
  function openPresentation() {
    if (dialog.open) return;
    lastFocus = document.activeElement;
    presentationTime = 0;
    presentationPlaying = true;
    document.body.classList.add('presentation-open');
    dialog.showModal();
    document.dispatchEvent(new Event('longchang:presentation-open'));
    renderPresentation();
    syncClock();
  }
  document.querySelectorAll('[data-open-presentation]').forEach(button => button.addEventListener('click', openPresentation));
  async function closePresentation() {
    if (document.fullscreenElement === dialog) await document.exitFullscreen().catch(() => {});
    dialog.close();
  }
  $('#presentation-close').addEventListener('click', closePresentation);
  dialog.addEventListener('cancel', event => { event.preventDefault(); closePresentation(); });
  dialog.addEventListener('close', () => {
    presentationPlaying = false;
    document.body.classList.remove('presentation-open');
    if (!exportMode) lastFocus?.focus({preventScroll: true});
    syncClock();
  });
  dialog.addEventListener('click', event => { if (event.target === dialog) closePresentation(); });
  function togglePresentation() { presentationPlaying = !presentationPlaying; renderPresentation(); syncClock(); }
  function changeChapter(delta) {
    const index = (stateAt(presentationTime).index + delta + scenes.length) % scenes.length;
    presentationTime = index * duration;
    renderPresentation();
  }
  $('#presentation-play').addEventListener('click', togglePresentation);
  $('#presentation-previous').addEventListener('click', () => changeChapter(-1));
  $('#presentation-next').addEventListener('click', () => changeChapter(1));
  $('#presentation-progress').addEventListener('input', event => {
    presentationTime = Math.min(total - .001, Number(event.target.value) / 10);
    renderPresentation();
  });
  dialog.addEventListener('keydown', event => {
    if (event.target.matches('input, select, textarea')) return;
    if (event.key === 'ArrowRight') { event.preventDefault(); changeChapter(1); }
    if (event.key === 'ArrowLeft') { event.preventDefault(); changeChapter(-1); }
    if (event.key === ' ' && event.target.tagName !== 'BUTTON') { event.preventDefault(); togglePresentation(); }
  });
  $('#presentation-evidence').addEventListener('click', async () => {
    const id = stateAt(presentationTime).scene.id;
    await closePresentation();
    window.showDiscovery?.(id);
  });
  $('#presentation-fullscreen').hidden = !document.fullscreenEnabled;
  $('#presentation-fullscreen').addEventListener('click', async () => {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await dialog.requestFullscreen();
    } catch (_) {   }
  });
  document.addEventListener('fullscreenchange', () => {
    $('#presentation-fullscreen').setAttribute('aria-label', document.fullscreenElement ? 'Exit full screen' : 'Enter full screen');
  });
  new IntersectionObserver(entries => { heroVisible = entries[0].isIntersecting; syncClock(); }, {threshold: .1}).observe(hero);
  document.addEventListener('visibilitychange', syncClock);
  reducedMotion.addEventListener('change', event => {
    if (event.matches) { heroPlaying = false; presentationPlaying = false; renderHero(); if (dialog.open) renderPresentation(); syncClock(); }
  });
  renderHero();


  window.LongChangMotion = Object.freeze({
    scenes, duration,
    draw: Object.freeze({base, point, points, line, text, polygon, ball, tile, rebound}),
    renderFrame(time) {
      exportMode = true;
      cancelAnimationFrame(frame);
      document.body.classList.add('motion-export', 'presentation-open');
      if (!dialog.open) dialog.showModal();
      presentationPlaying = false;
      presentationTime = clamp(time, 0, total - .001);
      renderPresentation();
    }
  });
})();
