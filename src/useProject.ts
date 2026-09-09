import {debugLog} from './debugLog';
import { useEffect, useRef, useState } from 'react';
import type { Project, HistoryEntry, Layer } from './types';
import { migrateGeneratedAssetNames } from './assetNames';
const blank = (): Project => ({id:crypto.randomUUID(),name:'Untitled collage',width:1536,height:1024,background:'#f2eee5',layers:[],revision:0});
// The asset library is durable project material, independent of undoable canvas edits.
function mergeSnippets(...groups:(Layer[]|undefined)[]):Layer[] {const items:Layer[]=[],ids=new Set<string>(),sources=new Set<string>();for(const group of groups)for(const layer of group||[]){if(ids.has(layer.id)||(layer.src&&sources.has(layer.src)))continue;items.push(layer);ids.add(layer.id);if(layer.src)sources.add(layer.src)}return items}
function libraryProject(project:Project,current?:Project,...groups:(Layer[]|undefined)[]):Project {
 const same=current?.id===project.id?current:undefined;
 const deletedSnippetIds=[...new Set([...(project.deletedSnippetIds||[]),...(same?.deletedSnippetIds||[])])];
 const deletedSnippetSources=[...new Set([...(project.deletedSnippetSources||[]),...(same?.deletedSnippetSources||[])])];
 const ids=new Set(deletedSnippetIds),sources=new Set(deletedSnippetSources);
 return migrateGeneratedAssetNames({...project,deletedSnippetIds,deletedSnippetSources,snippets:mergeSnippets(...groups).filter(l=>!ids.has(l.id)&&(!l.src||!sources.has(l.src)))});
}
function restoreLibrary(project:Project,history:HistoryEntry[]=[]):Project {return libraryProject(project,undefined,project.snippets,...history.filter(e=>e.project.id===project.id).map(e=>e.project.snippets))}
interface State { project:Project; past:HistoryEntry[]; future:HistoryEntry[] }
export function useProject() {
 const [state,setState]=useState<State>(()=>({project:blank(),past:[],future:[]}));
 const current=useRef(state); const [loading,setLoading]=useState(true); const [persistenceError,setError]=useState<string|null>(null); const db=useRef<IDBDatabase|null>(null);
 const update=(next:State)=>{current.current=next;setState(next)};
 useEffect(()=>{let disposed=false; const request=indexedDB.open('roguelike-collage',1); request.onupgradeneeded=()=>{if(!request.result.objectStoreNames.contains('projects'))request.result.createObjectStore('projects')};request.onerror=()=>{if(!disposed){setError('Local saving unavailable. Export a project bundle to save your work.');setLoading(false)}};request.onsuccess=()=>{if(disposed){request.result.close();return}db.current=request.result;const read=request.result.transaction('projects').objectStore('projects').get('current');read.onsuccess=()=>{if(disposed)return;if(read.result?.project)update({project:restoreLibrary(read.result.project,[...(read.result.past||[]),...(read.result.future||[])]),past:read.result.past||[],future:read.result.future||[]});setLoading(false)};read.onerror=()=>{if(!disposed)setLoading(false)}};return()=>{disposed=true;db.current?.close();db.current=null}},[]);
 useEffect(()=>{if(loading||!db.current)return;try{const tx=db.current.transaction('projects','readwrite');tx.objectStore('projects').put(state,'current');tx.oncomplete=()=>setError(null);tx.onerror=()=>setError('Could not save locally. Export a project bundle to keep your work.')}catch{setError('Local saving unavailable. Export your project to keep your work.')}},[state,loading]);
 function setProject(next:Project|((p:Project)=>Project),label='Edit') {debugLog('project.edit',{action:label});const s=current.current;const value=typeof next==='function'?next(s.project):next;update({project:{...libraryProject(value,s.project,value.snippets,value.id===s.project.id?s.project.snippets:undefined),revision:s.project.revision+1},past:[...s.past,{label,project:s.project,at:new Date().toISOString()}].slice(-60),future:[]})}
 function undo(){debugLog('project.undo');const s=current.current,entry=s.past.at(-1);if(!entry)return;update({project:{...libraryProject(entry.project,s.project,s.project.snippets,entry.project.snippets),revision:s.project.revision+1},past:s.past.slice(0,-1),future:[{label:entry.label,project:s.project,at:new Date().toISOString()},...s.future]})}
 function redo(){debugLog('project.redo');const s=current.current,entry=s.future[0];if(!entry)return;update({project:{...libraryProject(entry.project,s.project,s.project.snippets,entry.project.snippets),revision:s.project.revision+1},past:[...s.past,{label:entry.label,project:s.project,at:new Date().toISOString()}].slice(-60),future:s.future.slice(1)})}
 function reset(project:Project,history:HistoryEntry[]=[]) {debugLog('project.reset');update({project:{...restoreLibrary(project,history),revision:Math.max(project.revision||0,current.current.project.revision+1)},past:history.slice(-60),future:[]})}
 function registerSnippets(layers:Layer[],projectId?:string){const s=current.current;if(projectId&&projectId!==s.project.id)return;const project=libraryProject(s.project,undefined,s.project.snippets,layers);if(project.snippets?.length===(s.project.snippets?.length||0))return;update({...s,project})}
 // Library deletion is durable and deliberately independent of canvas undo.
 function deleteSnippets(ids:string[]){const s=current.current;const selected=new Set(ids);const removed=(s.project.snippets||[]).filter(l=>selected.has(l.id));if(!removed.length)return;const project=libraryProject({...s.project,deletedSnippetIds:[...(s.project.deletedSnippetIds||[]),...removed.map(l=>l.id)],deletedSnippetSources:[...(s.project.deletedSnippetSources||[]),...removed.flatMap(l=>l.src?[l.src]:[])]},undefined,s.project.snippets);update({...s,project})}
 return {project:state.project,setProject,registerSnippets,deleteSnippets,undo,redo,canUndo:!!state.past.length,canRedo:!!state.future.length,history:state.past,reset,loading,persistenceError};
}
