
(() => {
  'use strict';
  const data = window.LONGCHANG;
  const chart = document.querySelector('#model-chart');
  if (!data || !chart) return;
  const inspector = document.querySelector('#results-inspector');
  const announcement = document.querySelector('#results-announcement');
  const sort = document.querySelector('#results-sort');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const narrow = matchMedia('(max-width: 800px)');
  const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const metrics = [{key:'D', name:'Discovery'}, {key:'C', name:'Correct law'}, {key:'S', name:'Support'}];
  const scenes = data.scenes.filter(scene => scene.id !== '01');
  const behavior = [
    {key:'L', label:'Mean turns', unit:'', detail:'Mean turns used across all 45 runs.'},
    {key:'ES', label:'Early stops', unit:'%', detail:'Runs ending before the 100-turn limit.'},
    {key:'CS', label:'Runs with a build', unit:' / 45', detail:'Runs with at least one successfully built apparatus.'},
    {key:'CF', label:'Build failures', unit:'%', detail:'Failed build attempts as a percentage of all build attempts.'},
    {key:'AF', label:'Action failures', unit:'%', detail:'Turns with failed actions as a percentage of all turns.'}
  ];
  let selected = data.models[0];
  const rows = data.models.map(model => {
    const row = document.createElement('button');
    row.type = 'button';
    row.className = 'result-row';
    row.dataset.model = model.name;
    row.setAttribute('aria-controls', 'results-inspector');
    row.setAttribute('aria-label', `${model.name}. Discovery: ${model.D.toFixed(1)}%. Show model details.`);
    row.innerHTML = `<span class="result-model-name">${esc(model.name)}</span><span class="result-lanes" aria-hidden="true"><span class="result-lane result-D" data-result-metric="D" data-value="${model.D}"><i style="width:${model.D}%"></i></span></span><span class="result-row-value" aria-hidden="true">${model.D.toFixed(1)}%</span>`;
    row.addEventListener('click', () => select(model));
    chart.append(row);
    return {model, row};
  });

  function inspect() {
    const sceneResults = `<div class="result-scene-table-head"><span>Scene</span>${metrics.map(({key,name}) => `<span class="result-${key}" title="${name}">${key}</span>`).join('')}</div><div class="result-scenes">${scenes.map(scene => {
      const detail = `Scene ${scene.id}: ${scene.name}. ${metrics.map(metric => `${metric.name}: ${selected.scenes[scene.id][metric.key]}/3`).join('. ')}.`;
      return `<button type="button" class="result-scene" data-result-scene="${scene.id}" title="${esc(detail)}" aria-label="${esc(detail)} Read all three reports and their evaluations."><span class="result-scene-name"><small>${scene.id}</small>${esc(scene.name)}</span>${metrics.map(({key}) => `<strong class="result-${key}" data-level="${selected.scenes[scene.id][key]}">${selected.scenes[scene.id][key]}/3</strong>`).join('')}</button>`;
    }).join('')}</div>`;
    inspector.innerHTML = `<button type="button" class="result-inspector-close" aria-label="Close model details">×</button><div class="result-inspector-heading"><h3 id="result-model-title">${esc(selected.name)}</h3><a class="result-data-link" href="downloads/model-results.csv" download aria-label="Download all model metrics (CSV)" title="Download all model metrics (CSV)"><svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true"><path d="M12 3v12m-4-4 4 4 4-4M5 16v5h14v-5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg></a></div><dl class="result-scores">${metrics.map(({key, name}) => {
      const count = scenes.reduce((sum, scene) => sum + selected.scenes[scene.id][key], 0);
      return `<div class="result-score result-${key}" ${key === 'D' ? 'data-emphasized="true"' : ''}><dt><i class="result-dot" aria-hidden="true"></i>${name}</dt><dd><strong>${selected[key].toFixed(1)}<small>%</small></strong><span>${count} / 42 runs</span></dd></div>`;
    }).join('')}</dl><div class="result-behavior-heading"><span>Exploration</span><small>All 45 runs</small></div><dl class="result-behavior">${behavior.map(({key, label, unit, detail}) => `<div title="${esc(selected[key] == null ? 'No build attempts.' : detail)}"><dt>${label}</dt><dd data-behavior="${key}">${selected[key] == null ? '—' : `${key === 'CS' ? selected[key] : selected[key].toFixed(1)}${unit}`}</dd></div>`).join('')}</dl><div class="result-scene-heading"><span>Reports by scene</span><small>Passes / 3</small></div>${sceneResults}<button type="button" class="result-control" data-result-scene="01" title="Read the normal-control reports and evaluations."><span>01 · Normal control ↗</span><span><strong>${selected.R} / 3</strong> rejected</span></button>`;
  }

  function select(model, announce = true) {
    selected = model;
    rows.forEach(({model: item, row}) => {
      const active = item === selected;
      row.setAttribute('aria-pressed', String(active));
      row.tabIndex = active ? 0 : -1;
    });
    inspect();
    if (announce) {
      announcement.textContent = `${selected.name} selected. ${metrics.map(m => `${m.name}: ${selected[m.key].toFixed(1)}%`).join('. ')}.`;
      if (inspector.hasAttribute('popover')) {
        inspector.showPopover();
        inspector.querySelector('.result-inspector-close').focus({preventScroll:true});
      }
    }
  }

  function render(animate = true) {
    rows.forEach(({row}) => row.getAnimations().forEach(animation => animation.cancel()));
    const positions = new Map(rows.map(({row}) => [row, row.getBoundingClientRect().top]));
    const ordered = [...rows];
    if (sort.value === 'score') ordered.sort((a, b) => b.model.D - a.model.D);
    ordered.forEach(({row}) => chart.append(row));
    if (animate && !reduced.matches) {
      ordered.forEach(({row}) => {
        const offset = positions.get(row) - row.getBoundingClientRect().top;
        if (Math.abs(offset) > 1) row.animate([{transform:`translateY(${offset}px)`}, {transform:'translateY(0)'}], {duration:260, easing:'ease-out'});
        row.querySelectorAll('.result-lane:not([hidden]) i').forEach(bar => {
          bar.getAnimations().forEach(animation => animation.cancel());
          bar.animate([{transform:'scaleX(0)'}, {transform:'scaleX(1)'}], {duration:320, easing:'ease-out'});
        });
      });
    }
    inspect();
    announcement.textContent = `Discovery. ${sort.value === 'score' ? 'Sorted by discovery rate, highest first.' : 'Paper order.'} ${selected.name} selected.`;
  }

  sort.addEventListener('change', () => render());
  chart.addEventListener('keydown', event => {
    if (!['ArrowDown','ArrowUp','Home','End'].includes(event.key)) return;
    const buttons = [...chart.querySelectorAll('.result-row')];
    const current = buttons.indexOf(document.activeElement);
    if (current < 0) return;
    event.preventDefault();
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 : (current + (event.key === 'ArrowDown' ? 1 : -1) + buttons.length) % buttons.length;
    buttons[next].click();
    buttons[next].focus({preventScroll:true});
  });
  inspector.addEventListener('click', event => {
    if (event.target.closest('.result-inspector-close')) {
      inspector.hidePopover();
      rows.find(item => item.model === selected).row.focus({preventScroll:true});
      return;
    }
    const button = event.target.closest('[data-result-scene]');
    if (button) {
      if (inspector.hasAttribute('popover')) inspector.hidePopover();
      window.showResultEvidence?.(selected.name, button.dataset.resultScene);
    }
  });
  function layout() {
    const popup = narrow.matches && typeof inspector.showPopover === 'function';
    if (popup) {
      inspector.setAttribute('popover', 'auto');
      inspector.setAttribute('role', 'dialog');
    } else {
      if (inspector.hasAttribute('popover')) inspector.hidePopover();
      inspector.removeAttribute('popover');
      inspector.removeAttribute('role');
    }
    rows.forEach(({row}) => popup ? row.setAttribute('aria-haspopup', 'dialog') : row.removeAttribute('aria-haspopup'));
  }
  narrow.addEventListener('change', layout);
  layout();
  select(selected, false);
  render(false);
})();
