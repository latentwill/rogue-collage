import { useEffect, useState } from 'react';
import { Save } from 'lucide-react';

export function MemoryEditor() {
  const [content, setContent] = useState('');
  const [saved, setSaved] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [feedback, setFeedback] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    void fetch('/api/agent/memory', { signal: controller.signal })
      .then(async response => {
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || 'Could not load agent memory.');
        setContent(result.content);
        setSaved(result.content);
      })
      .catch(reason => {
        if (!controller.signal.aborted) setError(String(reason));
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, []);

  async function saveMemory() {
    setSaving(true);
    setError('');
    setFeedback('');
    try {
      const response = await fetch('/api/agent/memory', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'Could not save agent memory.');
      setContent(result.content);
      setSaved(result.content);
      setFeedback('Memory saved. The agent will use it on the next request.');
    } catch (reason) { setError(String(reason)); }
    finally { setSaving(false); }
  }

  return <fieldset>
    <legend>Agent memory</legend>
    <p className="muted">Your local memory.md carries artistic preferences, useful techniques, and ongoing context between conversations. Save memory separately from connection settings.</p>
    <label>memory.md<textarea className="code-input" rows={12} value={content} disabled={loading || saving} placeholder={loading ? 'Loading memory…' : 'Write what the agent should remember…'} onChange={event => { setContent(event.target.value); setFeedback(''); }}/></label>
    <button disabled={loading || saving || content === saved} onClick={() => void saveMemory()}><Save size={15}/>{saving ? 'Saving memory…' : 'Save memory'}</button>
    {content !== saved && <p className="muted">Unsaved memory changes</p>}
    {feedback && <p role="status" className="connection-feedback">{feedback}</p>}
    {error && <p role="alert" className="error">{error}</p>}
  </fieldset>;
}
