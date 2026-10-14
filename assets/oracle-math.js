
(() => {
  'use strict';
  const row = (...parts) => `<mrow>${parts.join('')}</mrow>`;
  const escape = text => String(text).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
  const variable = name => `<mi>${escape(name)}</mi>`;
  const number = value => `<mn>${value}</mn>`;
  const operator = value => `<mo>${escape(value)}</mo>`;
  const word = value => `<mtext>${escape(value)}</mtext>`;
  const sub = (base, value) => `<msub>${base}${value}</msub>`;
  const sup = (base, value) => `<msup>${base}${value}</msup>`;
  const frac = (a, b) => `<mfrac>${a}${b}</mfrac>`;
  const parens = value => row(operator('('), value, operator(')'));
  const abs = value => row(operator('|'), value, operator('|'));
  const equals = operator('='), v = variable('v'), m = variable('m'), t = variable('t');
  const g = sub(variable('g'), number(0)), vector = '<mi mathvariant="bold">v</mi>';
  const rebound = coefficient => row(sub(v, operator('↑')), equals, number(coefficient), abs(sub(v, operator('↓'))));

  const formulas = {
    '01': [['', word('Ordinary physics')]],
    '02': [['', row(variable('F'), equals, frac(number(20), sup(variable('r'), number(2))), '<mspace width="1em"/>', parens(row(variable('r'), operator('≥'), number('0.5'))))]],
    '03': [['', row(variable('a'), equals, g, `<msqrt>${frac(number(1), m)}</msqrt>`)]],
    '04': [['', row(variable('g'), parens(t), equals, g, operator('['), number(1), operator('+'), number('0.3'), '<mi mathvariant="normal">sin</mi>', parens(frac(row(number(2), variable('π'), t), number(6))), operator(']'))]],
    '05': [['', row(variable('F'), equals, operator('−'), number(8), parens(row(variable('s'), operator('−'), number('2.5'))), frac(vector, variable('s')))], ['Above threshold', row(variable('s'), operator('>'), number('2.5'))]],
    '06': [['', row(variable('F'), equals, number('1.2'), parens(row(sub(v, variable('y')), operator(','), operator('−'), sub(v, variable('x')), operator(','), number(0))))]],
    '07': [['Red tile', rebound('0.90'), 'red'], ['Blue tile', rebound('0.15'), 'blue']],
    '08': [['', row(variable('p'), equals, frac(row(m, vector), row(number(1), operator('−'), frac(sup(abs(vector), number(2)), sup(number('2.2'), number(2))))))]],
    '09': [['Enter', row(vector, operator('←'), number('0.4'), vector)], ['Exit', row(vector, operator('←'), number('2.5'), vector)]],
    '10': [['Seed', row(sub(v, variable('x')), equals, number('0.35'))], ['Gain per step', row(operator('×'), number('1.0015'))]],
    '11': [['At separation', row(sub(vector, word('after')), equals, number('1.8'), sub(vector, word('before')))]],
    '12': [['Colors', row(parens(row(sub(variable('c'), variable('A')), operator(','), sub(variable('c'), variable('B')))), operator('→'), parens(row(sub(variable('c'), variable('B')), operator(','), sub(variable('c'), variable('A'))))) ]],
    '13': [['Every third contact', row(sub(v, variable('z')), operator('←'), number(4))]],
    '14': [['', row(sub(vector, word('green')), parens(row(t, operator('+'), number(12))), operator('←'), sub(vector, word('red')), parens(sup(t, operator('+'))))]],
    '15': [['', row(sub(variable('F'), variable('y')), equals, number('1.5'), m)], ['Launch pauses', row(number(10), '<mspace width="0.25em"/>', word('counts'))]],
    'evo-generate': [['Repulsion', row(variable('a'), equals, number('1.5'))], ['After push', row(variable('Δt'), operator('≥'), number(10))]],
    'evo-mutate': [['Drift', row(sub(variable('a'), variable('y')), equals, number('1.5'))], ['When', row(variable('Δt'), operator('≥'), number(10), operator('∧'), word('blue outside'))]],
    'evo-compose': [['Drift resumes', row(variable('Δt'), operator('≥'), number(10))], ['Velocity copy', row(sub(vector, word('green')), parens(number(12)), operator('←'), sub(vector, word('red')), parens(sup(number(0), operator('+'))))]]
  };
  function render(element, id) {
    if (!element) return;
    element.classList.add('typeset-rule');
    const parts = formulas[id];
    if (!parts) { element.textContent = window.ORACLE_CATALOG?.[id]?.formula || ''; return; }
    element.replaceChildren(...parts.map(([label, expression, color]) => {
      const part = document.createElement('span');part.className = 'formula-part';
      if (label) { const tag = document.createElement('span');tag.className = 'formula-label' + (color ? ' formula-' + color : '');tag.textContent = label;part.append(tag); }
      const holder = document.createElement('span');
      holder.innerHTML = `<math xmlns="http://www.w3.org/1998/Math/MathML">${expression}</math>`;
      part.append(holder.firstElementChild);return part;
    }));
  }
  const vmax = sub(v, word('max')), d = variable('d'), r = variable('r');
  const cappedDistance = row('<mi mathvariant="normal">max</mi>', parens(row(r, operator(','), number('0.5'))));
  const attraction = row(variable('F'), equals, frac(row(number(20), d), sup(cappedDistance, number(3))));
  const inline = {
    '02': [['F=20d/max(r,0.5)^3', attraction], ['r=|d|',row(r,equals,abs(d))], ['d',d]],
    '03': [['g_0√(m_0/m)',row(g,`<msqrt>${frac(sub(m,number(0)),m)}</msqrt>`)], ['m_0=1',row(sub(m,number(0)),equals,number(1))]],
    '04': [['g(t)=g_0[1+0.3sin(2π t/6)]',formulas['04'][0][1]]],
    '05': [['F=-8(s-2.5)v/s',formulas['05'][0][1]], ['s=|v|>2.5',row(variable('s'),equals,abs(vector),operator('>'),number('2.5'))]],
    '06': [['F=1.2(v_y,-v_x,0)',formulas['06'][0][1]], ['|v_x|+|v_y|>0.001',row(abs(sub(v,variable('x'))),operator('+'),abs(sub(v,variable('y'))),operator('>'),number('0.001'))]],
    '07': [['e=0.9',row(variable('e'),equals,number('0.9'))], ['e=0.15',row(variable('e'),equals,number('0.15'))]],
    '08': [['p=mv/(1-|v|^2/v_max^2)',row(variable('p'),equals,frac(row(m,vector),row(number(1),operator('−'),frac(sup(abs(vector),number(2)),sup(vmax,number(2))))))], ['v_max=2.2',row(vmax,equals,number('2.2'))]],
    '09': [['|x-2|<1.5',row(abs(row(variable('x'),operator('−'),number(2))),operator('<'),number('1.5'))], ['|y|<1.5',row(abs(variable('y')),operator('<'),number('1.5'))]],
    '10': [['|x|<2',row(abs(variable('x')),operator('<'),number(2))], ['|y|<2',row(abs(variable('y')),operator('<'),number(2))], ['v_x=0.35',formulas['10'][0][1]], ['s=|v|<0.35',row(variable('s'),equals,abs(vector),operator('<'),number('0.35'))], ['0.35≤ s<6',row(number('0.35'),operator('≤'),variable('s'),operator('<'),number(6))]],
    '15': [['F_y=1.5m',formulas['15'][0][1]]]
  };
  function renderText(element, text, id) {
    const matches = inline[id] || [];let remaining = text;
    element.replaceChildren();
    while (remaining) {
      let best;
      for (const [source, expression] of matches) {

        const index = source.length===1 ? remaining.search(new RegExp('\\b'+source+'\\b')) : remaining.indexOf(source);
        if (index>=0 && (!best || index<best.index || (index===best.index && source.length>best.source.length))) best={source,expression,index};
      }
      if (!best) { element.append(document.createTextNode(remaining));break; }
      element.append(document.createTextNode(remaining.slice(0,best.index)));
      const holder=document.createElement('span');
      holder.innerHTML=`<math class="inline-rule-math" xmlns="http://www.w3.org/1998/Math/MathML">${best.expression}</math>`;
      element.append(holder.firstElementChild);remaining=remaining.slice(best.index+best.source.length);
    }
  }
  window.LongChangMath = Object.freeze({render,renderText});
})();
