/* The reader sees the oracle explicitly; explorers were not given it. */
(() => {
  const $=s=>document.querySelector(s);
  const entries=window.ORACLE_CATALOG;
  if(!entries)return;
  function show(id){
    const oracle=entries[id];if(!oracle)return;
    $('#oracle-formula').textContent=oracle.formula;
    $('#oracle-condition').textContent=oracle.condition;
    $('#oracle-effect').textContent=oracle.effect;
    $('#oracle-scope').textContent=oracle.scope;
    $('#oracle-signal').textContent=oracle.measure;
    $('#oracle-status').textContent='Oracle revealed to the reader';
  }
  document.addEventListener('longchang:scene',event=>show(event.detail.id));
  show(window.LongChangAtlas.currentScene());
})();
