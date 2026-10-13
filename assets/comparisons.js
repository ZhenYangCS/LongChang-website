
(() => {
  'use strict';
  const data = window.LONGCHANG;
  if (!data) return;
  const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fields = [
    {key:'D', label:'Discovery'},
    {key:'C', label:'Correct law'},
    {key:'S', label:'Support'},
    {key:'L', label:'Mean turns'},
    {key:'AF', label:'Failed actions'}
  ];
  const groups = [
    {id:'guidance', title:'Guidance helps.', note:'A task, altered-physics notice and scene clue.', names:['Free exploration','Task-guided'], labels:['Free','Guided']},
    {id:'budget', title:'More turns add little.', note:'The explorer stops after about 42 turns.', names:['100 turns','500 turns'], labels:['100 turns','500 turns']},
    {id:'apparatus', title:'Tool access helps.', note:'The explorer chooses whether to build.', names:['Disabled','Enabled'], labels:['Disabled','Enabled']}
  ];
  const target = document.querySelector('#controlled-comparisons');
  if (target) target.innerHTML = groups.map((group, index) => {
    const conditions = group.names.map(name => data.controlled.find(row => row.name === name));
    return `<article class="controlled-card" data-comparison="${group.id}"><span class="controlled-label">0${index + 1} / ${['TASK GUIDANCE','TURN BUDGET','APPARATUS ACCESS'][index]}</span><h3>${group.title}</h3><p>${group.note}</p><table><caption class="sr-only">GPT-6-Astra: ${group.names.join(' compared with ')}</caption><thead><tr><th scope="col">Metric</th>${group.labels.map(label => `<th scope="col">${label}</th>`).join('')}</tr></thead><tbody>${fields.map(({key, label}) => `<tr ${key === 'D' ? 'class="controlled-discovery"' : ''}><th scope="row">${label}</th>${conditions.map(row => `<td data-condition="${esc(row.name)}" data-metric="${key}"><span>${row[key].toFixed(1)}${key === 'L' ? '' : '%'}</span>${key === 'D' ? `<i class="controlled-track" aria-hidden="true"><i style="width:${row.D}%"></i></i>` : ''}</td>`).join('')}</tr>`).join('')}</tbody></table></article>`;
  }).join('');

  const evolution = document.querySelector('#evolution-results');
  if (evolution) evolution.innerHTML = `<caption class="sr-only">Independent GPT-6-Astra evaluation, three runs per scene; all rates in percent</caption><thead><tr><th scope="col">Scene</th><th scope="col">Discovery</th><th scope="col">Correct law</th><th scope="col">Support</th></tr></thead><tbody>${data.evolution.map((row, index) => `<tr data-evolution-result="${esc(row.name)}" ${index >= 2 ? 'class="evolved-result"' : ''}><th scope="row">${esc(row.name)}${index < 2 ? '<small>Source</small>' : ''}</th>${['D','C','S'].map(key => `<td data-metric="${key}">${row[key].toFixed(1)}%</td>`).join('')}</tr>`).join('')}</tbody>`;
})();
