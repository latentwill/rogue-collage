import {useEffect,useState} from 'react';
export function NumberField({value,onCommit,min=-100000,max=100000,label,step=1}:{value:number;onCommit:(value:number)=>void;min?:number;max?:number;label:string;step?:number}){
 const [draft,setDraft]=useState(String(value));
 useEffect(()=>setDraft(String(Math.round(value*100)/100)),[value]);
 const commit=()=>{const n=Number(draft);if(!draft.trim()||!Number.isFinite(n)){setDraft(String(value));return}const next=Math.min(max,Math.max(min,n));setDraft(String(next));if(next!==value)onCommit(next)};
 return <input type="text" inputMode="decimal" role="spinbutton" aria-label={label} aria-valuenow={value} aria-valuemin={min} aria-valuemax={max} title="Type a value, then press Enter or click away. Use ↑/↓ to adjust; Shift changes by 10." value={draft} onFocus={e=>e.currentTarget.select()} onChange={e=>setDraft(e.target.value)} onBlur={commit} onKeyDown={e=>{if(e.key==='Enter'){e.currentTarget.blur()}else if(e.key==='Escape'){setDraft(String(value));e.stopPropagation()}else if(e.key==='ArrowUp'||e.key==='ArrowDown'){e.preventDefault();const parsed=Number(draft);const next=Math.min(max,Math.max(min,(draft.trim()&&Number.isFinite(parsed)?parsed:value)+(e.key==='ArrowUp'?1:-1)*step*(e.shiftKey?10:1)));setDraft(String(next));if(next!==value)onCommit(next)}}}/>;
}
