// Minimal DOM test double for event/API integration. Not a browser renderer.
const assert=require('node:assert/strict');
class Node {
 constructor(tag){this.tagName=tag.toUpperCase();this.children=[];this._text='';this._value=null;this.dataset={};this.attributes={};this.hidden=false;this.disabled=false;this.checked=false;this.events={};this.files=[];this.classes=new Set();this.classList={add:x=>this.classes.add(x),contains:x=>this.classes.has(x),toggle:(x,on)=>on?this.classes.add(x):this.classes.delete(x)};}
 set textContent(v){this._text=String(v);this.children=[];}get textContent(){return this._text+this.children.map(c=>c.textContent).join('');}
 set value(v){this._value=String(v);}get value(){return this._value??(this.tagName==='SELECT'?this.firstChild?.value||'':'');}
 set className(v){this.classes=new Set(v.split(' ').filter(Boolean));}get className(){return [...this.classes].join(' ');}
 append(...nodes){this.children.push(...nodes);}replaceChildren(...nodes){this.children=nodes;this._text='';if(this.tagName==='SELECT')this._value=null;}get firstChild(){return this.children[0];}
 setAttribute(k,v){this.attributes[k]=String(v);}addEventListener(k,fn){(this.events[k]??=[]).push(fn);}remove(){}async click(){if(!this.disabled)await this.onclick?.({detail:0});}
 async dispatch(type,event={}){for(const fn of this.events[type]||[])await fn(event);}
}
function makeDOM(html){
 const nodes=new Map();for(const m of html.matchAll(/<([a-z]+)[^>]*\bid="([^"]+)"[^>]*>/g)){const n=new Node(m[1]);n.id=m[2];const value=/\bvalue="([^"]*)"/.exec(m[0]);if(value)n.value=value[1];n.hidden=/\bhidden\b/.test(m[0]);n.disabled=/\bdisabled\b/.test(m[0]);nodes.set(n.id,n);}
 for(const m of html.matchAll(/<select[^>]*\bid="([^"]+)"[^>]*>([\s\S]*?)<\/select>/g)){const select=nodes.get(m[1]);for(const option of m[2].matchAll(/<option(?:\s+value="([^"]*)")?[^>]*>([^<]*)<\/option>/g)){const o=new Node('option');o.value=option[1]??option[2];o.textContent=option[2];select.append(o);}}
 const all=()=>[...nodes.values()].flatMap(function walk(n){return[n,...n.children.flatMap(walk)]});
 const document={getElementById:id=>{assert(nodes.has(id),`Missing HTML id: ${id}`);return nodes.get(id);},createElement:t=>new Node(t),createElementNS:(_,t)=>new Node(t),querySelectorAll:q=>q==='#sheet-preview button[data-row]'?all().filter(n=>n.tagName==='BUTTON'&&n.dataset.row!==undefined):all().filter(n=>['INPUT','SELECT','BUTTON'].includes(n.tagName))};
 const window={events:{},addEventListener(k,f){this.events[k]=f;}};return {nodes,document,window,all};
}
module.exports={makeDOM};
