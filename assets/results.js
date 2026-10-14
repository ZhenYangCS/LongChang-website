
(() => {
  'use strict';
  const data = window.LONGCHANG;
  const chart = document.querySelector('#model-chart');
  if (!data || !chart) return;
  const inspector = document.querySelector('#results-inspector');
  const explorationPanel = document.querySelector('#result-exploration');
  const outcomesPanel = document.querySelector('#result-outcomes');
  const announcement = document.querySelector('#results-announcement');
  const narrow = matchMedia('(max-width: 1000px)');
  const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const metrics = [
    {key:'D', name:'Discovery', hint:'C + S must pass', detail:'Both C (correct law) and S (evidence support) must pass in the same run.'},
    {key:'C', name:'Correct law', hint:'Full rule identified', detail:'The report identifies the complete altered law.'},
    {key:'S', name:'Evidence support', hint:'Claims backed by evidence', detail:'The report’s claims and reasoning are supported by its recorded experiments.'}
  ];
  const scenes = data.scenes.filter(scene => scene.id !== '01');
  const alteredRuns = scenes.length * 3, allRuns = data.scenes.length * 3;
  const behavior = [
    {key:'L', label:'Turns used', hint:'Average · 100 max', unit:'', detail:'Mean turns used out of the 100 available per run.'},
    {key:'ES', label:'Early stops', hint:'Before turn 100', unit:'%', detail:'Share of runs ending before the 100-turn limit; this does not indicate success.'},
    {key:'CS', label:'Built a tool', hint:'Runs with a build', unit:` / ${allRuns}`, detail:'Runs that successfully built at least one instrument.'},
    {key:'CF', label:'Build failures', hint:'Of build attempts', unit:'%', detail:'Failed build attempts divided by all build attempts; lower means fewer failures.'},
    {key:'AF', label:'Action errors', hint:'Of action turns', unit:'%', detail:'Turns with failed actions divided by all turns; lower means fewer execution failures.'}
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
    const counts = Object.fromEntries(metrics.map(({key}) => [key, scenes.reduce((sum, scene) => sum + selected.scenes[scene.id][key], 0)]));
    const exploration = `<div class="result-behavior-heading"><span>Exploration behavior</span><small>${allRuns} runs incl. control</small></div><dl class="result-behavior">${behavior.map(({key, label, hint, unit, detail}) => {
      const value = selected[key] == null ? '—' : key === 'CS' ? selected[key] : selected[key].toFixed(1);
      return `<div class="result-metric" title="${esc(selected[key] == null ? 'No build attempts.' : detail)}"><dt>${label}</dt><dd><span class="result-metric-value" data-behavior="${key}"><strong>${value}</strong><span>${selected[key] == null ? '' : unit}</span></span><span class="result-metric-hint">${selected[key] == null ? 'No attempts' : hint}</span></dd></div>`;
    }).join('')}</dl>`;
    explorationPanel.hidden = narrow.matches;
    explorationPanel.innerHTML = narrow.matches ? '' : exploration;
    const sceneHead = `<div class="result-scene-table-head"><span>Scene</span>${metrics.map(({key,name}) => `<span class="result-${key}" title="${name}">${key}</span>`).join('')}</div>`;
    const sceneResults = `<div class="result-scene-heads" aria-hidden="true">${sceneHead}${sceneHead}</div><div class="result-scenes">${scenes.map(scene => {
      const detail = `Scene ${scene.id}: ${scene.name}. ${metrics.map(metric => `${metric.name}: ${selected.scenes[scene.id][metric.key]}/3`).join('. ')}.`;
      return `<button type="button" class="result-scene" data-result-scene="${scene.id}" title="${esc(detail)}" aria-label="${esc(detail)} Read all three reports and their evaluations."><span class="result-scene-name"><small>${scene.id}</small>${esc(scene.name)}</span>${metrics.map(({key}) => `<strong class="result-${key}" data-level="${selected.scenes[scene.id][key]}">${selected.scenes[scene.id][key]}/3</strong>`).join('')}</button>`;
    }).join('')}</div>`;
    const outcomes = `<div class="result-behavior-heading"><span>Discovery outcome</span><small>${alteredRuns} altered runs</small></div><dl class="result-scores">${metrics.map(({key, name, hint, detail}) => {
      return `<div class="result-metric result-score result-${key}" title="${esc(detail)} ${counts[key]} of ${alteredRuns} runs passed." ${key === 'D' ? 'data-emphasized="true"' : ''}><dt><span class="result-metric-code" aria-hidden="true">${key}</span>${name}</dt><dd aria-label="${selected[key].toFixed(1)} percent; ${counts[key]} of ${alteredRuns} runs passed."><span class="result-metric-value"><strong>${selected[key].toFixed(1)}</strong><span>%</span></span><span class="result-metric-hint">${hint}</span></dd></div>`;
    }).join('')}</dl>`;
    outcomesPanel.hidden = narrow.matches;
    outcomesPanel.innerHTML = narrow.matches ? '' : outcomes;
    inspector.innerHTML = `<button type="button" class="result-inspector-close" aria-label="Close model details">×</button><div class="result-inspector-heading"><h3 id="result-model-title">${esc(selected.name)}</h3></div>${narrow.matches ? `<section class="result-outcomes">${outcomes}</section><section class="result-exploration">${exploration}</section>` : ''}<div class="result-scene-heading"><span>Reports by scene</span><small>Passes / 3</small></div>${sceneResults}<button type="button" class="result-control" data-result-scene="01" title="Read the normal-control reports and evaluations."><span>01 · Normal control ↗</span><span><strong>${selected.R} / 3</strong> rejected</span></button>`;
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
  narrow.addEventListener('change', () => { layout(); inspect(); });
  layout();
  select(selected, false);
})();
