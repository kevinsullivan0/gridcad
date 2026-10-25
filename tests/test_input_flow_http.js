// Executes production app.js event handlers against the real Python HTTP API.
// DOM is a test double: no rendering, real pointer hit-testing or Windows claim.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const {makeDOM}=require('./dom_test_double');
const [origin,token,fixtures]=process.argv.slice(2),root=path.resolve(__dirname,'..');
const html=fs.readFileSync(path.join(root,'ui/index.html'),'utf8'),app=fs.readFileSync(path.join(root,'ui/app.js'),'utf8');
const checks=[],traffic=[],downloads=[];let failPreviewOnce=false;
function check(value,label){assert(value,label);checks.push(label);}
function setup(fragment,protocol="http:"){const dom=makeDOM(html);const ctx=vm.createContext({...dom,location:{hash:fragment,protocol,reload(){}},fetch:async(route,options)=>{traffic.push(route);if(failPreviewOnce&&route==='/api/workbook-preview'){failPreviewOnce=false;throw Error('Injected interrupted preview');}return fetch(origin+route,options);},console,URL:{createObjectURL(blob){downloads.push(blob);return 'blob:synthetic-test';},revokeObjectURL(){}},Blob,AbortController,setTimeout,clearTimeout});vm.runInContext(app,ctx);return {...dom,run:c=>vm.runInContext(c,ctx)};}
function file(name){const blob=new Blob([fs.readFileSync(path.join(fixtures,name))]);blob.name=name;return blob;}
(async()=>{
 let d=setup('#'+token,'file:');await d.run('startup');check(d.nodes.get('workbook').disabled&&d.nodes.get('session-status').textContent.includes('HTML file'),'Opening HTML directly is distinguished from running the local app');
 d=setup('');await d.run('startup');check(d.nodes.get('workbook').disabled,'Missing session disables workbook loading');check(d.nodes.get('session-status').textContent.includes('Session missing'),'Missing session has distinct recovery message');
 d=setup('#wrong-token');await d.run('startup');check(d.nodes.get('workbook').disabled,'Expired session disables workbook loading');check(d.nodes.get('session-status').textContent.includes('Session expired'),'Expired token is a session error, not a workbook error');
 d=setup('#'+token);await d.run('startup');const {nodes,run,all,window}=d;
 check(!nodes.get('workbook').disabled&&nodes.get('build-version').textContent.includes('alpha.3'),'Valid session reveals actual server build and enables loading');
 nodes.get('workbook').files=[file('multi.xlsx')];await nodes.get('workbook').dispatch('change');
 check(nodes.get('sheet').value==='Recipes','Multi-tab upload immediately displays saved active tab');
 check(all().some(n=>n.dataset.row===2&&n.dataset.column===2),'Addressed worksheet cells load without any PRINT file');
 check(!nodes.get('range').value,'Displaying active sheet does not infer recipe selection');
 check(nodes.get('sheet').children.length===4,'All three actual tabs remain selectable');
 // Recipe selection by real production pointer-handler event sequence.
 let cells=all().filter(n=>n.dataset.row!==undefined),a=cells.find(n=>n.dataset.row===2&&n.dataset.column===2),b=cells.find(n=>n.dataset.row===3&&n.dataset.column===5);
 a.onpointerdown({preventDefault(){},shiftKey:false});b.onpointerenter();window.events.pointerup();
 check(nodes.get('range').value==='B2:E3','Drag produces exact recipe range with internal hole');
 await nodes.get('check-recipes').click();check(nodes.get('recipe-check').textContent.includes('7 valid recipes, 1 blank positions, 0 cells'),'Workbook-only check parses full region and hole');
 nodes.get('region-sample').value='1,2';await nodes.get('check-recipes').click();check(nodes.get('recipe-check').textContent.includes('7 valid recipes'),'Workbook-only checks ignore malformed physical tray coordinates');nodes.get('region-sample').value='';
 check(nodes.get('save').disabled,'Workbook-only checks never enable candidate saving');
 // Mark sidebar without replacing recipe range.
 nodes.get('sheet-role').value='sidebar';await nodes.get('sheet-role').dispatch('change');a=cells.find(n=>n.dataset.row===2&&n.dataset.column===1);a.onpointerdown({preventDefault(){},shiftKey:false});window.events.pointerup();
 check(nodes.get('range').value==='B2:E3'&&run('workbookRegions[0].range')==='A2:A2','Sidebar annotation does not overwrite recipe selection');
 await nodes.get('check-recipes').click();check(nodes.get('recipe-check').textContent.includes('7 valid recipes'),'Explicit sidebar exclusion passes backend validation');
 a.onpointerdown({preventDefault(){},shiftKey:false});window.events.pointerup();
 await nodes.get('extend-selection').click();b=cells.find(n=>n.dataset.row===3&&n.dataset.column===1);b.onpointerdown({preventDefault(){},shiftKey:false});window.events.pointerup();
 check(run('workbookRegions.length===1 && workbookRegions[0].range==="A2:A3"'),'Extending a reselected reference mark replaces its anchor instead of adding overlap');
 nodes.get('sheet-role').value='inspect';await nodes.get('sheet-role').dispatch('change');a=cells.find(n=>n.dataset.row===2&&n.dataset.column===3);a.onpointerdown({preventDefault(){},shiftKey:false});window.events.pointerup();
 check(nodes.get('range').value==='B2:E3'&&run('workbookRegions.length===1'),'Inspect-only click preserves recipe and reference selections');
 nodes.get('sheet-role').value='sidebar';await nodes.get('sheet-role').dispatch('change');
 // Choose conflicting sidebar: do not silently subtract it.
 a=cells.find(n=>n.dataset.row===2&&n.dataset.column===2);a.onpointerdown({preventDefault(){},shiftKey:false});window.events.pointerup();await nodes.get('check-recipes').click();
 check(nodes.get('recipe-check').textContent.includes('overlaps'),'Overlapping marked sidebar is rejected, not silently skipped');
 await nodes.get('clear-workbook-regions').click();
 // Long sheet navigation and no-keyboard endpoint selection.
 nodes.get('sheet').value='Long';await nodes.get('sheet').dispatch('change');
 check(nodes.get('range').value===''&&nodes.get('preview-start').value==='B2','Tab switch resets selection and starts at actual used cells');
 nodes.get('sheet-role').value='recipe';await nodes.get('sheet-role').dispatch('change');cells=all().filter(n=>n.dataset.row!==undefined);a=cells.find(n=>n.dataset.row===2&&n.dataset.column===2);a.onpointerdown({preventDefault(){},shiftKey:false});window.events.pointerup();await nodes.get('extend-selection').click();
 nodes.get('preview-start').value='B482';await nodes.get('refresh-sheet').click();cells=all().filter(n=>n.dataset.row!==undefined);b=cells.find(n=>n.dataset.row===501&&n.dataset.column===3);b.onpointerdown({preventDefault(){},shiftKey:false});window.events.pointerup();
 check(nodes.get('range').value==='B2:C501','Choose-last-cell action spans pages without manual range numbers');
 nodes.get('transpose').checked=true;await nodes.get('transpose').dispatch('input');await nodes.get('transpose').dispatch('change');check(nodes.get('transpose-summary').textContent.includes('2 rows × 500 columns'),'Transpose shape updates before project mapping');
 await nodes.get('check-recipes').click();check(nodes.get('recipe-check').textContent.includes('Long!B2:C501'),'Long selection checks all rows, not just page');
 nodes.get('sheet').value='Recipes';await nodes.get('sheet').dispatch('change');check(nodes.get('preview-start').value==='A1'&&nodes.get('range').value==='','Short-tab switch does not retain late-page address/range');
 // Upload success + first preview interruption must preserve tabs and retry.
 failPreviewOnce=true;nodes.get('workbook').files=[file('multi.xlsx')];await nodes.get('workbook').dispatch('change');
 check(nodes.get('sheet').value==='Recipes'&&nodes.get('sheet').children.length===4,'Preview failure preserves uploaded workbook tab choices');
 check(nodes.get('activity').textContent.includes('Workbook loaded, but this preview failed'),'Preview failure is distinguished from unreadable workbook');
 await nodes.get('refresh-sheet').click();check(all().some(n=>n.dataset.row===2&&n.dataset.column===2),'Preview retry recovers without file reselection');
 // Cached formulas shown before admission, preserved provenance after confirmation.
 nodes.get('workbook').files=[file('cached.xlsx')];await nodes.get('workbook').dispatch('change');
 cells=all().filter(n=>n.dataset.row!==undefined);a=cells.find(n=>n.dataset.row===2&&n.dataset.column===2);a.onpointerdown({preventDefault(){},shiftKey:false});window.events.pointerup();
 check(nodes.get('sheet-cell-detail').textContent.includes('Saved result:'),'Formula raw/cache detail is available immediately');
 await nodes.get('check-recipes').click();check(nodes.get('recipe-check').textContent.includes('freshness cannot be verified'),'Unconfirmed cached formula cannot become a recipe');
 nodes.get('formula-cache').checked=true;await nodes.get('formula-cache').dispatch('input');await nodes.get('check-recipes').click();check(nodes.get('recipe-check').textContent.includes('1 valid recipes'),'Explicit cache confirmation admits valid bundle');
 nodes.get('workbook').files=[file('empty.xlsx')];await nodes.get('workbook').dispatch('change');
 check(nodes.get('sheet-preview-status').textContent.includes('has no populated cells'),'Empty worksheet gets explicit empty state rather than unexplained blank grid');
 nodes.get('workbook').files=[file('bad-cache.xlsx')];await nodes.get('workbook').dispatch('change');
 check(nodes.get('sheet-preview-status').textContent.includes('Raw cell view')&&all().some(n=>n.dataset.row===2&&n.dataset.column===3),'Malformed cache still exposes addressed raw cells with an explicit warning');
 nodes.get('range').value='C2';await nodes.get('range').dispatch('input');await nodes.get('check-recipes').click();check(nodes.get('recipe-check').textContent.includes('1 valid recipes'),'Unrelated malformed formula cache does not block checking selected literal cell');
 nodes.get('workbook').files=[file('infinite-cache.xlsx')];await nodes.get('workbook').dispatch('change');check(all().some(n=>n.dataset.row===2&&n.dataset.column===2),'Nonfinite saved cache still produces valid JSON and addressed cells');nodes.get('range').value='B2';await nodes.get('range').dispatch('input');nodes.get('formula-cache').checked=true;await nodes.get('formula-cache').dispatch('input');await nodes.get('check-recipes').click();check(nodes.get('recipe-check').textContent.includes('non-finite'),'Nonfinite formula cache gets explicit rejection, not JSON parse failure');
 // Restore synthetic physical grid and finish exact mapping API preview.
 nodes.get('workbook').files=[file('multi.xlsx')];await nodes.get('workbook').dispatch('change');nodes.get('range').value='B2:E3';await nodes.get('range').dispatch('input');nodes.get('project').files=[file('synthetic.PRINT')];await nodes.get('project').dispatch('change');
 for(const [id,value] of [['region-sample','29,39,83,67'],['region-row_label','11,39,17,67'],['region-column_label','29,27,86,30']]){nodes.get(id).value=value;await nodes.get(id).dispatch('input');}
 await nodes.get('analyze').click();check(!nodes.get('review').hidden&&run('report.grid.errors.length===0'),'Real production Inspect flow reaches mapping with valid recipes');
 const chosen=nodes.get('candidate').children.find(o=>o.textContent.includes('Original axes'));
 check(!!chosen&&nodes.get('candidate').value==='','Valid orientations offered without silent selection');
 nodes.get('candidate').value=chosen.value;nodes.get('candidate').onchange();nodes.get('reviewed').checked=true;await nodes.get('reviewed').dispatch('change');nodes.get('overwrite').checked=true;await nodes.get('overwrite').dispatch('change');await nodes.get('compare').click();
 check(!nodes.get('save').disabled&&nodes.get('comparison').textContent.includes('bodies will change'),'Explicit review reaches actual disposable-copy material/preservation preview');
 async function freshReview(){await nodes.get('clear-workbook-regions').click();nodes.get('range').value='B2:E3';await nodes.get('range').dispatch('input');nodes.get('transpose').checked=false;await nodes.get('transpose').dispatch('input');await nodes.get('analyze').click();const option=nodes.get('candidate').children.find(o=>o.textContent.includes('Original axes'));nodes.get('candidate').value=option.value;nodes.get('candidate').onchange();nodes.get('reviewed').checked=true;await nodes.get('reviewed').dispatch('change');nodes.get('overwrite').checked=true;await nodes.get('overwrite').dispatch('change');await nodes.get('compare').click();assert(!nodes.get('save').disabled);return run('({analysis_id:report.analysis_id,review_id:comparison.review_id})');}
 for(const change of ['range','transpose','sidebar','workbook-check']){
  const old=await freshReview();
  if(change==='range'){nodes.get('range').value='B2:E2';await nodes.get('range').dispatch('input');}
  if(change==='transpose'){nodes.get('transpose').checked=true;await nodes.get('transpose').dispatch('input');await nodes.get('transpose').dispatch('change');}
  if(change==='sidebar'){nodes.get('sheet-role').value='sidebar';await nodes.get('sheet-role').dispatch('change');const cell=all().find(n=>n.dataset.row===2&&n.dataset.column===1);cell.onpointerdown({preventDefault(){},shiftKey:false});window.events.pointerup();}
  if(change==='workbook-check')await nodes.get('check-recipes').click();
  check(nodes.get('save').disabled,'Changing '+change+' disables the previously reviewed save');
  await assert.rejects(run('call("/api/save",'+JSON.stringify(old)+')'));
  check(true,'Server rejects old review after '+change+' change');
 }
 await freshReview();await nodes.get('save').click();check(nodes.get('save-result').textContent.includes('Saved unverified candidate'),'Actual UI save flow completes separate candidate creation and download');check(nodes.get('save').disabled,'Save review is consumed after candidate download');const bytes=Buffer.from(await downloads.at(-1).arrayBuffer());check(bytes.subarray(0,2).toString()==='PK','Downloaded candidate contains a real PRINT ZIP archive');fs.writeFileSync(path.join(fixtures,'downloaded.PRINT'),bytes);
 await run('requests');
 console.log(JSON.stringify({kind:'Production JavaScript event handlers plus real Python HTTP API, minimal DOM (not browser rendering)',checks_passed:checks.length,http_requests:traffic.length,checks},null,2));
})().catch(e=>{console.error(e);process.exitCode=1;});
