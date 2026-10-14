(() => {
  'use strict';
  const $ = selector => document.querySelector(selector);
  const dialog = $('#result-evidence-dialog'), turnDialog = $('#evidence-turn-dialog');
  const reports = new Map(), records = new Map(), english = new Map();
  let summaries = new Map();
  const metrics = [{key:'D', name:'Discovery'}, {key:'C', name:'Correct law'}, {key:'S', name:'Evidence support'}];
  let group = null, selected = 0, version = 0, turnVersion = 0, origin = null, turnOrigin = null, currentRecord = null, request = null;
  const node = (tag, className, text) => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined && text !== null) element.textContent = text;
    return element;
  };
  function textBlock(tag, className, text) {
    const element = node(tag, className, text);
    if (/[\u3400-\u9fff]/.test(text || '')) element.lang = 'zh';
    return element;
  }
  function preview(text) {
    const value = String(text || '').replace(/\s+/g, ' ').trim();
    const chinese = /[\u3400-\u9fff]/.test(value);
    const limit = chinese ? 62 : 150;
    if (value.length <= limit) return value;
    const excerpt = value.slice(0, limit);
    const sentence = excerpt.match(/^.*[。！？.!?](?=\s|$)/)?.[0];
    if (sentence && sentence.length >= limit / 3) return sentence;
    return (chinese ? excerpt : excerpt.replace(/\s+\S*$/, ''))+'…';
  }
  function resultMark(key, passed) {
    const name = metrics.find(metric => metric.key === key).name;
    const value = passed === null ? '—' : (passed ? '✓' : '×');
    const mark = node('span', `evidence-check result-${key}`, `${key} ${value}`);
    mark.dataset.pass = passed === null ? 'na' : String(passed);
    mark.setAttribute('aria-label', `${name}: ${passed === null ? 'not applicable' : passed ? 'pass' : 'fail'}`);
    return mark;
  }
  function status(text, retry = false) {
    $('#evidence-status').hidden = !text;
    $('#evidence-status span').textContent = text;
    $('#evidence-retry').hidden = !retry;
  }
  function format(value) { return typeof value === 'string' ? value : JSON.stringify(value, null, 2); }
  function renderRun(index) {
    selected = index;
    const run = group.runs[index];
    dialog.dataset.run = String(run.repeat);
    $('#evidence-runs').querySelectorAll('button').forEach((button, i) => {
      button.setAttribute('aria-selected', String(i === index));
      button.tabIndex = i === index ? 0 : -1;
    });
    $('#evidence-content').setAttribute('aria-labelledby', `evidence-run-${run.repeat}`);
    const checks = $('#evidence-checks');
    checks.replaceChildren();
    if (run.control) {
      checks.append(node('strong', '', run.accepted ? 'Normal-control report accepted' : 'Normal-control report rejected'));
      checks.append(node('span', 'evidence-check-note', 'No altered law to discover.'));
    } else {
      const verdict = run.D ? 'Discovery: law and evidence both pass.' : run.C ? 'Law passes; experimental support does not.' : run.S ? 'Evidence passes; the full law was not identified.' : 'Neither law nor evidence passes.';
      checks.append(node('strong', '', verdict));
    }
    const claims = $('#evidence-claims');
    claims.replaceChildren();
    if (!run.report.conclusions.length) claims.append(node('p', '', 'The report contains no conclusions.'));
    const more = node('details', 'evidence-more-claims');
    more.append(node('summary', '', `${run.report.conclusions.length-3} more findings`));
    run.report.conclusions.forEach((claim, claimIndex) => {
      const article = node('details', 'evidence-claim');
      const summary = node('summary');
      summary.append(node('span', 'evidence-claim-number', String(claimIndex+1).padStart(2, '0')));
      summary.append(textBlock('span', 'evidence-claim-preview', preview(claim.claim)));
      article.append(summary);
      const body = node('div', 'evidence-claim-body');
      body.append(textBlock('p', 'evidence-claim-text', claim.claim));
      const citations = node('div', 'evidence-citations');
      citations.append(node('span', '', 'Cited turns'));
      for (const turn of claim.evidence_turns || []) {
        const button = node('button', '', String(turn));
        button.type = 'button';
        button.dataset.evidenceTurn = String(turn);
        button.setAttribute('aria-label', `Read original turn ${turn}`);
        citations.append(button);
      }
      body.append(citations);
      const details = node('details', 'evidence-reasoning');
      details.append(node('summary', '', 'Conditions and reasoning'));
      if (claim.preconditions) details.append(textBlock('p', '', claim.preconditions));
      if (claim.reasoning) details.append(textBlock('p', '', claim.reasoning));
      if (claim.result) details.append(textBlock('p', '', claim.result));
      body.append(details);
      article.append(body);
      (claimIndex < 3 ? claims : more).append(article);
    });
    if (run.report.conclusions.length > 3) claims.append(more);
    const summary = summaries.get(run.id);
    const matchedSummary = summary?.evaluation_sha256 === run.evaluation_sha256 && summary.scene === group.scene && summary.repeat === run.repeat;
    $('#evidence-summary').textContent = matchedSummary ? summary.summary : 'English summary unavailable. The original judge reason is available below.';
    $('#evidence-reason').replaceChildren(textBlock('span', '', run.reason));
    $('#evidence-truth').textContent = format(run.truth);
    $('#evidence-rule-preview').textContent = preview(format(run.truth));
    $('#evidence-full-report').textContent = JSON.stringify(run.report, null, 2);
    const clip = (window.DISCOVERIES || []).find(item => item.episode_id === run.id);
    $('#evidence-film').hidden = !clip;
    $('#evidence-film').dataset.scene = clip?.id || '';
    $('#evidence-record-download').href = run.archive;
    $('#evidence-record-download').download = `${group.model}-scene-${group.scene}-run-${run.repeat}.zip`;
    $('#evidence-content').querySelectorAll('details').forEach(details => { details.open = false; });
    $('#evidence-content').hidden = false;
  }
  async function loadReports(model, scene) {
    const path = `data/result-evidence/${encodeURIComponent(model.toLowerCase())}/${scene}.json`;
    if (!reports.has(path)) {
      const loading = fetch(path, {signal:AbortSignal.timeout(20000)}).then(response => {
        if (!response.ok) throw new Error('Report unavailable');
        return response.json();
      }).catch(error => { reports.delete(path); throw error; });
      reports.set(path, loading);
    }
    return reports.get(path);
  }
  async function loadSummaries(model) {
    const path = `data/judge-summaries/${encodeURIComponent(model.toLowerCase())}.json`;
    if (!english.has(path)) {
      const loading = fetch(path, {signal:AbortSignal.timeout(20000)}).then(response => {
        if (!response.ok) throw new Error('English summaries unavailable');
        return response.json();
      }).catch(error => { english.delete(path); throw error; });
      english.set(path, loading);
    }
    return english.get(path);
  }
  window.showResultEvidence = async (model, scene) => {
    const entry = window.LONGCHANG.models.find(item => item.name === model);
    const world = window.LONGCHANG.scenes.find(item => item.id === scene);
    if (!entry || !world) return;
    if (!dialog.open) origin = document.activeElement;
    const token = ++version;
    request = {model, scene};
    group = null;
    summaries = new Map();
    dialog.dataset.scene = scene;
    $('#evidence-model').textContent = model;
    $('#evidence-title').textContent = `${scene} · ${world.name}`;
    $('#evidence-content').hidden = true;
    $('#evidence-runs').replaceChildren();
    status('Loading reports…');
    if (!dialog.open) dialog.showModal();
    dialog.scrollTop = 0;
    document.dispatchEvent(new CustomEvent('longchang:evidence-open'));
    try {
      const [result, notes] = await Promise.all([loadReports(model, scene), loadSummaries(model).catch(() => null)]);
      if (token !== version || !dialog.open) return;
      group = result;
      summaries = new Map((notes?.runs || []).map(summary => [summary.episode_id, summary]));
      result.runs.forEach((run, index) => {
        const button = node('button', 'evidence-run');
        button.id = `evidence-run-${run.repeat}`;
        button.type = 'button';
        button.setAttribute('role', 'tab');
        button.setAttribute('aria-controls', 'evidence-content');
        button.dataset.runIndex = String(index);
        button.append(node('strong', '', `Run ${run.repeat}`));
        if (run.control) button.append(node('span', '', run.accepted ? 'Accepted' : 'Rejected'));
        else button.append(...metrics.map(({key}) => resultMark(key, run[key])));
        $('#evidence-runs').append(button);
      });
      status('');
      renderRun(0);
    } catch (_) {
      if (token === version) status('Reports could not load. Please retry.', true);
    }
  };
  $('#evidence-retry').addEventListener('click', () => { if (request) window.showResultEvidence(request.model, request.scene); });
  $('#evidence-runs').addEventListener('click', event => {
    const button = event.target.closest('[data-run-index]');
    if (button) renderRun(Number(button.dataset.runIndex));
  });
  $('#evidence-runs').addEventListener('keydown', event => {
    if (!group || !['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? 2 : (selected+(event.key === 'ArrowRight' ? 1 : 2))%3;
    renderRun(next);
    $('#evidence-runs').querySelectorAll('button')[next].focus();
  });
  $('#evidence-film').addEventListener('click', event => window.showDiscovery?.(event.currentTarget.dataset.scene));

  async function loadRecord(run) {
    if (!records.has(run.id)) {
      const loading = fetch(run.record, {signal:AbortSignal.timeout(20000)}).then(async response => {
        if (!response.ok) throw new Error('Record unavailable');
        if (!window.DecompressionStream) throw new Error('Download the full record to view the original turns in this browser.');
        return new Response(response.body.pipeThrough(new DecompressionStream('gzip'))).json();
      }).catch(error => { records.delete(run.id); throw error; });
      if (records.size >= 3) records.delete(records.keys().next().value);
      records.set(run.id, loading);
    }
    return records.get(run.id);
  }
  function renderTurn(number) {
    const turn = currentRecord.turns.find(item => item.turn === number);
    if (!turn) return;
    $('#evidence-turn-title').textContent = `Original record · Turn ${number}`;
    $('#evidence-turn-select').value = String(number);
    $('#evidence-turn-action').textContent = turn.act || 'No action executed; see the original submission and feedback.';
    $('#evidence-turn-outcome').textContent = format(turn.outcome);
    $('#evidence-turn-after').textContent = format(turn.result_observation);
    $('#evidence-turn-before').textContent = format(turn.observation);
    $('#evidence-turn-note').textContent = turn.note || '';
    $('#evidence-turn-raw').textContent = turn.raw || '';
    $('#evidence-turn-content').hidden = false;
    $('#evidence-turn-status').hidden = true;
  }
  async function openTurn(number) {
    const run = group.runs[selected], token = ++turnVersion;
    turnOrigin = document.activeElement;
    currentRecord = null;
    $('#evidence-turn-title').textContent = `Original record · Turn ${number}`;
    $('#evidence-turn-select').replaceChildren();
    $('#evidence-turn-content').hidden = true;
    $('#evidence-turn-status').textContent = 'Loading original record…';
    $('#evidence-turn-status').hidden = false;
    turnDialog.showModal();
    try {
      const record = await loadRecord(run);
      if (token !== turnVersion || !turnDialog.open) return;
      currentRecord = record;
      record.turns.forEach(turn => { const option = node('option', '', `Turn ${turn.turn}`); option.value = String(turn.turn); $('#evidence-turn-select').append(option); });
      renderTurn(number);
    } catch (error) {
      if (token === turnVersion) $('#evidence-turn-status').textContent = error.message.startsWith('Download') ? error.message : 'The original record could not load. Close this view and select the turn to retry.';
    }
  }
  $('#evidence-claims').addEventListener('click', event => {
    const button = event.target.closest('[data-evidence-turn]');
    if (button) openTurn(Number(button.dataset.evidenceTurn));
  });
  $('#evidence-turn-select').addEventListener('change', event => renderTurn(Number(event.target.value)));
  $('#evidence-close').addEventListener('click', () => dialog.close());
  $('#evidence-turn-close').addEventListener('click', () => turnDialog.close());
  for (const modal of [dialog, turnDialog]) modal.addEventListener('click', event => {
    if (event.target !== modal) return;
    const box = modal.getBoundingClientRect();
    if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) modal.close();
  });
  turnDialog.addEventListener('close', () => { turnVersion++; currentRecord = null; turnOrigin?.focus({preventScroll:true}); });
  dialog.addEventListener('close', () => {
    if (dialog.open) return;
    version++;
    group = null;
    if (turnDialog.open) turnDialog.close();
    const target = origin?.isConnected && origin.getClientRects().length ? origin : $('.result-row[aria-pressed=true]');
    target?.focus({preventScroll:true});
  });
})();
