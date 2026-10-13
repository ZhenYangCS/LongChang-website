
(() => {
  const $=s=>document.querySelector(s);
  const entries=window.ORACLE_CATALOG;
  if(!entries)return;
  function show(id){
    const oracle=entries[id];if(!oracle)return;
    $('#oracle-plain').textContent=oracle.plain;
    window.LongChangMath.renderText($('#scene-law-text'),oracle.explanation||oracle.law,id);
    $('#full-rule-label').textContent='Scene rule';
    $('#oracle-kind').textContent=id==='01'?'Control scene':'The hidden rule';
    window.LongChangMath.render($('#oracle-formula'),id);
    $('#oracle-signal').textContent='Demo data · '+oracle.measure;
  }
  document.addEventListener('longchang:scene',event=>show(event.detail.id));
  show(window.LongChangAtlas.currentScene());
})();
