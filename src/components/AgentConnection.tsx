import {useState} from 'react';
import {AgentModelSelect} from './AgentModelSelect';
import {CodexLogin} from './CodexLogin';
import type {Settings} from '../types';

const loginSteps = {
  codex: 'Sign in through Codex CLI on this Mac before sending a studio-agent prompt.',
  claude: 'Sign in through Claude Code on this Mac before sending a studio-agent prompt.',
  gemini: 'Install Gemini CLI and sign in there before sending a studio-agent prompt.',
};

export function AgentConnection({value,onChange,onSave}:{value:Settings;onChange:(value:Settings)=>void;onSave:(value:Settings)=>Promise<void>}) {
  const [checking,setChecking]=useState(false);
  const [result,setResult]=useState<{ok:boolean;message:string}|null>(null);
  const connection=value.llm.connector||'api';
  const local=/^https?:\/\/(localhost|127\.0\.0\.1|\[::1\])(?=[:/]|$)/i.test(value.llm.endpoint||'');
  const [models,setModels]=useState<string[]>([]);
  async function discover(){setChecking(true);setResult(null);try{await onSave(value);const response=await fetch('/api/agent/models');const data=await response.json();if(!response.ok)throw new Error(data.detail||'Model discovery failed');setModels(data.models||[]);setResult({ok:true,message:data.models?.length?`Found ${data.models.length} models. Choose a model that supports tool calling.`:'No models loaded. Load a model in your local server, then refresh.'})}catch(e){setResult({ok:false,message:e instanceof Error?e.message:'Model discovery failed'})}finally{setChecking(false)}}
  const harness=value.llm.acpx_agent||'codex';
  const update=(patch:Partial<Settings['llm']>)=>{setResult(null);onChange({...value,llm:{...value.llm,...patch}})};
  async function check(){
    setChecking(true);setResult(null);
    try {
      await onSave(value);
      const response=await fetch('/api/settings/test',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({provider:'llm'})});
      const data=await response.json();
      setResult({ok:response.ok&&data.ok===true,message:data.message||data.detail||'Connection check failed.'});
    }catch(error){setResult({ok:false,message:error instanceof Error?error.message:String(error)})}
    finally{setChecking(false)}
  }
  return <div className="agent-connection">
    <label>Agent connection<select value={connection==='acpx'?'acpx':local?'local':'api'} onChange={e=>{setModels([]);if(e.target.value==='acpx')update({connector:'acpx'});else update({connector:'api',endpoint:e.target.value==='local'?'http://localhost:11434/v1':'',model:'',api_key:'',clear_api_key:true})}}>
      <option value="local">Local LLM · Ollama / LM Studio</option><option value="api">OpenAI-compatible API</option>
      <option value="acpx">ACPX · CLI subscription</option>
    </select></label>
    {connection==='acpx'?<>
      <p className="muted">Use an existing CLI login for the studio agent. Account access and usage limits are managed by the selected provider.</p>
      <label>CLI agent<select value={harness} onChange={e=>update({acpx_agent:e.target.value as 'codex'|'claude'|'gemini'})}>
        <option value="codex">Codex</option><option value="claude">Claude Code</option><option value="gemini">Gemini CLI</option>
      </select></label>
      {harness==='codex'?<AgentModelSelect value={value.llm.acpx_model||''} onChange={acpx_model=>update({acpx_model})}/>:<label>Model override<input value={value.llm.acpx_model||''} onChange={e=>update({acpx_model:e.target.value})}/></label>}
      {harness==='codex'?<CodexLogin/>:<p>{loginSteps[harness]}</p>}
      <p className="muted">No subscription token is copied into Rogue Collage. This connector sends project metadata and chat to the CLI; image-provider settings remain separate. Canvas previews use the LLM API connection.</p>
      <a href="https://github.com/openclaw/acpx" target="_blank" rel="noreferrer">ACPX setup reference</a>
    </>:<>
      <p className="muted">Connect an OpenAI-compatible chat API to inspect the composition, edit layers, and request generation.</p>
      {local&&<><label>Local server<select value={value.llm.endpoint?.includes(':11434')?'ollama':value.llm.endpoint?.includes(':1234')?'lmstudio':'custom'} onChange={e=>{setModels([]);update({endpoint:e.target.value==='ollama'?'http://localhost:11434/v1':e.target.value==='lmstudio'?'http://localhost:1234/v1':'http://localhost:8080/v1',model:'',api_key:'',clear_api_key:true})}}><option value="ollama">Ollama</option><option value="lmstudio">LM Studio</option><option value="custom">Other local server</option></select></label><p className="muted">Start your local server and load a tool-capable model first. Rogue Collage connects to it; it does not install an LLM.</p></>}
      <label>LLM base URL<input value={value.llm.endpoint||''} onChange={e=>update({endpoint:e.target.value})}/></label>
      <label>Agent model ID<input list="available-agent-models" value={value.llm.model||''} placeholder="Model ID from your server" onChange={e=>update({model:e.target.value})}/><datalist id="available-agent-models">{models.map(id=><option key={id} value={id}/>)}</datalist></label><button disabled={checking} onClick={()=>void discover()}>Save & discover models</button><p className="muted">Uses this exact model with the chat-completions API and tool calling. No automatic model fallback.</p>
      <label>API key<input type="password" autoComplete="off" value={value.llm.api_key||''} placeholder={value.llm.has_api_key?'Saved key · leave blank to keep':'Optional for local models'} onChange={e=>update({api_key:e.target.value,clear_api_key:false})}/></label>
      <label className="check-label"><input type="checkbox" checked={value.llm.clear_api_key||false} onChange={e=>update({clear_api_key:e.target.checked})}/>Clear saved LLM key</label>
    </>}
    <button disabled={checking} onClick={()=>void check()}>{checking?'Checking…':connection==='acpx'?'Save & check connection':'Save & test LLM'}</button>
    {connection==='acpx'&&<p className="muted">This checks installation and, for Codex, local ChatGPT login. It does not send a prompt; model access and usage limits are checked on your first message.</p>}
    {result&&<p role={result.ok?'status':'alert'} className={result.ok?'':'error'}>{result.message}</p>}
  </div>;
}
