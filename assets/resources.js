/* Share downloads and parsed scene data without coupling callers' cancellation. */
(() => {
  'use strict';
  const entries = new Map(), limit = 4;
  const aborted = signal => signal.reason || new DOMException('Aborted', 'AbortError');
  function trim() {
    const ready = [...entries].filter(([, entry]) => entry.complete);
    while (ready.length > limit) entries.delete(ready.shift()[0]);
  }
  function json(path, {signal} = {}) {
    if (signal?.aborted) return Promise.reject(aborted(signal));
    const url = new URL(path, document.baseURI).href;
    let entry = entries.get(url);
    if (!entry) {
      const controller = new AbortController();
      entry = {controller, users:0, complete:false};
      entries.set(url, entry);
      const timer = setTimeout(() => controller.abort(new DOMException('Timed out', 'TimeoutError')), 20000);
      entry.promise = fetch(url, {signal:controller.signal}).then(response => {
        if (!response.ok) throw new Error(`Resource unavailable (${response.status})`);
        return response.json();
      }).then(data => {
        entry.complete = true;
        trim();
        return data;
      }).catch(error => {
        if (entries.get(url) === entry) entries.delete(url);
        throw error;
      }).finally(() => clearTimeout(timer));
    } else {
      entries.delete(url); entries.set(url, entry);
    }
    return new Promise((resolve, reject) => {
      let done = false;
      entry.users++;
      const finish = (callback, value) => {
        if (done) return;
        done = true;
        signal?.removeEventListener('abort', cancel);
        entry.users--;
        if (!entry.complete && !entry.users) {
          if (entries.get(url) === entry) entries.delete(url);
          entry.controller.abort();
        }
        callback(value);
      };
      const cancel = () => finish(reject, aborted(signal));
      signal?.addEventListener('abort', cancel, {once:true});
      entry.promise.then(value => finish(resolve, value), error => finish(reject, error));
    });
  }
  window.LongChangResources = Object.freeze({json});
})();
