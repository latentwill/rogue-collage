import type {Layer,Stroke} from '../types';

export function layerCorners(layer:Layer){
 const r=layer.rotation*Math.PI/180,c=Math.cos(r),s=Math.sin(r);
 return [[0,0],[layer.width,0],[layer.width,layer.height],[0,layer.height]].map(([x,y])=>({x:layer.x+x*c-y*s,y:layer.y+x*s+y*c}));
}

export function rotateLayers(layers:Layer[],center:{x:number;y:number},degrees:number):Layer[]{
 const r=degrees*Math.PI/180,c=Math.cos(r),s=Math.sin(r);
 return layers.map(layer=>{const x=layer.x-center.x,y=layer.y-center.y;return {...layer,x:center.x+x*c-y*s,y:center.y+x*s+y*c,rotation:layer.rotation+degrees}});
}

interface TransformNode {width():number;height():number;scaleX():number;scaleX(value:number):unknown;scaleY():number;scaleY(value:number):unknown;rotation():number;x():number;y():number}
export function readTransformedLayer(layer:Layer,node:TransformNode):Layer {
 const width=Math.max(2,Math.abs(node.width()*node.scaleX())),height=Math.max(2,Math.abs(node.height()*node.scaleY()));
 const rotation=node.rotation(),r=rotation*Math.PI/180,flipX=node.scaleX()<0,flipY=node.scaleY()<0;
 node.scaleX(flipX?-1:1);node.scaleY(flipY?-1:1);
 const resize=(strokes?:Stroke[])=>strokes?.map(stroke=>({...stroke,size:stroke.size*width/layer.width,feather:(stroke.feather||0)*width/layer.width,points:stroke.points.map((v,i)=>v*(i%2?height/layer.height:width/layer.width))}));
 return {...layer,x:node.x()-(flipX?Math.cos(r)*width:0)+(flipY?Math.sin(r)*height:0),y:node.y()-(flipX?Math.sin(r)*width:0)-(flipY?Math.cos(r)*height:0),width,height,rotation,flipX,flipY,strokes:resize(layer.strokes),maskStrokes:resize(layer.maskStrokes)};
}
