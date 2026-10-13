/* Explore the frozen paper results without changing their evaluation scale. */
(() => {
  'use strict';
  const data = window.LONGCHANG;
  const chart = document.querySelector('#model-chart');
  if (!data || !chart) return;
  const inspector = document.querySelector('#results-inspector');
  const announcement = document.querySelector('#results-announcement');
  const controls = [...document.querySelectorAll('[data-result-view]')];
  const sort = document.querySelector('#results-sort');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const narrow = matchMedia('(max-width: 800px)');
  const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const metrics = [{key:'D', name:'Discovery'}, {key:'C', name:'Correct law'}, {key:'S', name:'Support'}];
  const scenes = data.scenes.filter(scene => scene.id !== '01');
  let view = 'all';
  let selected = data.models[0];
  const rows = data.models.map(model => {
    const row = document.createElement('button');
    row.type = 'button';
    row.className = 'result-row';
    row.dataset.model = model.name;
    row.setAttribute('aria-controls', 'results-inspector');
    row.setAttribute('aria-label', `${model.name}. ${metrics.map(m => `${m.name}: ${model[m.key].toFixed(1)}%`).join('. ')}. Show model details.`);
    row.innerHTML = `<span class="result-model-name">${esc(model.name)}</span><span class="result-lanes" aria-hidden="true">${metrics.map(({key}) => `<span class="result-lane result-${key}" data-result-metric="${key}" data-value="${model[key]}"><i style="width:${model[key]}%"></i></span>`).join('')}</span><span class="result-row-value" aria-hidden="true"></span>`;
    row.addEventListener('click', () => select(model));
    chart.append(row);
    return {model, row};
  });

  function inspect() {
    const sceneMetric = view === 'all' ? 'D' : view;
    const sceneLabel = metrics.find(metric => metric.key === sceneMetric).name;
    inspector.innerHTML = `<button type="button" class="result-inspector-close" aria-label="Close model details">×</button><div class="result-inspector-heading"><span class="result-inspector-label">SELECTED MODEL</span><a class="result-data-link" href="downloads/model-results.csv" download aria-label="Download all model metrics (CSV)" title="Download all model metrics (CSV)"><svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true"><path d="M12 3v12m-4-4 4 4 4-4M5 16v5h14v-5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg></a></div><h3 id="result-model-title">${esc(selected.name)}</h3><dl class="result-scores">${metrics.map(({key, name}) => {
      const count = scenes.reduce((sum, scene) => sum + selected.scenes[scene.id][key], 0);
      return `<div class="result-score result-${key}" ${view === key ? 'data-emphasized="true"' : ''}><dt><i class="result-dot" aria-hidden="true"></i>${name}</dt><dd><strong>${selected[key].toFixed(1)}<small>%</small></strong><span>${count} / 42 runs</span></dd></div>`;
    }).join('')}</dl><div class="result-scene-heading"><span>${sceneLabel} by scene</span><small>Passes / 3</small></div><div class="result-scenes">${scenes.map(scene => {
      const value = selected.scenes[scene.id][sceneMetric];
      const label = `Scene ${scene.id}: ${scene.name}. ${sceneLabel}: ${value} of 3 runs.`;
      const detail = `Scene ${scene.id}: ${scene.name}. ${metrics.map(metric => `${metric.name}: ${selected.scenes[scene.id][metric.key]}/3`).join('. ')}.`;
      const canWatch = sceneMetric === 'D' && selected.name === 'GPT-6-Astra' && value > 0;
      const content = `<span>${scene.id}</span><strong>${value}/3</strong>`;
      return canWatch
        ? `<button type="button" class="result-scene" data-level="${value}" data-result-scene="${scene.id}" aria-label="${esc(label)} Watch a successful exploration." title="${esc(detail)} Watch an exploration.">${content}</button>`
        : `<span class="result-scene" data-level="${value}" title="${esc(detail)}" aria-label="${esc(label)}">${content}</span>`;
    }).join('')}</div><div class="result-control" title="Scene 01 follows ordinary physics. Reports are rejected for false claims of altered physics or unsupported explanations."><span>Normal control</span><span><strong>${selected.R} / 3</strong> rejected</span></div>`;
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
    const key = view === 'all' ? 'D' : view;
    rows.forEach(({row}) => row.getAnimations().forEach(animation => animation.cancel()));
    const positions = new Map(rows.map(({row}) => [row, row.getBoundingClientRect().top]));
    const ordered = [...rows];
    if (sort.value === 'score') ordered.sort((a, b) => b.model[key] - a.model[key]);
    chart.dataset.view = view;
    sort.options[1].textContent = view === 'all' ? 'Discovery first' : 'Highest first';
    controls.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.resultView === view)));
    ordered.forEach(({model, row}) => {
      row.querySelectorAll('[data-result-metric]').forEach(lane => {
        lane.hidden = view !== 'all' && lane.dataset.resultMetric !== view;
      });
      row.querySelector('.result-row-value').textContent = view === 'all' ? '›' : `${model[key].toFixed(1)}%`;
      chart.append(row);
    });
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
    announcement.textContent = `${view === 'all' ? 'All metrics' : metrics.find(m => m.key === view).name}. ${sort.value === 'score' ? `Sorted by ${metrics.find(m => m.key === key).name.toLowerCase()}, highest first.` : 'Paper order.'} ${selected.name} selected.`;
  }

  controls.forEach(button => button.addEventListener('click', () => {
    view = button.dataset.resultView;
    render();
  }));
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
      window.showDiscovery?.(button.dataset.resultScene);
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
