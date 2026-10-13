/* The reader sees the oracle explicitly; explorers were not given it. */
(() => {
  const $=s=>document.querySelector(s);
  const entries=window.ORACLE_CATALOG;
  if(!entries)return;
  function show(id){
    const oracle=entries[id];if(!oracle)return;
    $('#oracle-plain').textContent=oracle.plain;
    $('#oracle-kind').textContent=id==='01'?'Control scene':'The hidden rule';
    $('#oracle-formula').textContent=oracle.formula;
    $('#oracle-signal').textContent=oracle.measure;
  }
  document.addEventListener('longchang:scene',event=>show(event.detail.id));
  show(window.LongChangAtlas.currentScene());
})();
