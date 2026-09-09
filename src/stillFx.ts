/** Original still-image effects. No upstream NTSCRT shader or preset code is used. */
export type FxTarget = 'canvas'|'object'|'selection';
export type StillFx = {width:number;resampler:'smooth'|'pixel';noise:number;bleed:number;tracking:number;wave:number;headSwitch:number;scanlines:number;mask:number;glow:number;curvature:number;seed:number};
export const FX_PRESETS:Record<string,StillFx> = {
  'Clean CRT':{width:960,resampler:'smooth',noise:0.035,bleed:0.08,tracking:0,wave:0,headSwitch:0,scanlines:0.3,mask:0.2,glow:0.12,curvature:0.1,seed:17},
  'Worn tape':{width:640,resampler:'smooth',noise:0.22,bleed:0.48,tracking:0.3,wave:0.15,headSwitch:0.3,scanlines:0.12,mask:0,glow:0.07,curvature:0,seed:17},
  'Signal damage':{width:480,resampler:'pixel',noise:0.45,bleed:0.7,tracking:0.7,wave:0.55,headSwitch:0.65,scanlines:0.32,mask:0.15,glow:0.14,curvature:0.14,seed:17},
  'Pixel monitor':{width:320,resampler:'pixel',noise:0,bleed:0,tracking:0,wave:0,headSwitch:0,scanlines:0.2,mask:0.35,glow:0.04,curvature:0,seed:17},
};
function surface(width:number,height:number){const canvas=document.createElement('canvas');canvas.width=width;canvas.height=height;const context=canvas.getContext('2d',{willReadFrequently:true});if(!context)throw new Error('Your browser could not create an image surface.');return {canvas,context};}
function check(signal?:AbortSignal){signal?.throwIfAborted();}
function random(x:number,y:number,seed:number){let n=Math.imul(x+seed,374761393)^Math.imul(y,668265263);n=Math.imul(n^(n>>>13),1274126177);return ((n^(n>>>16))>>>0)/4294967295;}
/** maxEdge limits preview only; the apply path retains the source's full pixel dimensions. */
export async function renderStillFx(src:string,fx:StillFx,{maxEdge,signal}:{maxEdge?:number;signal?:AbortSignal}={}):Promise<string>{
  check(signal);
  const image=new Image();image.crossOrigin='anonymous';image.src=src;
  try{await image.decode()}catch{throw new Error('Could not read the source image. Import it into Rogue Collage and try again.')}
  check(signal);
  const ratio=maxEdge?Math.min(1,maxEdge/Math.max(image.naturalWidth,image.naturalHeight)):1;
  const width=Math.max(1,Math.round(image.naturalWidth*ratio)),height=Math.max(1,Math.round(image.naturalHeight*ratio));
  const logicalWidth=Math.min(image.naturalWidth,Math.max(64,fx.width)),logicalHeight=Math.max(1,Math.round(image.naturalHeight*logicalWidth/image.naturalWidth));
  const small=surface(logicalWidth,logicalHeight);small.context.imageSmoothingEnabled=fx.resampler==='smooth';small.context.imageSmoothingQuality='high';small.context.drawImage(image,0,0,logicalWidth,logicalHeight);
  const out=surface(width,height);out.context.imageSmoothingEnabled=fx.resampler==='smooth';out.context.imageSmoothingQuality='high';out.context.drawImage(small.canvas,0,0,width,height);
  const source=out.context.getImageData(0,0,width,height),result=out.context.createImageData(width,height),pixels=source.data,dest=result.data;
  const scale=width/logicalWidth;
  for(let y=0;y<height;y++){
    if(y%96===0){check(signal);await new Promise<void>(resolve=>setTimeout(resolve,0))}
    const ly=Math.floor(y/scale),ny=(y/height-.5)*2;
    const band=random(0,Math.floor(ly/9),fx.seed),tracking=band>.87?(band-.87)*fx.tracking*logicalWidth*.23:0;
    const head=y/height>.94?Math.sin(ly*.47+fx.seed)*fx.headSwitch*logicalWidth*.035:0;
    const wave=Math.sin(ny*9+fx.seed)*fx.wave*logicalWidth*.009;
    for(let x=0;x<width;x++){
      const nx=(x/width-.5)*2,lx=Math.floor(x/scale),dst=(y*width+x)*4;
      const warpedX=nx*(1+fx.curvature*ny*ny*.2),warpedY=ny*(1+fx.curvature*nx*nx*.2);
      const sx=Math.round((warpedX/2+.5)*width+(tracking+head+wave)*scale),sy=Math.round((warpedY/2+.5)*height);
      if(sx<0||sx>=width||sy<0||sy>=height)continue;
      const at=(sy*width+sx)*4,bleed=Math.round(fx.bleed*5*scale);
      const red=(sy*width+Math.max(0,sx-bleed))*4,blue=(sy*width+Math.min(width-1,sx+bleed))*4;
      const noise=(random(lx,ly,fx.seed)-.5)*fx.noise*110;
      const scan=1-fx.scanlines*(ly%3===2?.7:0);
      for(let c=0;c<3;c++){
        const sample=c===0?red:c===2?blue:at;
        const color=pixels[sample+3]?pixels[sample+c]:pixels[at+c];
        const phosphor=1-(lx%3===c?0:fx.mask*.38);
        dest[dst+c]=(color+noise)*scan*phosphor;
      }
      dest[dst+3]=pixels[at+3];
    }
  }
  check(signal);out.context.putImageData(result,0,0);
  if(fx.glow>0){const glow=surface(width,height);glow.context.filter=`blur(${Math.max(.5,2.5*scale)}px)`;glow.context.drawImage(out.canvas,0,0);out.context.globalCompositeOperation='source-atop';out.context.globalAlpha=fx.glow*.6;out.context.drawImage(glow.canvas,0,0);out.context.globalAlpha=1;out.context.globalCompositeOperation='source-over';glow.canvas.width=1;glow.canvas.height=1;}
  check(signal);const png=out.canvas.toDataURL('image/png');small.canvas.width=1;small.canvas.height=1;out.canvas.width=1;out.canvas.height=1;return png;
}
