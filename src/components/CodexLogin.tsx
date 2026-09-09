import {useEffect,useState} from 'react';
type Login={state:string;message?:string;url?:string;code?:string};
type Status={ok:boolean;message:string;login:Login};
async function request(method='GET',body?:object){const response=await fetch('/api/acpx/auth',{method,cache:'no-store',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});const data=await response.json();if(!response.ok)throw new Error(data.detail||'Could not reach the login service.');return data}
export function CodexLogin(){
 const [status,setStatus]=useState<Status|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[refresh,setRefresh]=useState(0);
 useEffect(()=>{let active=true;let timer:ReturnType<typeof setTimeout>;async function check(){try{const next=await request();if(active){setStatus(next);setError('');if(next.login.state==='pending')timer=setTimeout(check,2000)}}catch(e){if(active)setError(e instanceof Error?e.message:String(e))}}void check();return()=>{active=false;clearTimeout(timer)}},[refresh]);
 async function act(method:string,body?:object){setBusy(true);setError('');try{const login=await request(method,body);setStatus(previous=>({ok:previous?.ok||false,message:previous?.message||'',login}))}catch(e){setError(e instanceof Error?e.message:String(e))}finally{setBusy(false);setRefresh(n=>n+1)}}
 const pending=status?.login.state==='pending';
 return <fieldset className="codex-login"><legend>Sign in to OpenAI</legend>
 <p>Use your ChatGPT subscription through Codex. An API key belongs in the LLM API connection instead.</p>
 <p role="status">{status?.message||'Checking this Mac’s Codex login…'}</p>
 <div className="login-actions"><button disabled={busy||pending} onClick={()=>void act('POST',{method:'browser'})}>Sign in with browser</button><button disabled={busy||pending} onClick={()=>void act('POST',{method:'device'})}>Use a device code</button><button disabled={busy} onClick={()=>{setRefresh(n=>n+1)}}>Check login</button></div>
 {pending&&<div className="login-progress" role="status"><p>{status.login.message}</p>{status.login.url&&<a href={status.login.url} target="_blank" rel="noreferrer">Open OpenAI sign-in</a>}{status.login.code&&<p>Enter this code: <strong className="device-code">{status.login.code}</strong></p>}<button disabled={busy} onClick={()=>void act('DELETE')}>Cancel sign-in</button></div>}
 {status?.login.state==='failed'&&<p className="error" role="alert">{status.login.message}</p>}
 {error&&<p className="error" role="alert">{error}</p>}
 <p className="muted">Sign-in uses the Codex login shared with other Codex tools on this Mac. Rogue Collage does not store your OpenAI password or subscription tokens.</p>
 <a href="https://developers.openai.com/codex/auth/#login-on-headless-devices" target="_blank" rel="noreferrer">Device-code setup and troubleshooting</a>
 </fieldset>
}
