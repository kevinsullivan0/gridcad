'use strict';
const $=id=>document.getElementById(id), token=location.hash.slice(1);
let report=null, comparison=null, busy=false, uploaded={}, plot=null, lastGeometry=null, workbookInfo=null, sheetPreview=null, gridPageRow=0, gridPageColumn=0, sheetAnchor=null, sessionReady=false, workbookRegions=[], pendingRange=null, extendSelection=false, checkedCells=new Map(), anchorRegionIndex=null;
function text(tag,value,cls){const n=document.createElement(tag);n.textContent=value;if(cls)n.className=cls;return n;}
function issues(id,items){$(id).replaceChildren(...items.map(x=>text('p',typeof x==='string'?x:JSON.stringify(x))));}
function fail(e){$('error').textContent=e.message||String(e);$('error').hidden=false;}
function syncControls(){
 const locked=busy||!sessionReady;
 document.querySelectorAll('input,select,button').forEach(n=>{n.disabled=locked;});
 $('retry-session').disabled=busy;
 if(locked)return;
 $('sheet').disabled=!workbookInfo;
 for(const id of ['sheet-prev','sheet-next','sheet-left','sheet-right','sheet-home','refresh-sheet','sheet-role','extend-selection','clear-workbook-regions'])$(id).disabled=!workbookInfo||!$('sheet').value;
 $('check-recipes').disabled=!workbookInfo||!rangeBounds($('range').value);
 $('candidate').disabled=!report;$('compare').disabled=!report||!$('candidate').value||!$('reviewed').checked||!$('overwrite').checked;$('save').disabled=!comparison?.review_id;$('export').disabled=!report;
}
function setBusy(value,message=''){busy=value;$('activity').textContent=message;syncControls();}
function sessionProblem(message){sessionReady=false;$('session-status').textContent=message;syncControls();}
async function checkSession(){
 if(busy)return;
 if(location.protocol==='file:'){sessionProblem('This is the HTML file, not the running app. Double-click launch-windows.cmd and use the local browser link it opens.');return;}
 if(!token){sessionProblem('Session missing. Open the complete link printed in the running GridCAD console, including its private session code. No workbook has been loaded.');return;}
 setBusy(true,'Checking local connection…');
 try{const result=await call('/api/session',{});if(result.session_ready!==true)throw Error('This page and local app do not match. Reopen the link from the new launcher.');sessionReady=true;$('build-version').textContent=result.build+' · UNPUBLISHED REVIEW';$('session-status').textContent='Connected to this local GridCAD session. Choose your workbook below.';$('error').hidden=true;}
 catch(e){sessionProblem(e.message);fail(e);}
 finally{setBusy(false,sessionReady?'Ready to load your workbook.':'Connection needed before loading files.');}
}
// Serialize local requests so fast input changes cannot overtake invalidations.
let requests=Promise.resolve();
function call(path,data,binary=false){const run=async()=>{
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),30000);
 try{
  let r;try{r=await fetch(path,{method:'POST',headers:{'X-GridCAD-Token':token,'Content-Type':binary?'application/octet-stream':'application/json'},body:binary?data:JSON.stringify(data),signal:controller.signal});}catch(e){$('session-status').textContent='Last request did not finish. Check the local connection if retrying fails.';throw Error('The local app did not respond within the request window. Keep the GridCAD console open, then check the connection and reload this view.');}
  let value;try{value=await r.json();}catch(e){throw Error('The local app returned an unreadable response. Your originals are unchanged. Reload this view or reopen the current launcher link.');}
  if(!r.ok){if(r.status===403)sessionProblem('Session expired or wrong launcher link. Open the complete link from the current GridCAD console.');throw Error(value.error||'Request failed');}return value;
 }finally{clearTimeout(timer);}
 };const result=requests.then(run);requests=result.catch(()=>{});return result;}

function region(role){const value=$('region-'+role).value.trim();if(!value)return null;const parts=value.split(',').map(x=>x.trim());if(parts.length!==4||parts.some(x=>!x||!Number.isFinite(Number(x))))throw Error('Regions require four finite numbers: xmin, ymin, xmax, ymax.');return parts.map(Number);}
function workbookOptions(){return {sheet:$('sheet').value,range:$('range').value,order:$('order').value.toUpperCase(),delimiter:$('delimiter').value,empty_zero:$('empty-zero').checked,formula_cache_confirmed:$('formula-cache').checked,transpose:$('transpose').checked,workbook_regions:workbookRegions.map(x=>({...x}))};}
function options(){const selection={};const samples=region('sample');if(samples)selection.region_mm=samples;const roles={};for(const r of ['row_label','column_label']){const a=region(r);if(a)roles[r]=a;}if(Object.keys(roles).length)selection.role_regions_mm=roles;return {...workbookOptions(),tray_id:$('tray-id').value,selection};}

function invalidate(){ $('cell-detail').textContent='Inputs changed. Inspect again before relying on this preview.'; $('grid-summary').textContent='Inputs changed. Inspect again to refresh the recipes and mapping.'; $('grid').replaceChildren();$('recipe-errors').replaceChildren();$('formula-warnings').replaceChildren();$('candidate-summary').textContent='Inputs changed. Inspect again before reviewing an orientation.';renderTray(lastGeometry);if(sessionReady)call('/api/invalidate',{}).catch(fail);checkedCells.clear();$('recipe-check').textContent='Selection or options changed. Check the selected recipes again.';$('reviewed').checked=false;$('overwrite').checked=false;$('save').disabled=true;$('save-result').replaceChildren();comparison=null;report=null;$('candidate').value='';$('candidate').disabled=true;$('export').disabled=true;$('compare').disabled=true;$('comparison').replaceChildren();$('activity').textContent='Inputs changed. Check recipes or inspect mapping again.';syncControls();}
function showWorkbookInfo(info){
 workbookInfo=info;
 const previous=$('sheet').value;
 $('sheet').replaceChildren(text('option','Choose an Excel tab'));
 $('sheet').firstChild.value='';
 for(const tab of info?.sheets||[]){const o=text('option',tab.name);o.value=tab.name;$('sheet').append(o);}
 if(info?.sheets.some(tab=>tab.name===previous))$('sheet').value=previous;
 else if(info?.sheets.length)$('sheet').value=info.sheets.some(t=>t.name===info.active_sheet)?info.active_sheet:info.sheets[0].name;
 $('preview-start').value=info?.preview_origins?.[$('sheet').value]||'A1';
 showSheetInfo();
}
function showSheetInfo(){const tab=workbookInfo?.sheets.find(t=>t.name===$('sheet').value);$('sheet-info').textContent=tab?`Viewing “${tab.name}” (${workbookInfo.sheets.length} tab${workbookInfo.sheets.length===1?'':'s'}). Used area ${tab.used_range} includes headings and sidebars. No recipe range is inferred; select it below.`:'Choose the tab containing the recipe grid, not a separate settings or instructions tab.';}
function excelColumn(n){let out='';for(;n>0;n=Math.floor((n-1)/26))out=String.fromCharCode(65+(n-1)%26)+out;return out;}
function rangeBounds(value){const match=/^\$?([A-Z]+)\$?([1-9][0-9]*)(?::\$?([A-Z]+)\$?([1-9][0-9]*))?$/i.exec(value.trim());if(!match)return null;const col=s=>[...s.toUpperCase()].reduce((n,c)=>n*26+c.charCodeAt(0)-64,0);const a=col(match[1]),b=Number(match[2]),c=col(match[3]||match[1]),d=Number(match[4]||match[2]);return a<=c&&b<=d&&c<=16384&&d<=1048576?[a,b,c,d]:null;}
function intersects(a,b){return a&&b&&!(a[2]<b[0]||b[2]<a[0]||a[3]<b[1]||b[3]<a[1]);}
function highlightRange(){
 const bounds=rangeBounds($('range').value),pending=rangeBounds(pendingRange||'');
 const inside=(r,c,b)=>b&&c>=b[0]&&c<=b[2]&&r>=b[1]&&r<=b[3];
 document.querySelectorAll('#sheet-preview button[data-row]').forEach(b=>{const row=Number(b.dataset.row),col=Number(b.dataset.column);b.classList.toggle('selected',!!inside(row,col,bounds));b.classList.toggle('pending-mark',$('sheet-role').value!=='recipe'&&!!inside(row,col,pending));for(const role of ['sidebar','header'])b.classList.toggle(role+'-mark',workbookRegions.some(x=>x.role===role&&inside(row,col,rangeBounds(x.range))));b.setAttribute('aria-pressed',b.classList.contains('selected'));});
 const overlap=workbookRegions.find(x=>intersects(bounds,rangeBounds(x.range)));
 $('selection-status').textContent=bounds?`Recipe grid: ${$('sheet').value}!${excelColumn(bounds[0])}${bounds[1]}:${excelColumn(bounds[2])}${bounds[3]} · ${bounds[3]-bounds[1]+1} rows × ${bounds[2]-bounds[0]+1} columns. `+(overlap?'Overlaps marked '+overlap.role+' '+overlap.range+'. Adjust or remove that mark before checking.':'All blank positions inside are retained.'):$('range').value?'Enter a valid rectangle such as B2:F4.':'No recipe rectangle selected. Drag over the recipe cells below.';
 $('transpose-summary').textContent=bounds?`Mapping shape: ${$('transpose').checked?bounds[2]-bounds[0]+1:bounds[3]-bounds[1]+1} rows × ${$('transpose').checked?bounds[3]-bounds[1]+1:bounds[2]-bounds[0]+1} columns${$('transpose').checked?' (transposed)':''}. Original Excel addresses and holes stay attached. Physical label regions are not swapped.`:'Select a recipe rectangle to see its mapping dimensions. Transpose never edits Excel.';
 $('reference-regions').replaceChildren(...workbookRegions.map((x,i)=>{const row=text('p',`${x.role==='sidebar'?'Sidebar/reference':'Heading'}: ${x.range} · not imported`),remove=text('button','Remove','quiet');remove.type='button';remove.onclick=()=>{workbookRegions.splice(i,1);sheetAnchor=null;anchorRegionIndex=null;extendSelection=false;invalidate();highlightRange();};row.append(remove);return row;}));
 syncControls();
}

function selectSheetCell(c){
 const lines=[`${sheetPreview.sheet}!${c.cell}`, 'Original content: '+(c.raw===null?'(blank)':String(c.raw))];
 if(c.unsupported_formula_region)lines.push('Unsupported array/spill or data-table formula region: '+c.unsupported_formula_region+'. Paste evaluated recipes as values in a workbook copy before selecting this region.');
 if(c.cache_read_error)lines.push(c.cache_read_error);
 if(c.is_formula)lines.push('Saved result: '+(c.cached_value===null?'(missing or unreadable)':JSON.stringify(c.cached_value)), 'Not calculated by GridCAD. Confirm freshly recalculated/saved results before using formulas.');
 const value=c.is_formula?c.cached_value:c.raw;
 if(typeof value==='number'||typeof value==='boolean')lines.push('This is a scalar, not a six-channel recipe. It may be a sidebar input or a component value; GridCAD will not guess six channels.');
 const parsed=checkedCells.get(c.cell);if(parsed?.recipe)lines.push(Object.entries(parsed.recipe.channels).map(([k,v])=>k+' '+v+'%').join(' / '),'Total '+parsed.recipe.total+'%');else if(parsed?.error)lines.push('Recipe check: '+parsed.error);
 $('sheet-cell-detail').replaceChildren(...lines.map((line,i)=>text(i===0?'strong':'div',line)));$('sheet-cell-detail').hidden=false;
}
async function loadSheetPreview(){
 // Never let old-tab cells remain selectable during or after a failed refresh.
 sheetPreview=null;sheetDrag=null;$('sheet-preview').replaceChildren();$('sheet-cell-detail').hidden=true;$('sheet-cell-detail').replaceChildren();
 $('sheet-preview-status').textContent=$('sheet').value?'Loading worksheet data…':'Choose an Excel tab to see its cells.';
 if(!$('sheet').value)return;
 let data;try{data=await call('/api/workbook-preview',{sheet:$('sheet').value,start_cell:$('preview-start').value.trim()||'A1'});}catch(e){$('sheet-preview-status').textContent='Worksheet preview unavailable. Check the tab and start address, then choose Reload this view.';throw e;}sheetPreview=data;
 const table=document.createElement('table'),head=document.createElement('tr');head.append(text('th',''));for(const col of data.column_labels)head.append(text('th',col));table.append(head);
 let index=0;
 for(let r=0;r<data.rows;r++){const row=document.createElement('tr');row.append(text('th',data.start_row+r));for(let col=0;col<data.columns;col++){
  const c=data.preview_cells[index++],td=document.createElement('td'),value=c.is_formula?(c.cached_value===null?c.raw:c.cached_value):c.raw,b=text('button',value===null?'':String(value));
  b.type='button';b.dataset.row=c.row;b.dataset.column=c.column;b.setAttribute('aria-label',c.cell+': '+(value===null?'blank or no saved result':String(value)));b.title=c.cell+' · '+(c.unsupported_formula_region?'Unsupported structured formula region '+c.unsupported_formula_region+' · ':'')+(c.raw===null?'blank':String(c.raw));
  if(c.is_formula||c.unsupported_formula_region)b.classList.add('formula');if(c.unsupported_formula_region||(c.is_formula&&c.cached_value===null))b.classList.add('missing');
  b.onpointerdown=e=>{if(busy||!sessionReady)return;e.preventDefault();selectSheetCell(c);if($('sheet-role').value==='inspect')return;const extend=!!((e.shiftKey||extendSelection)&&sheetAnchor);sheetDrag={start:extend?sheetAnchor:c,last:c,extending:extend,previousRange:$('range').value};if(!extend){sheetAnchor=c;anchorRegionIndex=null;}paintSheetDrag(c);};
  b.onpointerenter=()=>{if(sheetDrag){sheetDrag.last=c;paintSheetDrag(c);}};
  b.onclick=e=>{if(e.detail===0&&!busy&&sessionReady){selectSheetCell(c);if($('sheet-role').value==='inspect')return;const extend=!!((e.shiftKey||extendSelection)&&sheetAnchor);sheetDrag={start:extend?sheetAnchor:c,last:c,extending:extend,previousRange:$('range').value};if(!extend){sheetAnchor=c;anchorRegionIndex=null;}paintSheetDrag(c);finishSheetSelection();}};
  td.append(b);row.append(td);
 }table.append(row);}
 $('sheet-preview').replaceChildren(table);$('sheet-cell-detail').hidden=true;
 $('sheet-preview-status').textContent=data.cache_read_error?`Raw cell view for ${data.sheet}!${data.preview_range}. ${data.cache_read_error}`:data.sheet_nonempty_count===0?`Worksheet “${data.sheet}” has no populated cells. Choose another tab, or keep this empty data view. No recipe range is inferred.`:data.preview_nonempty_count===0?`No populated cells on page ${data.sheet}!${data.preview_range}. This worksheet has data elsewhere; choose First used cells or navigate to another page.`:`Showing ${data.sheet}!${data.preview_range}. `+(data.preview_limited?'Preview is limited to 40 rows × 30 columns; use the page buttons or optional “Jump to cell” to view another area.':'Drag the recipe rectangle. Sidebar values and headings can remain outside it.');highlightRange();
}
let sheetDrag=null;
function paintSheetDrag(c){const a=sheetDrag.start;pendingRange=`${excelColumn(Math.min(a.column,c.column))}${Math.min(a.row,c.row)}:${excelColumn(Math.max(a.column,c.column))}${Math.max(a.row,c.row)}`;if($('sheet-role').value==='recipe')$('range').value=pendingRange;highlightRange();}
function finishSheetSelection(){
 if(!sheetDrag)return;const extending=sheetDrag.extending;sheetDrag=null;
 if($('sheet-role').value!=='recipe'&&pendingRange){
  if(extending&&anchorRegionIndex!==null&&workbookRegions[anchorRegionIndex]?.role===$('sheet-role').value)workbookRegions[anchorRegionIndex]={role:$('sheet-role').value,range:pendingRange};
  else if(workbookRegions.length>=32)fail(Error('At most 32 reference regions. Remove an old mark before adding another.'));
  else{const existing=workbookRegions.findIndex(x=>x.role===$('sheet-role').value&&x.range===pendingRange);if(existing>=0)anchorRegionIndex=existing;else{workbookRegions.push({role:$('sheet-role').value,range:pendingRange});anchorRegionIndex=workbookRegions.length-1;}}
 }
 pendingRange=null;extendSelection=false;$('extend-selection').textContent='Choose last cell next';invalidate();highlightRange();
}
window.addEventListener('pointerup',finishSheetSelection);
window.addEventListener('pointercancel',()=>{if(sheetDrag&&$('sheet-role').value==='recipe')$('range').value=sheetDrag.previousRange;sheetDrag=null;pendingRange=null;extendSelection=false;invalidate();highlightRange();});

async function refreshSheet(){if(busy||!sessionReady)return;$('error').hidden=true;setBusy(true,'Reading worksheet data…');try{await loadSheetPreview();}catch(e){fail(e);}finally{setBusy(false,'Worksheet preview only. Inspect inputs to validate recipes and mapping.');}}
async function uploadInput(kind){
 const file=$(kind).files[0];
 if(!file)throw Error(kind==='workbook'?'Choose an Excel .xlsx workbook first.':'Choose a saved .PRINT project first.');
 if(!file.name.toLowerCase().endsWith(kind==='workbook'?'.xlsx':'.print'))throw Error('Choose a .xlsx workbook and a .PRINT project.');
 if(file.size>(kind==='workbook'?20:128)*1024*1024)throw Error(kind+' exceeds the local upload limit.');
 if(uploaded[kind]!==file){const result=await call('/api/upload/'+kind,file,true);uploaded[kind]=file;$(kind+'-state').textContent='Local copy loaded · '+(file.size/1024).toFixed(1)+' KiB';if(kind==='workbook')showWorkbookInfo(result.workbook_info);}
}
async function loadWorkbook(){
 if(busy||!sessionReady)return;
 invalidate();workbookRegions=[];pendingRange=null;extendSelection=false;sheetAnchor=null;anchorRegionIndex=null;$('range').value='';$('preview-start').value='A1';$('transpose').checked=false;highlightRange();uploaded.workbook=null;workbookInfo=null;$('formula-cache').checked=false;$('sheet').replaceChildren(text('option','Loading Excel tabs…'));$('sheet').firstChild.value='';$('sheet-info').textContent='';$('sheet-preview').replaceChildren();$('sheet-cell-detail').hidden=true;sheetPreview=null;$('error').hidden=true;
 setBusy(true,'Reading Excel tabs locally…');
 try{await uploadInput('workbook');await loadSheetPreview();$('activity').textContent='Workbook visible. Select the recipe grid here; sidebars can remain outside it.';}
 catch(e){fail(e);if(workbookInfo){$('activity').textContent='Workbook loaded, but this preview failed. Tabs are available: choose another tab or Reload this view.';}else{$('activity').textContent='Workbook could not be read. Choose another file or select this file again.';$('sheet-preview-status').textContent=$('activity').textContent;}}
 finally{setBusy(false,$('activity').textContent);}
}
async function analyze(){
 if(busy||!sessionReady)return;$('error').hidden=true;setBusy(true,'Inspecting copies locally…');comparison=null;report=null;$('review').hidden=true;
 try{
  await uploadInput('workbook');
  if(!$('sheet').value)throw Error('Choose the Excel tab containing your recipe grid.');
  if(!$('range').value.trim())throw Error('Enter the recipe grid rectangle, for example B2:F4. Exclude headings and sidebar inputs, but keep blank positions inside the grid.');
  await uploadInput('project');
  report=await call('/api/analyze',options());gridPageRow=gridPageColumn=0;render();$('activity').textContent=report.grid.errors.length?'Some recipe cells need attention. Check the red cells below. Originals unchanged.':'Inspection complete. Review the cell-to-body mapping. Originals unchanged.';
 }catch(e){fail(e);$('activity').textContent='Review stopped. No project changes made.';}
 finally{setBusy(false,$('activity').textContent);}
}
async function checkRecipes(){
 if(busy||!sessionReady)return;invalidate();$('error').hidden=true;setBusy(true,'Checking selected recipe cells…');
 try{const o=workbookOptions();const result=await call('/api/workbook-check',o),g=result.grid;checkedCells=new Map(g.cells.map(c=>[c.cell,c]));
  const count=role=>g.cells.filter(c=>c.role===role).length;
  $('recipe-check').replaceChildren(text('p',`${g.sheet}!${g.range}: ${count('sample')} valid recipes, ${count('hole')} blank positions, ${g.errors.length} cells needing attention. ${g.formula_count} formula cells. No .PRINT or original workbook changed.`));
  for(const error of g.errors.slice(0,50)){const row=text('p',error.cell+': '+error.error),button=text('button','Show '+error.cell,'secondary');button.onclick=async()=>{if(busy)return;$('preview-start').value=error.cell;await refreshSheet();const c=sheetPreview?.preview_cells.find(c=>c.cell===error.cell);if(c)selectSheetCell(c);};row.append(button);$('recipe-check').append(row);}
  if(g.errors.length>50)$('recipe-check').append(text('p','Showing first 50 errors. Select any cell to inspect its checked result; all selected cells were checked.'));
  $('activity').textContent=g.errors.length?'Recipe issues found. Use Show cell to inspect each one.':count('sample')===0?'No populated recipes selected. Choose the actual recipe grid before mapping.':'Recipes checked. Choose a .PRINT project to continue to mapping.';
 }catch(e){fail(e);$('recipe-check').textContent=e.message;$('activity').textContent='Recipe check stopped. Adjust the highlighted selection or options; originals unchanged.';}
 finally{setBusy(false,$('activity').textContent);}
}
function render(){const g=report.grid, geom=report.geometry,p=report.proposal;$('review').hidden=false;$('reviewed').checked=false;$('overwrite').checked=false;$('profile-gate').textContent=(report.profile_gate.candidate_allowed?'Candidate profile admitted: ':'Preview only: ')+report.profile_gate.reason;renderStoredProfile();$('stats').replaceChildren();for(const [v,label] of [[g.cells.filter(x=>x.role==='sample').length,'valid recipes'],[g.cells.filter(x=>x.role==='hole').length,'blank grid cells'],[geom?.bodies.length??'—','project bodies'],[p?.orientation_candidates.length??0,'possible orientations']]){const div=text('div','','stat');div.append(text('strong',v),text('span',label));$('stats').append(div);}renderGrid(g);renderTray(geom);issues('formula-warnings',g.warnings||[]);issues('recipe-errors',[...g.errors.slice(0,200).map(x=>x.cell+': '+x.error),...(g.errors.length>200?[`${g.errors.length} errors total. Showing the first 200; use the grid pages or save review JSON for all cells.`]:[])]);issues('geometry-issues',report.geometry_error?[report.geometry_error]:p?.issues||[]);$('uncertainties').replaceChildren(...(p?.uncertainties||['Geometry mapping is not available for these inputs.']).map(x=>text('li',x)));$('candidate').replaceChildren(text('option','Choose an orientation'));$('candidate').firstChild.value='';for(const c of p?.orientation_candidates||[]){const t=c.transform,o=text('option',`${t.transpose?'Transpose · ':''}${t.mirror_rows?'Mirror rows · ':''}${t.mirror_columns?'Mirror columns · ':''}${!t.transpose&&!t.mirror_rows&&!t.mirror_columns?'Original axes · ':''}${c.assignments.length} samples`);o.value=c.candidate_id;$('candidate').append(o);} $('candidate-summary').textContent=`${report.transpose?'Transpose enabled: Excel columns become mapping rows, and Excel rows become mapping columns.':'Original Excel rows and columns retained.'} No orientation is silently selected, even when only one fits. Check the cell addresses on the tray. Printed label text associations are not inferred.`;$('comparison').replaceChildren();}
function renderStoredProfile(){
 const stored=report.stored_profile||{},show=v=>v===null||v===undefined?'not stored':typeof v==='object'?JSON.stringify(v):String(v);
 const lines=['Model/profile: '+show(stored.gender),'Selected printer metadata: '+show(stored.selectedPrinter)];
 for(const tray of stored.trays||[])lines.push('Tray '+show(tray.id)+': '+Object.entries(tray).filter(([key])=>key!=='id').map(([key,value])=>key.replace('pj.tray.','')+' = '+show(value)).join(' · '));
 issues('stored-profile',lines);
}
function showCell(c){
 const values=[text('strong',`${report.grid.sheet}!${c.cell} · ${c.role==='sample'?'valid recipe':c.role==='hole'?'blank grid position':'needs attention'}`),text('div','Original cell content: '+(c.raw===null?'(blank)':String(c.raw)))];
 if(c.value_source==='saved_formula_result')values.push(text('div','Saved formula result: '+(c.cached_value===null?'(missing or unreadable)':JSON.stringify(c.cached_value))),text('div','GridCAD did not calculate this formula. Cache freshness cannot be verified.'));
 if(c.recipe)values.push(text('div',Object.entries(c.recipe.channels).map(([k,v])=>k+' '+v+'%').join(' / ')),text('div','Total: '+c.recipe.total+'% · exact values, no normalization'));
 else values.push(text('div',c.error||'Blank cell: no recipe assignment. The position remains part of the grid; it is not an all-zero recipe.'));
 $('cell-detail').replaceChildren(...values);
}
function renderGrid(g){
 const transposed=report.transpose,rows=transposed?g.columns:g.rows,columns=transposed?g.rows:g.columns;
 $('grid-summary').textContent=`Excel tab “${g.sheet}”, range ${g.range}: source ${g.rows} rows × ${g.columns} columns. Mapping preview ${rows} rows × ${columns} columns${transposed?' (transposed)':''}. Original Excel addresses are preserved. ${g.formula_count||0} formula cells. Read order: ${g.parser_policy.order}.`;
 $('grid-page').textContent=`Showing mapping rows ${gridPageRow+1}–${Math.min(rows,gridPageRow+40)} of ${rows}, columns ${gridPageColumn+1}–${Math.min(columns,gridPageColumn+30)} of ${columns}. Blank positions are retained. All cells are inspected, not just this page.`;
 const table=document.createElement('table'),by=new Map(g.cells.map(c=>[c.grid_row+','+c.grid_column,c]));let shown=0;
 for(let r=gridPageRow;r<Math.min(rows,gridPageRow+40);r++){const tr=document.createElement('tr');for(let col=gridPageColumn;col<Math.min(columns,gridPageColumn+30);col++,shown++){
  const c=by.get(transposed?col+','+r:r+','+col),td=document.createElement('td'),b=text('button',c.cell,c.role);
  const value=c.value_source==='saved_formula_result'?c.cached_value:c.raw;
  b.append(text('span',value===null?'(blank / no saved result)':String(value),'cell-value'),text('span',c.role==='sample'?'Total '+c.recipe.total+'%':c.role==='hole'?'Hole':'Needs attention','cell-status'));
  b.title=c.error||String(value??'Blank cell');b.onclick=()=>showCell(c);td.append(b);tr.append(td);
 }table.append(tr);}
 $('grid').replaceChildren(table);
 const first=g.cells.find(c=>c.role==='invalid' && (transposed?c.grid_column:c.grid_row)>=gridPageRow && (transposed?c.grid_column:c.grid_row)<gridPageRow+40 && (transposed?c.grid_row:c.grid_column)>=gridPageColumn && (transposed?c.grid_row:c.grid_column)<gridPageColumn+30)||by.get(transposed?gridPageColumn+','+gridPageRow:gridPageRow+','+gridPageColumn);if(first)showCell(first);
}
function svg(tag,attrs){const n=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));return n;}
function renderTray(geom){lastGeometry=geom;$('tray').replaceChildren();plot=null;if(!geom?.bodies.length)return;const bodies=geom.bodies,xmin=Math.min(...bodies.map(b=>b.bounds_mm[0][0])),xmax=Math.max(...bodies.map(b=>b.bounds_mm[1][0])),ymin=Math.min(...bodies.map(b=>b.bounds_mm[0][1])),ymax=Math.max(...bodies.map(b=>b.bounds_mm[1][1]));const scale=Math.min(580/Math.max(1,xmax-xmin),360/Math.max(1,ymax-ymin));plot={xmin,ymin,xmax,ymax,scale,px:x=>30+(x-xmin)*scale,py:y=>390-(y-ymin)*scale};for(const b of bodies){const lo=b.bounds_mm[0],hi=b.bounds_mm[1],rect=svg('rect',{x:plot.px(lo[0]),y:plot.py(hi[1]),width:Math.max(2,(hi[0]-lo[0])*scale),height:Math.max(2,(hi[1]-lo[1])*scale),rx:2,fill:'#718d77',stroke:'#47684e','stroke-width':.7});const title=svg('title',{});title.textContent=b.occurrence_id+' · centre '+b.centroid_mm.slice(0,2).map(x=>x.toFixed(3)).join(', ')+' mm';rect.append(title);$('tray').append(rect);}for(const [role,color] of [['sample','#298368'],['row_label','#df9d42'],['column_label','#7e70aa']]){let r;try{r=region(role);}catch{continue;}if(r)$('tray').append(svg('rect',{x:plot.px(r[0]),y:plot.py(r[3]),width:(r[2]-r[0])*scale,height:(r[3]-r[1])*scale,fill:color,'fill-opacity':.12,stroke:color,'stroke-width':2}));}const label=svg('text',{x:15,y:18,fill:'#617c65','font-size':12});label.textContent='XY · mm · +Y ↑';$('tray').append(label);}
function renderOrientation(candidate){
 if(!plot)return;
 // For a dense grid show corner/edge anchors; full exact correspondence remains in preview.
 const display=candidate.assignments.length<=80?candidate.assignments:candidate.assignments.filter(a=>a.source_grid[0]===0||a.source_grid[0]===report.grid.rows-1).filter((a,i)=>i%Math.max(1,Math.ceil(report.grid.columns/12))===0);
 for(const a of display){const label=svg('text',{x:plot.px(a.centroid_mm[0]),y:plot.py(a.centroid_mm[1])-5,fill:'#142d23','font-size':11,'text-anchor':'middle','pointer-events':'none'});label.textContent=a.cell;$('tray').append(label);}
}
let drag=null;
function point(e){const pt=$('tray').createSVGPoint();pt.x=e.clientX;pt.y=e.clientY;return pt.matrixTransform($('tray').getScreenCTM().inverse());}
$('tray').onpointerdown=e=>{if(!plot||busy)return;const p=point(e);drag={start:p,rect:svg('rect',{x:p.x,y:p.y,width:0,height:0,fill:'#298368','fill-opacity':.15,stroke:'#298368'})};$('tray').append(drag.rect);$('tray').setPointerCapture(e.pointerId);};
$('tray').onpointermove=e=>{if(!drag)return;const p=point(e);for(const [k,v] of Object.entries({x:Math.min(p.x,drag.start.x),y:Math.min(p.y,drag.start.y),width:Math.abs(p.x-drag.start.x),height:Math.abs(p.y-drag.start.y)}))drag.rect.setAttribute(k,v);};
$('tray').onpointerup=e=>{if(!drag)return;const p=point(e),s=drag.start;drag.rect.remove();drag=null;if(Math.abs(p.x-s.x)<3||Math.abs(p.y-s.y)<3)return;const x=v=>plot.xmin+(v-30)/plot.scale,y=v=>plot.ymin+(390-v)/plot.scale;const r=[Math.min(x(p.x),x(s.x)),Math.min(y(p.y),y(s.y)),Math.max(x(p.x),x(s.x)),Math.max(y(p.y),y(s.y))];$('region-'+$('role').value).value=r.map(v=>v.toFixed(3)).join(', ');const geom=lastGeometry;invalidate();renderTray(geom);};
$('tray').onpointercancel=()=>{if(drag)drag.rect.remove();drag=null;};
$('candidate').onchange=()=>{call('/api/revoke-review',{}).catch(fail);$('reviewed').checked=false;$('save').disabled=true;comparison=null;$('comparison').replaceChildren();$('compare').disabled=true;const c=report?.proposal?.orientation_candidates.find(x=>x.candidate_id===$('candidate').value);renderTray(lastGeometry);if(c){renderOrientation(c);$('candidate-summary').textContent=`${c.assignments.length} sample bodies, ${c.targets.filter(t=>t.role!=='sample').reduce((n,t)=>n+t.occurrence_ids.length,0)} label glyphs, ${report.proposal.preserved_other_ids.length} other bodies preserved. ${c.transform.transpose?'Transposed sample axes; ':''}review label coverage explicitly. Printed row/column labels stay in the selected physical regions; their text is not changed or inferred. Unspecified labels are not colored.`;issues('comparison',c.label_grouping_issues);}};
function renderComparison(){
 const p=comparison.preview,r=comparison.result;
 issues('comparison',[...(p.issues||[]),...(p.warnings||[]),...(r?.source_layout_warnings||[]),r?`${r.changed_objects} bodies will change; ${r.skipped_exact_matches} complete exact matches skipped; ${r.preserved_unmatched_objects} unselected bodies preserved. Python checks passed; normal GrabCAD reopen/recompose still required.`:'Preview only: '+comparison.profile_gate.reason]);
 const details=document.createElement('details');details.append(text('summary','Exact cell → body recipes and label changes'));
 const changes=new Set(r?.changed_occurrence_ids||[]);
 for(const a of p.assignments.slice(0,1000)){const recipe=a.recipe?Object.entries(a.recipe.channels).map(([k,v])=>k+' '+v+'%').join(' / '):'Direct Tray Materials → EcoFlex Black';details.append(text('p',`${a.cell||a.role}${a.source_grid?' [source row '+(a.source_grid[0]+1)+', column '+(a.source_grid[1]+1)+' → target row '+(a.target_grid[0]+1)+', column '+(a.target_grid[1]+1)+']':''}: ${recipe} → ${a.occurrence_ids.join(', ')}${r?' · '+a.occurrence_ids.filter(id=>changes.has(id)).length+' change(s)':''}`));}
 if(p.assignments.length>1000)details.append(text('p',`${p.assignments.length} assignments total. Showing first 1,000; save review JSON for the complete exact mapping.`));
 $('comparison').append(details);
}
$('compare').onclick=async()=>{if(busy)return;$('error').hidden=true;comparison=null;setBusy(true,'Checking exact recipes, changes and preservation…');try{comparison=await call('/api/preview',{analysis_id:report.analysis_id,candidate_id:$('candidate').value,reviewed:$('reviewed').checked,overwrite_targets:$('overwrite').checked});renderComparison();}catch(e){fail(e);}finally{setBusy(false,'Preview complete. Original files unchanged.');}};
function downloadBlob(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),30000);}
$('save').onclick=async()=>{if(busy||!comparison?.review_id)return;$('error').hidden=true;const reviewId=comparison.review_id;comparison.review_id=null;setBusy(true,'Saving and checking a new candidate copy…');try{const saved=await call('/api/save',{analysis_id:report.analysis_id,review_id:reviewId});const download=async()=>{const response=await fetch('/api/download/'+saved.download_id,{headers:{'X-GridCAD-Token':token}});if(!response.ok)throw Error('Download expired. Preview and save again.');downloadBlob(await response.blob(),saved.filename);};await download();$('save-result').replaceChildren(text('p',`Saved unverified candidate: ${saved.result.changed_objects} bodies changed. Python checks passed; normal GrabCAD reopen/recompose still required. Choose a new filename if your browser asks; do not replace your source.`));const retry=text('button','Download this candidate again','secondary');retry.onclick=()=>download().catch(fail);$('save-result').append(retry);}catch(e){fail(e);}finally{setBusy(false,'Original files unchanged.');}};
$('export').onclick=()=>{if(!report)return;const data={schema:'gridcad.local-review.v1',production_ready:false,writer_enabled:!!comparison?.writer_enabled,review:report,comparison};const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='gridcad-review.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
$('analyze').onclick=analyze;$('remap').onclick=analyze;$('clear').onclick=()=>{for(const r of ['sample','row_label','column_label'])$('region-'+r).value='';const geom=lastGeometry;invalidate();renderTray(geom);};
$('workbook').addEventListener('change',loadWorkbook);
$('project').addEventListener('change',()=>{lastGeometry=null;for(const r of ['sample','row_label','column_label'])$('region-'+r).value='';invalidate();});
$('sheet').addEventListener('change',()=>{sheetAnchor=null;anchorRegionIndex=null;workbookRegions=[];pendingRange=null;extendSelection=false;$('range').value='';$('preview-start').value=workbookInfo?.preview_origins?.[$('sheet').value]||'A1';showSheetInfo();$('formula-cache').checked=false;invalidate();highlightRange();return refreshSheet();});
$('range').addEventListener('input',highlightRange);
$('transpose').addEventListener('change',highlightRange);
$('sheet-role').addEventListener('change',()=>{sheetAnchor=null;anchorRegionIndex=null;pendingRange=null;extendSelection=false;$('extend-selection').textContent='Choose last cell next';highlightRange();});
$('extend-selection').onclick=()=>{if(!sheetAnchor){fail(Error('Click the first cell of the range, then choose this button.'));return;}extendSelection=true;$('extend-selection').textContent='Now click the last cell';$('sheet-preview-status').textContent='First cell: '+sheetAnchor.cell+'. Navigate if needed, then click the last cell.';};
$('clear-workbook-regions').onclick=()=>{$('range').value='';workbookRegions=[];sheetAnchor=null;anchorRegionIndex=null;pendingRange=null;extendSelection=false;invalidate();highlightRange();};
$('sheet-home').onclick=()=>{$('preview-start').value=workbookInfo?.preview_origins?.[$('sheet').value]||'A1';return refreshSheet();};
$('check-recipes').onclick=checkRecipes;
$('retry-session').onclick=checkSession;
$('refresh-sheet').onclick=refreshSheet;
for(const [id,dr,dc] of [['sheet-prev',-40,0],['sheet-next',40,0],['sheet-left',0,-30],['sheet-right',0,30]])$(id).onclick=()=>{const start=rangeBounds($('preview-start').value)||[1,1];$('preview-start').value=excelColumn(Math.max(1,Math.min(16384,start[0]+dc)))+Math.max(1,Math.min(1048576,start[1]+dr));return refreshSheet();};
for(const [id,dr,dc] of [['grid-prev',-40,0],['grid-next',40,0],['grid-left',0,-30],['grid-right',0,30]])$(id).onclick=()=>{if(!report)return;const rows=report.transpose?report.grid.columns:report.grid.rows,cols=report.transpose?report.grid.rows:report.grid.columns;gridPageRow=Math.max(0,Math.min(Math.floor((rows-1)/40)*40,gridPageRow+dr));gridPageColumn=Math.max(0,Math.min(Math.floor((cols-1)/30)*30,gridPageColumn+dc));renderGrid(report.grid);};
for(const id of ['project','sheet','range','order','delimiter','empty-zero','formula-cache','transpose','tray-id','region-sample','region-row_label','region-column_label'])$(id).addEventListener('input',invalidate);
for(const id of ['reviewed','overwrite'])$(id).addEventListener('change',()=>{call('/api/revoke-review',{}).catch(fail);comparison=null;$('save').disabled=true;$('comparison').replaceChildren();$('compare').disabled=!$('candidate').value||!$('reviewed').checked||!$('overwrite').checked;});
const startup=checkSession();

// A pasted full launcher link can change only the fragment in the same tab.
// Reload to adopt its token and discard any previous session UI safely.
window.addEventListener("hashchange",()=>location.reload());
