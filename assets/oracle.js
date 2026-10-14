
(() => {
  const $=s=>document.querySelector(s);
  const entries=window.ORACLE_CATALOG;
  if(!entries)return;
  function show(id){
    const oracle=entries[id];if(!oracle)return;
    $('#oracle-plain').textContent=oracle.plain;
    const explanation = id==='13' ? 'Only separate touches between the original red and blue balls count. Touch 3 makes both jump at upward speed 4; holding contact counts once.' : oracle.explanation||oracle.law;
    window.LongChangMath.renderText($('#scene-law-text'),explanation,id);
    $('#full-rule-label').textContent='Scene rule';
    $('#oracle-kind').textContent=id==='01'?'Control scene':'The hidden rule';
    window.LongChangMath.render($('#oracle-formula'),id);
    $('#oracle-signal').textContent='Video data · '+oracle.measure;
  }
  document.addEventListener('longchang:scene',event=>show(event.detail.id));
  show(window.LongChangAtlas.currentScene());
})();
