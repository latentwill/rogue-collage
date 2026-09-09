import {useEffect,useState} from 'react';
import {createPortal} from 'react-dom';
const help:Record<string,string>={
 'Transparent':'Remove the canvas background. The artboard boundary remains visible; exported PNGs have transparent pixels.',
 'Queue':'Track generation progress and add finished images to the canvas.',
 'History':'Review and undo your canvas edits.',
 'Export PNG':'Export the canvas as a flat PNG at the chosen long-edge size.',
 'Save project bundle':'Download an editable project with all snippets, layers, history, and a flat PNG.',
 'Fit artboard':'Fit the entire canvas in the available workspace.',
 'Remove background':'Queue background removal for the selected object, preserving its original.',
};
export function Tooltips(){
 const [tip,setTip]=useState<{text:string;x:number;y:number}|null>(null);
 useEffect(()=>{let timer:ReturnType<typeof setTimeout>;let owner:HTMLElement|null=null;
  const clear=()=>{clearTimeout(timer);setTip(null);if(owner?.getAttribute('aria-describedby')==='studio-tooltip')owner.removeAttribute('aria-describedby');owner=null};
  const show=(event:Event)=>{const element=(event.target as Element)?.closest<HTMLElement>('button, [data-tooltip], input[title]');if(!element||element===owner)return;clear();const native=element.getAttribute('title');if(native){element.dataset.tooltip=native;element.removeAttribute('title')}const label=element.getAttribute('aria-label')||element.textContent?.trim()||'';const text=element.dataset.tooltip||help[label]||label;if(!text)return;owner=element;timer=setTimeout(()=>{const r=element.getBoundingClientRect();element.setAttribute('aria-describedby','studio-tooltip');setTip({text,x:Math.max(12,Math.min(window.innerWidth-292,r.left)),y:r.bottom+44<window.innerHeight?r.bottom+8:Math.max(8,r.top-62)})},event.type==='focusin'?150:450)};
  const leave=(event:Event)=>{if(owner&&!owner.contains((event as MouseEvent).relatedTarget as Node))clear()};
  document.addEventListener('mouseover',show);document.addEventListener('focusin',show);document.addEventListener('mouseout',leave);document.addEventListener('focusout',clear);document.addEventListener('pointerdown',clear);document.addEventListener('dragstart',clear);window.addEventListener('scroll',clear,true);const key=(e:KeyboardEvent)=>{if(e.key==='Escape')clear()};document.addEventListener('keydown',key);
  return()=>{clear();document.removeEventListener('mouseover',show);document.removeEventListener('focusin',show);document.removeEventListener('mouseout',leave);document.removeEventListener('focusout',clear);document.removeEventListener('pointerdown',clear);document.removeEventListener('dragstart',clear);window.removeEventListener('scroll',clear,true);document.removeEventListener('keydown',key)};
 },[]);
 return tip?createPortal(<div id="studio-tooltip" role="tooltip" className="studio-tooltip" style={{left:tip.x,top:tip.y}}>{tip.text}</div>,document.body):null;
}
