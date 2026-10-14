
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
    {id:'guidance', title:'Guidance helps.', names:['Free exploration','Task-guided'], labels:['Free','Guided'], setup:'Task guidance · 100-turn limit'},
    {id:'budget', title:'More time goes unused.', note:'About 42 turns used under either limit.', names:['100 turns','500 turns'], labels:['100 turns','500 turns'], setup:'Turn budget · no context compaction'},
    {id:'apparatus', title:'Tool access helps.', names:['Disabled','Enabled'], labels:['Tools off','Tools on'], setup:'Tool access · 100-turn limit'}
  ];
  const conditionsFor = group => group.names.map(name => data.controlled.find(row => row.name === name));
  const target = document.querySelector('#controlled-comparisons');
  if (target) target.innerHTML = groups.map(group => {
    const conditions = conditionsFor(group);
    return `<article class="controlled-finding" data-comparison="${group.id}">
      <h4>${group.title}</h4>
      <div class="controlled-pair">${conditions.map((row, index) => `${index ? '<span class="controlled-arrow" aria-hidden="true">→</span>' : ''}<div><span class="controlled-condition">${group.labels[index]}</span><strong data-condition="${esc(row.name)}" data-metric="D">${row.D.toFixed(1)}<small>%</small></strong></div>`).join('')}</div>
      ${group.note ? `<p>${group.note}</p>` : ''}
    </article>`;
  }).join('');

  const tables = document.querySelector('#controlled-tables');
  if (tables) tables.innerHTML = groups.map(group => {
    const conditions = conditionsFor(group);
    return `<table class="controlled-table"><caption>${group.setup}</caption><thead><tr><th scope="col">Metric</th>${group.labels.map(label => `<th scope="col">${label}</th>`).join('')}</tr></thead><tbody>${fields.map(({key, label}) => `<tr><th scope="row">${label}</th>${conditions.map(row => `<td data-condition="${esc(row.name)}" data-metric="${key}">${row[key].toFixed(1)}${key === 'L' ? '' : '%'}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
  }).join('');

  const evolution = document.querySelector('#evolution-results');
  if (evolution) {
    const labels=['Source 15','Source 14','Generate','Refine','Compose'];
    evolution.innerHTML = `<caption class="sr-only">Independent GPT-6-Astra evaluation, three runs per scene; all rates in percent</caption><thead><tr><th scope="col">Metric</th>${data.evolution.map((row,i)=>`<th scope="col" data-evolution-result="${esc(row.name)}" title="${esc(row.name)}">${labels[i]}</th>`).join('')}</tr></thead><tbody>${fields.slice(0,3).map(({key,label})=>`<tr><th scope="row">${label}</th>${data.evolution.map((row,i)=>`<td data-condition="${esc(row.name)}" data-metric="${key}" ${i>=2?'class="evolved-result"':''}>${row[key].toFixed(1)}%</td>`).join('')}</tr>`).join('')}</tbody>`;
  }
})();
