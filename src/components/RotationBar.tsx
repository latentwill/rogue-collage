import {useRef,useState} from 'react';
import {RotateCcw,RotateCw} from 'lucide-react';
import {NumberField} from './NumberField';
import type {Layer} from '../types';
import './rotation.css';

export function rotateAroundCenter(layer:Layer,rotation:number):Layer {
 const before=layer.rotation*Math.PI/180,after=rotation*Math.PI/180;
 const cx=layer.x+Math.cos(before)*layer.width/2-Math.sin(before)*layer.height/2;
 const cy=layer.y+Math.sin(before)*layer.width/2+Math.cos(before)*layer.height/2;
 return {...layer,rotation,x:cx-Math.cos(after)*layer.width/2+Math.sin(after)*layer.height/2,y:cy-Math.sin(after)*layer.width/2-Math.cos(after)*layer.height/2};
}
const angle=(value:number)=>((value+180)%360+360)%360-180;

export function RotationBar({layer,scale,position,viewport,onPreview,onCommit}:{layer:Layer;scale:number;position:{x:number;y:number};viewport:{width:number;height:number};onPreview:(rotation:number|null)=>void;onCommit:(rotation:number)=>void}){
 const [draft,setDraft]=useState<number|null>(null),pending=useRef<number|null>(null);
 const rotation=draft??angle(layer.rotation),r=layer.rotation*Math.PI/180;
 const corners=[[0,0],[layer.width,0],[0,layer.height],[layer.width,layer.height]].map(([x,y])=>({x:position.x+(layer.x+x*Math.cos(r)-y*Math.sin(r))*scale,y:position.y+(layer.y+x*Math.sin(r)+y*Math.cos(r))*scale}));
 const width=Math.min(340,Math.max(0,viewport.width-16));
 const left=Math.max(8,Math.min(viewport.width-width-8,(Math.min(...corners.map(p=>p.x))+Math.max(...corners.map(p=>p.x)))/2-width/2));
 const bottom=Math.max(...corners.map(p=>p.y));
 const top=Math.max(8,Math.min(viewport.height-48,bottom+14));
 const preview=(value:number)=>{pending.current=value;setDraft(value);onPreview(value)};
 const finish=()=>{const value=pending.current;pending.current=null;setDraft(null);if(value!==null)onCommit(value);onPreview(null)};
 const cancel=()=>{pending.current=null;setDraft(null);onPreview(null)};
 return <div className="rotation-bar" role="group" aria-label={`Rotate ${layer.name}`} style={{left,top,width}} onKeyDown={e=>e.stopPropagation()}>
  <button type="button" title="Rotate counterclockwise 90°" aria-label="Rotate counterclockwise 90 degrees" onClick={()=>onCommit(angle(layer.rotation-90))}><RotateCcw/></button>
  <input type="range" min={-180} max={180} step={1} value={rotation} aria-label="Object rotation" title="Drag to rotate around the object's center" onChange={e=>preview(Number(e.target.value))} onPointerDown={e=>e.currentTarget.setPointerCapture(e.pointerId)} onPointerUp={finish} onPointerCancel={cancel} onBlur={finish} onKeyUp={e=>{if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End','PageUp','PageDown'].includes(e.key))finish()}} onKeyDown={e=>{if(e.key==='Escape'){e.preventDefault();cancel()}}}/>
  <span className="rotation-angle"><NumberField label="Object rotation in degrees" value={rotation} min={-36000} max={36000} onCommit={value=>onCommit(angle(value))}/><span aria-hidden="true">°</span></span>
  <button type="button" title="Rotate clockwise 90°" aria-label="Rotate clockwise 90 degrees" onClick={()=>onCommit(angle(layer.rotation+90))}><RotateCw/></button>
  <button type="button" className="rotation-reset" title="Reset rotation to 0°" disabled={rotation===0} onClick={()=>onCommit(0)}>Reset</button>
 </div>;
}
