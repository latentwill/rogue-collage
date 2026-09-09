import type {Layer,TextContent} from './types';
export const textFonts=[['Arial, Helvetica, sans-serif','Sans serif'],['Georgia, serif','Serif'],['Courier New, monospace','Monospace']] as const;
const defaults:TextContent={content:'Your text',fontFamily:textFonts[0][0],fontSize:96,bold:true,italic:false,align:'left',fill:'#ffffff',outlineColor:'#10191d',outlineWidth:2,glowColor:'#00e8be',glowRadius:0,shadowColor:'#000000',shadowBlur:0,shadowX:0,shadowY:0,boxWidth:900,boxHeight:160};
function font(t:TextContent){return `${t.italic?'italic ':''}${t.bold?'bold ':''}${t.fontSize}px ${t.fontFamily}`}
function padding(t:TextContent){return Math.ceil(Math.max(8,t.outlineWidth*2,t.glowRadius*3,t.shadowBlur*3+Math.abs(t.shadowX),t.shadowBlur*3+Math.abs(t.shadowY)))}
function textLines(ctx:CanvasRenderingContext2D,t:TextContent){
 ctx.font=font(t);const available=Math.max(t.fontSize,t.boxWidth-padding(t)*2),lines:string[]=[];
 for(const paragraph of t.content.split('\n')){let line='';for(const char of Array.from(paragraph)){const next=line+char;if(line&&ctx.measureText(next).width>available){lines.push(line);line=char}else line=next}lines.push(line)}return lines;
}
export function updateTextLayer(layer:Layer,patch:Partial<TextContent>):Partial<Layer>{
 const old=layer.text||defaults,t={...old,...patch};const ctx=document.createElement('canvas').getContext('2d')!;
 t.boxWidth=Math.max(t.boxWidth,padding(t)*2+t.fontSize*2);t.boxHeight=Math.ceil(textLines(ctx,t).length*t.fontSize*1.25+padding(t)*2);
 return {text:t,width:layer.width*t.boxWidth/old.boxWidth,height:layer.height*t.boxHeight/old.boxHeight};
}
export function createTextLayer(width:number,height:number):Layer{
 const t={...defaults,fontSize:Math.max(24,Math.min(192,Math.round(width/12))),boxWidth:Math.max(240,Math.min(1200,width*.65))};
 let layer:Layer={id:crypto.randomUUID(),name:'Text',kind:'text',text:t,x:0,y:0,width:t.boxWidth,height:t.boxHeight,rotation:0,opacity:1,visible:true};
 layer={...layer,...updateTextLayer(layer,{})};return {...layer,x:(width-layer.width)/2,y:(height-layer.height)/2};
}
/** The same transparent bitmap feeds the editor, image operations, and final export. */
export function paintText(ctx:CanvasRenderingContext2D,t:TextContent,width:number,height:number){
 ctx.save();ctx.scale(width/t.boxWidth,height/t.boxHeight);ctx.font=font(t);ctx.textBaseline='top';ctx.textAlign=t.align;ctx.lineJoin='round';
 const matrix=ctx.getTransform(),sx=Math.hypot(matrix.a,matrix.b),sy=Math.hypot(matrix.c,matrix.d),blurScale=(sx+sy)/2;
 const inset=padding(t),x=t.align==='center'?t.boxWidth/2:t.align==='right'?t.boxWidth-inset:inset,lines=textLines(ctx,t);
 const glyphs=(fill:string)=>{ctx.fillStyle=fill;lines.forEach((line,i)=>ctx.fillText(line,x,inset+i*t.fontSize*1.25))};
 // Isolate the shadow to prevent it being applied again to the outline and glow passes.
 if(t.shadowBlur||t.shadowX||t.shadowY){ctx.save();ctx.shadowColor=t.shadowColor;ctx.shadowBlur=t.shadowBlur*blurScale;ctx.shadowOffsetX=t.shadowX*sx;ctx.shadowOffsetY=t.shadowY*sy;glyphs(t.fill);ctx.restore()}
 if(t.glowRadius){ctx.save();ctx.shadowColor=t.glowColor;ctx.shadowBlur=t.glowRadius*blurScale;glyphs(t.glowColor);glyphs(t.glowColor);ctx.restore()}
 if(t.outlineWidth){ctx.strokeStyle=t.outlineColor;ctx.lineWidth=t.outlineWidth*2;lines.forEach((line,i)=>ctx.strokeText(line,x,inset+i*t.fontSize*1.25))}
 glyphs(t.fill);ctx.restore();
}
export function validateText(value:unknown):asserts value is TextContent{
 const t=value as TextContent;if(!t||typeof t.content!=='string'||t.content.length>100000||!textFonts.some(([family])=>family===t.fontFamily)||!['left','center','right'].includes(t.align)||typeof t.bold!=='boolean'||typeof t.italic!=='boolean')throw new Error('Invalid text layer');
 for(const key of ['fill','outlineColor','glowColor','shadowColor'] as const)if(!/^#[\da-f]{6}$/i.test(t[key]))throw new Error('Invalid text color');
 for(const key of ['fontSize','outlineWidth','glowRadius','shadowBlur','shadowX','shadowY','boxWidth','boxHeight'] as const)if(!Number.isFinite(t[key])||Math.abs(t[key])>32768)throw new Error('Invalid text dimensions');
 if(t.fontSize<1||t.boxWidth<1||t.boxHeight<1||t.outlineWidth<0||t.glowRadius<0||t.shadowBlur<0)throw new Error('Invalid text dimensions');
}
