import { useEffect, useState } from 'react';
import { Maximize, Minimize } from 'lucide-react';
import './fullscreen.css';

export function FullscreenButton() {
  const [fullscreen, setFullscreen] = useState(!!document.fullscreenElement);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    const update = () => { setFullscreen(!!document.fullscreenElement); setError(''); };
    document.addEventListener('fullscreenchange', update);
    return () => document.removeEventListener('fullscreenchange', update);
  }, []);
  async function toggle() {
    setError('');
    if (!document.fullscreenEnabled || !document.documentElement.requestFullscreen) {
      setError('This browser does not support app fullscreen. Open Rogue Collage in Chrome, Firefox, or Safari.');
      return;
    }
    setBusy(true);
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await document.documentElement.requestFullscreen();
    } catch {
      setError('Fullscreen was blocked by the browser. Try opening Rogue Collage in a separate browser window.');
    } finally { setBusy(false); }
  }
  return <span className="fullscreen-control">
    <button disabled={busy} aria-label={fullscreen ? 'Exit fullscreen' : 'Enter fullscreen'} title={fullscreen ? 'Exit fullscreen (Esc)' : 'Enter fullscreen'} aria-pressed={fullscreen} onClick={() => void toggle()}>{fullscreen ? <Minimize size={17}/> : <Maximize size={17}/>}</button>
    {error && <span className="fullscreen-error" role="alert">{error}</span>}
  </span>;
}
