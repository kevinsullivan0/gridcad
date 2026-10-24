/* New DOM-contract tests using a minimal test double, NOT browser/visual QA. */
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const root=path.resolve(__dirname,'..'),html=fs.readFileSync(path.join(root,'ui/index.html'),'utf8');
class Node {
 constructor(tag){this.tagName=tag.toUpperCase();this.children=[];this._text='';this._value='';this.dataset={};this.attributes={};this.hidden=false;this.disabled=false;this.checked=false;this.events={};this.files=[];this.classes=new Set();this.classList={add:x=>this.classes.add(x),contains:x=>this.classes.has(x),toggle:(x,on)=>on?this.classes.add(x):this.classes.delete(x)};}
 set textContent(v){this._text=String(v);this.children=[];}get textContent(){return this._text+this.children.map(c=>c.textContent).join('');}
 set value(v){this._value=String(v);}get value(){return this._value;}
 set className(v){this.classes=new Set(v.split(' ').filter(Boolean));}get className(){return [...this.classes].join(' ');}
 append(...nodes){this.children.push(...nodes);}replaceChildren(...nodes){this.children=nodes;this._text='';}get firstChild(){return this.children[0];}
 setAttribute(k,v){this.attributes[k]=String(v);}addEventListener(k,fn){(this.events[k]??=[]).push(fn);}remove(){}click(){this.onclick?.({detail:0});}
}
const nodes=new Map();for(const m of html.matchAll(/<([a-z]+)[^>]*\bid="([^"]+)"[^>]*>/g)){const n=new Node(m[1]);n.id=m[2];n.value=/\bvalue="([^"]*)"/.exec(m[0])?.[1]||'';n.hidden=/\bhidden\b/.test(m[0]);nodes.set(n.id,n);}
const all=()=>[...nodes.values()].flatMap(function walk(n){return[n,...n.children.flatMap(walk)]});
const document={getElementById:id=>{assert(nodes.has(id),`Missing HTML id: ${id}`);return nodes.get(id);},createElement:t=>new Node(t),createElementNS:(_,t)=>new Node(t),querySelectorAll:q=>q==='#sheet-preview button[data-row]'?all().filter(n=>n.tagName==='BUTTON'&&n.dataset.row!==undefined):all().filter(n=>['INPUT','SELECT','BUTTON'].includes(n.tagName))};
const window={events:{},addEventListener(k,f){this.events[k]=f;}};
const requests=[];
let response={},previewFails=false;
const ctx=vm.createContext({document,window,location:{hash:'#testtoken',reload(){}},fetch:async(url,opts)=>{requests.push({url,body:JSON.parse(opts.body)});return{ok:!(previewFails&&url==='/api/workbook-preview'),json:async()=>previewFails&&url==='/api/workbook-preview'?{error:'Preview starts at one Excel cell'}:response};},console,URL:{createObjectURL(){return'test';},revokeObjectURL(){}},Blob:function(){},setTimeout(){}});
vm.runInContext(fs.readFileSync(path.join(root,'ui/app.js'),'utf8'),ctx);
const run=code=>vm.runInContext(code,ctx),checks=[];
function check(value,label){assert(value,label);checks.push(label);}
(async()=>{
 check(run("JSON.stringify(rangeBounds('$B$2:$F$4'))")==='[2,2,6,4]','Absolute addressed ranges recognized');
 for(const bad of ['A0','B3:A2','A1:XFE1','A1:A1048577','A:A','1:2'])check(run(`rangeBounds(${JSON.stringify(bad)})===null`),'Invalid/unbounded range rejected: '+bad);
 nodes.get('sheet').value='Samples';nodes.get('range').value='B2:E3';nodes.get('transpose').checked=true;nodes.get('formula-cache').checked=true;
 check(run('options().transpose===true && options().formula_cache_confirmed===true'),'UI sends explicit transpose and formula cache confirmations');
 response={sheet:'Samples',preview_range:'B2:C3',start_row:2,start_column:2,rows:2,columns:2,column_labels:['B','C'],preview_limited:false,preview_cells:[{cell:'B2',row:2,column:2,raw:'=A1',cached_value:'20/0/0/0/30/50',is_formula:true},{cell:'C2',row:2,column:3,raw:20,is_formula:false},{cell:'B3',row:3,column:2,raw:null,is_formula:false},{cell:'C3',row:3,column:3,raw:'0/0/0/0/0/100',is_formula:false}]};
 await run('loadSheetPreview()');
 let buttons=all().filter(n=>n.dataset.row!==undefined);
 check(buttons.length===4,'Addressed worksheet grid builds bounded cells');
 buttons[0].onpointerdown({preventDefault(){},shiftKey:false});buttons[3].onpointerenter();window.events.pointerup();
 check(nodes.get('range').value==='B2:C3','Drag sets rectangle including holes');
 check(buttons.every(b=>b.classList.contains('selected')),'Drag highlights every selected cell');
 run("selectSheetCell(sheetPreview.preview_cells[1])");
 check(nodes.get('sheet-cell-detail').textContent.includes('scalar, not a six-channel recipe'),'Scalar worksheet detail explains bundle mismatch');
 response={...response,preview_range:'B41:C41',start_row:41,rows:1,preview_cells:[{cell:'B41',row:41,column:2,raw:null,is_formula:false},{cell:'C41',row:41,column:3,raw:null,is_formula:false}]};
 await run('loadSheetPreview()');buttons=all().filter(n=>n.dataset.row===41);
 buttons[1].onpointerdown({preventDefault(){},shiftKey:true});window.events.pointerup();
 check(nodes.get('range').value==='B2:C41','Shift-click extends anchored selection across pages');
 check(requests.some(r=>r.url==='/api/invalidate'),'Selection revokes prior reviewed save');
 previewFails=true;nodes.get('sheet').value='Different tab';nodes.get('preview-start').value='A0';
 await assert.rejects(run('loadSheetPreview()'));
 check(nodes.get('sheet-preview').children.length===0&&run('sheetPreview===null'),'Failed tab refresh clears old selectable cells and old sheet data');
 check(nodes.get('sheet-cell-detail').hidden&&nodes.get('sheet-preview-status').textContent.includes('unavailable'),'Failed refresh clears stale details and displays recovery instruction');
 previewFails=false;nodes.get('range').value='B2:C41';nodes.get('preview-start').value='B400';nodes.get('transpose').checked=true;
 await run('loadWorkbook()');
 check(nodes.get('range').value===''&&nodes.get('preview-start').value==='A1'&&!nodes.get('transpose').checked,'Workbook replacement resets range, start address and transpose');
 check(run('sheetAnchor===null'),'Workbook replacement clears selection anchor');

 run(`report={transpose:true,grid:{sheet:'Samples',range:'B2:C502',rows:501,columns:2,formula_count:0,parser_policy:{order:'CMYKWT'},cells:Array.from({length:1002},(_,i)=>({cell:'cell'+i,grid_row:Math.floor(i/2),grid_column:i%2,raw:null,role:'hole'}))}};gridPageRow=0;gridPageColumn=0;renderGrid(report.grid);`);
 check(nodes.get('grid-summary').textContent.includes('2 rows × 501 columns (transposed)'),'Transposed dimensions shown with original source dimensions');
 check(nodes.get('grid').children[0].children.length===2&&nodes.get('grid').children[0].children[0].children.length===30,'Long transposed recipe preview renders only visible page');
 nodes.get('grid-right').onclick();check(nodes.get('grid-page').textContent.includes('columns 31–60 of 501'),'Paging reaches next transposed columns');
 run("report={grid:{sheet:'Samples'}};showCell({cell:'B2',role:'sample',raw:'=A2',value_source:'saved_formula_result',cached_value:'20/0/0/0/30/50',recipe:{channels:{C:'20',M:'0',Y:'0',K:'0',W:'30',T:'50'},total:'100'}})");
 check(nodes.get('cell-detail').textContent.includes('Original cell content: =A2')&&nodes.get('cell-detail').textContent.includes('Total: 100%'),'Recipe detail retains formula, saved value, channel sum');
 nodes.get('review').hidden=false;run('invalidate()');check(nodes.get('review').hidden===false,'Editing role regions does not hide controls mid-entry');
 await run('requests');
 console.log(JSON.stringify({kind:'Node minimal-DOM contract tests, not browser QA',checks_passed:checks.length,checks},null,2));
})().catch(e=>{console.error(e);process.exitCode=1;});
