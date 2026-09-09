type Detail = string | number | boolean | null | undefined;
let enabled = false;
let installed = false;
let timer: ReturnType<typeof setTimeout> | undefined;
let pending: {event: string; details: Record<string, Detail>}[] = [];
const fields = new Set(['method','path','status','request_id','duration_ms','job_id','provider','operation','action_count','warning_count','error_type','count','layer_id','snippet_id','selected_count','target','action','tag','input_type','enabled','command','success']);

export function debugLog(event: string, details: Record<string, Detail> = {}) {
  if (!enabled) return;
  const safe: Record<string, Detail> = {};
  for (const [key, value] of Object.entries(details)) {
    if (fields.has(key) && (typeof value !== 'string' || /^[a-zA-Z0-9_./:{} -]{0,180}$/.test(value) && !value.includes('://'))) safe[key] = value;
  }
  pending.push({event: /^[a-zA-Z0-9_.-]{1,80}$/.test(event) ? event : 'invalid_event', details: safe});
  if (pending.length > 100) pending.shift();
  if (!timer) timer = setTimeout(flush, 500);
}

function flush() {
  timer = undefined;
  const events = pending.splice(0);
  if (!enabled || !events.length) return;
  void fetch('/api/debug/events', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({events}), keepalive:true}).catch(() => {});
}

function interaction(event: Event) {
  const node = event.target instanceof Element ? event.target.closest('button,input,select,textarea,[role="button"],[data-debug-action]') : null;
  if (!node) return;
  // Never read textContent, labels, input values, asset names or prompts.
  debugLog(`ui.${event.type}`, {tag:node.tagName.toLowerCase(), action:node.getAttribute('data-debug-action') || undefined, input_type:node instanceof HTMLInputElement ? node.type : undefined});
}

export function setDebugLogging(value: boolean) {
  enabled = value;
  if (!value) { pending = []; if(timer)clearTimeout(timer); timer=undefined; }
  if (installed) return;
  installed = true;
  document.addEventListener('click', interaction, true);
  document.addEventListener('change', interaction, true);
  document.addEventListener('drop', () => debugLog('ui.drop'), true);
  window.addEventListener('error', () => debugLog('browser.error', {error_type:'ErrorEvent'}));
  window.addEventListener('unhandledrejection', () => debugLog('browser.error', {error_type:'UnhandledRejection'}));
  window.addEventListener('pagehide', flush);
}
