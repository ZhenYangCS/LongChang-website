
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
    {id:'guidance', title:'Task guidance', note:'Discovery rate', names:['Free exploration','Task-guided'], labels:['Without guidance','With guidance'], setup:'Task guidance · 100 turns · task + clues'},
    {id:'budget', title:'Turn budget', metric:'L', note:'Mean turns used', names:['100 turns','500 turns'], labels:['100-turn limit','500-turn limit'], setup:'Turn budget · separate baseline · no context compaction'},
    {id:'apparatus', title:'Apparatus access', note:'Discovery rate', names:['Disabled','Enabled'], labels:['Disabled','Enabled'], setup:'Apparatus access · 100 turns'}
  ];
  const conditionsFor = group => group.names.map(name => data.controlled.find(row => row.name === name));
  const target = document.querySelector('#controlled-comparisons');
  if (target) target.innerHTML = groups.map(group => {
    const conditions = conditionsFor(group);
    const metric = group.metric || 'D';
    return `<article class="controlled-finding" data-comparison="${group.id}" data-primary-metric="${metric}">
      <h4>${group.title}</h4>
      <div class="controlled-pair">${conditions.map((row, index) => `${index ? '<span class="controlled-arrow" aria-hidden="true">→</span>' : ''}<div><span class="controlled-condition">${group.labels[index]}</span><strong data-condition="${esc(row.name)}" data-metric="${metric}">${row[metric].toFixed(1)}${metric === 'L' ? '' : '<small>%</small>'}</strong></div>`).join('')}</div>
      ${group.note ? `<p>${group.note}</p>` : ''}
    </article>`;
  }).join('');

  const tables = document.querySelector('#controlled-tables');
  if (tables) tables.innerHTML = groups.map(group => {
    const conditions = conditionsFor(group);
    const orderedFields = group.metric === 'L' ? [fields.find(field => field.key === 'L'), ...fields.filter(field => field.key !== 'L')] : fields;
    return `<table class="controlled-table"><caption>${group.setup}</caption><thead><tr><th scope="col">Metric</th>${group.labels.map(label => `<th scope="col">${label}</th>`).join('')}</tr></thead><tbody>${orderedFields.map(({key, label}) => `<tr><th scope="row">${label}</th>${conditions.map(row => `<td data-condition="${esc(row.name)}" data-metric="${key}">${row[key].toFixed(1)}${key === 'L' ? '' : '%'}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
  }).join('');

})();
