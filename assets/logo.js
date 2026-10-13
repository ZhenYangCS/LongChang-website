/* A shared, bounded gaze; blinking stays on the outer eye groups. */
(() => {
  'use strict';
  const logos = [...document.querySelectorAll('.longchang-logo')];
  if (!logos.length) return;
  const visible = new Set(logos);

  let pointer = null;
  let frame = 0;
  let release = 0;

  function paint() {
    frame = 0;
    for (const logo of visible) {
      let x = 0, y = 0;
      if (pointer) {
        const box = logo.getBoundingClientRect();
        // Each logo looks from its own eyes' midpoint toward the same target.
        const dx = pointer.x - (box.left + box.width * .5);
        const dy = pointer.y - (box.top + box.height * .6);
        const distance = Math.hypot(dx, dy, 70);
        x = 1.55 * dx / distance;
        y = .95 * dy / distance;
      }
      logo.style.setProperty('--gaze-x', `${x.toFixed(3)}px`);
      logo.style.setProperty('--gaze-y', `${y.toFixed(3)}px`);
    }
  }

  function schedule() {
    if (!frame) frame = requestAnimationFrame(paint);
  }

  function reset() {
    clearTimeout(release);
    pointer = null;
    schedule();
  }

  function follow(event) {
    if (!visible.size || !event.isPrimary) return;
    clearTimeout(release);
    pointer = {x:event.clientX, y:event.clientY};
    schedule();
  }

  document.addEventListener('pointermove', follow, {passive:true});
  document.addEventListener('pointerdown', follow, {passive:true});
  document.addEventListener('pointerup', event => {
    if (event.isPrimary && event.pointerType === 'touch') {
      release = setTimeout(reset, 800);
    }
  }, {passive:true});
  document.addEventListener('pointercancel', reset, {passive:true});
  document.documentElement.addEventListener('pointerleave', event => {
    if (event.pointerType !== 'touch') reset();
  }, {passive:true});
  window.addEventListener('blur', reset);
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) reset();
  });
  const reposition = () => { if (pointer && visible.size) schedule(); };
  window.addEventListener('resize', reposition, {passive:true});
  window.addEventListener('scroll', reposition, {passive:true});

  // One listener set for every logo; only visible logos receive pointer updates.
  const observer = new IntersectionObserver(entries => {
    for (const {target, isIntersecting} of entries) {
      if (isIntersecting) {
        visible.add(target);
      } else {
        visible.delete(target);
        target.style.removeProperty('--gaze-x');
        target.style.removeProperty('--gaze-y');
      }
    }
    if (!visible.size) reset();
    else if (pointer) schedule();
  });
  logos.forEach(logo => observer.observe(logo));
})();
