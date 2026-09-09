import {generatedAssetName} from './assetNames';
import type {Job,Layer,Project} from './types';
import {readImage,layerBitmap} from './editorUtils';

const finite=(value:unknown,fallback:number)=>typeof value==='number'&&Number.isFinite(value)?value:fallback;
const positive=(value:unknown,fallback:number)=>{const number=finite(value,fallback);return number>0?number:fallback};
const text=(value:unknown)=>typeof value==='string'&&value.length>0?value:undefined;

/** Constrain a returned crop to the original selection, even if its provider ignored the mask. */
async function clipResult(image:HTMLImageElement,job:Job):Promise<string|undefined>{
 const target=job.target||{};
 if(target.type!=='selection')return;
 const points=Array.isArray(target.points)&&target.points.length>=6&&target.points.length%2===0&&target.points.every(v=>typeof v==='number'&&Number.isFinite(v))?target.points as number[]:undefined;
 const maskSource=text(target.mask)||text(job.params?.mask);
 if(!points&&!maskSource)return;
 const output=document.createElement('canvas');output.width=image.naturalWidth;output.height=image.naturalHeight;
 const ctx=output.getContext('2d')!;ctx.drawImage(image,0,0);
 const mask=document.createElement('canvas');mask.width=output.width;mask.height=output.height;
 const m=mask.getContext('2d',{willReadFrequently:true})!;
 if(maskSource){
  const source=await readImage(maskSource);m.drawImage(source,0,0,mask.width,mask.height);
  // Our inference masks are white=edit, black=preserve. Convert luminance to alpha.
  const pixels=m.getImageData(0,0,mask.width,mask.height);
  for(let i=0;i<pixels.data.length;i+=4){pixels.data[i+3]=Math.round((pixels.data[i]*.2126+pixels.data[i+1]*.7152+pixels.data[i+2]*.0722)*pixels.data[i+3]/255);pixels.data[i]=pixels.data[i+1]=pixels.data[i+2]=255}
  m.putImageData(pixels,0,0);
 }else if(points){
  const x=finite(target.x,0),y=finite(target.y,0),width=positive(target.width,output.width),height=positive(target.height,output.height);
  m.scale(output.width/width,output.height/height);m.translate(-x,-y);m.beginPath();m.moveTo(points[0],points[1]);
  for(let i=2;i<points.length;i+=2)m.lineTo(points[i],points[i+1]);
  m.closePath();m.fillStyle='white';m.fill();
 }
 ctx.globalCompositeOperation='destination-in';ctx.drawImage(mask,0,0);
 return output.toDataURL('image/png');
}

/** Build a layer from saved job placement; callers choose whether to add or replace its source. */
export async function buildResultLayer(src:string,job:Job,project:Project):Promise<Layer>{
 const image=await readImage(src),target=job.target||{};
 const sameProject=!target.projectId||target.projectId===project.id;
 const isObject=target.type==='object';
 const source=isObject&&sameProject?project.layers.find(layer=>layer.id===target.layerId):undefined;
 const ratio=image.naturalHeight/image.naturalWidth;
 const nativeSize=target.nativeSize===true||(job.operation==='generate-piece'&&target.type!=='selection'&&target.type!=='object');
 const defaultWidth=image.naturalWidth;
 const width=nativeSize?image.naturalWidth:sameProject?positive(target.width,source?.width||defaultWidth):defaultWidth;
 const height=nativeSize?image.naturalHeight:sameProject?positive(target.height,source?.height||width*ratio):width*ratio;
 const masked=await clipResult(image,job);
 const originalSrc=text(target.originalSrc)||source?.originalSrc||source?.src||(source?.kind==='drawing'?(await layerBitmap({...source,maskStrokes:[]})).toDataURL('image/png'):src);
 return {
  id:crypto.randomUUID(),name:generatedAssetName(job),kind:'image',src:masked||src,
  originalSrc,
  x:nativeSize?(project.width-width)/2:sameProject?finite(target.x,source?.x||0):0,y:nativeSize?(project.height-height)/2:sameProject?finite(target.y,source?.y||0):0,width,height,
  rotation:sameProject?finite(target.rotation,source?.rotation||0):0,
  flipX:sameProject?(typeof target.flipX==='boolean'?target.flipX:source?.flipX):false,
  flipY:sameProject?(typeof target.flipY==='boolean'?target.flipY:source?.flipY):false,
  opacity:isObject?Math.max(0,Math.min(1,finite(target.opacity,source?.opacity??1))):1,
  blendMode:isObject?(text(target.blendMode) as GlobalCompositeOperation|undefined)||source?.blendMode:'source-over',
  visible:true,
  // Input pixels already contained any painted mask and drawing; never apply them twice.
  maskStrokes:[],strokes:[],
 };
}
