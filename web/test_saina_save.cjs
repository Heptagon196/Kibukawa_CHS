// Isolated browser storage; exercise the actual Flash save/restore engine.
const {chromium}=require('C:/Users/hepta/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path'),http=require('http');
const root=path.join(__dirname,'saina-onsen/build'),out=path.join(__dirname,'saina-onsen/reports/save');
fs.mkdirSync(out,{recursive:true});
const fixture=`*start|读档回归检查
[BGSet pic="事務所"]
[CharaIN char="伊綱" look="nom"]
[TransAll t=1]
[Talker char="音成" SE=off]
保存前对白。[pp]
*menu|读档回归检查
[Var SaveSlot=1]
[AutoSave]
读档后应恢复此画面。[pp]
存档之后继续推进，不能破坏已存画面。[m]
[LoadGame no=1]
`;
(async()=>{
const server=http.createServer((req,res)=>{let file=path.join(root,decodeURIComponent(req.url.split('?')[0]));if(req.url==='/')file=path.join(root,'index.html');try {let data=fs.readFileSync(file);res.setHeader('Content-Type',file.endsWith('.wasm')?'application/wasm':file.endsWith('.js')?'text/javascript':file.endsWith('.html')?'text/html;charset=utf-8':'application/octet-stream');res.end(data)}catch(e){res.statusCode=404;res.end()}});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
let app;
let browser;
if(process.env.DESKTOP){
 const exe=path.join(__dirname,'desktop/portable/Kibukawa-Web-Spinoffs-CHS-portable/Kibukawa-Web-Spinoffs-CHS.exe');
 app=require('child_process').spawn(exe,[],{windowsHide:true,env:{...process.env,WEBVIEW2_USER_DATA_FOLDER:path.join(out,process.env.EXISTING?'user-save-copy2':'profile'),WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:'--remote-debugging-port=9338'}});
 for(let i=0;i<100;i++){try{browser=await chromium.connectOverCDP('http://127.0.0.1:9338');break}catch{await new Promise(r=>setTimeout(r,200))}}
}else browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
try{
const page=process.env.DESKTOP?browser.contexts()[0].pages()[0]:await browser.newPage({viewport:{width:1000,height:800}}),logs=[];
if(process.env.EXISTING){
 await page.waitForTimeout(2000);
 const saved=JSON.parse(fs.readFileSync(path.join(out,process.env.REPAIRED?'repaired-storage.json':'recovered-storage.json'),'utf8'));
 if(!Object.keys(saved).some(k=>k.endsWith('_1_a')))throw Error('Missing real save; do not test empty slots');
 await page.evaluate(data=>{for(const [k,v] of Object.entries(data))localStorage.setItem(k,v)},saved);
 fs.writeFileSync(path.join(out,'storage-initial.json'),JSON.stringify(await page.evaluate(()=>({...localStorage})),null,2));
}
let cold=false;
page.on('console',m=>logs.push(m.type()+': '+m.text()));page.on('pageerror',e=>logs.push(String(e)));
page.on('response',r=>{if(r.status()>=400)logs.push('HTTP '+r.status()+' '+r.url())});
if(process.env.BASELINE)await page.route('**/LemoNovel.swf',r=>r.fulfill({body:fs.readFileSync(path.join(__dirname,'desktop/portable/Kibukawa-Web-Spinoffs-CHS-portable/www/games/saina-onsen/LemoNovel.swf'))}));
if(process.env.REPAIRED)await page.route('**/LemoNovel.swf',r=>r.fulfill({body:fs.readFileSync(path.join(root,'LemoNovel.swf'))}));
if(!process.env.EXISTING){
await page.route('**/script/first.adv',r=>r.fulfill({body:fs.readFileSync(path.join(root,'script/first.adv'),'utf8').replace('[Var DebugFlug=0]',cold?'[Var DebugFlug=0]':'[Var DebugFlug=1]')}));
await page.route('**/script/s01.adv',r=>r.fulfill({body:process.env.ACTUAL?'[Var DebugFlug=0]\n[Goto label="start"]\n'+fs.readFileSync(path.join(root,'script/s03.adv'),'utf8'):fixture}));
}
await page.goto(process.env.DESKTOP?'http://kibukawa.localhost/games/saina-onsen/index.html':`http://127.0.0.1:${server.address().port}/`);await page.waitForTimeout(10000);
fs.writeFileSync(path.join(out,'storage.json'),JSON.stringify(await page.evaluate(()=>({...localStorage})),null,2));
let initial=await page.locator('#player').boundingBox();if(!process.env.EXISTING){await page.mouse.click(initial.x+650,initial.y+550);await page.waitForTimeout(1000);}
await page.locator('#player').screenshot({path:path.join(out,'before.png')});
const box=await page.locator('#player').boundingBox();if(!process.env.EXISTING){await page.mouse.click(box.x+650,box.y+550);await page.waitForTimeout(1000);}
if(process.env.COLD_LOAD || !process.env.EXISTING){
 cold=true;await page.reload();await page.waitForTimeout(8000);
 await page.mouse.click(box.x+400,box.y+443);await page.waitForTimeout(1000);
 await page.locator('#player').screenshot({path:path.join(out,'menu.png')});
 await page.mouse.click(box.x+350,box.y+(process.env.ACTUAL?355:397));
}
await page.waitForTimeout(10000);
await page.locator('#player').screenshot({path:path.join(out,'after.png')});
if(!process.env.EXISTING){
 await page.mouse.click(box.x+650,box.y+550);await page.waitForTimeout(1000);
 await page.reload();await page.waitForTimeout(8000);
 const saves=await page.evaluate(()=>({...localStorage}));
 const scene=Object.entries(saves).find(([key])=>key.endsWith('_1_d'));
 if(!scene || scene[1].length<1000)throw Error('Advancing after save/load erased the persisted scene');
 await page.mouse.click(box.x+400,box.y+443);await page.waitForTimeout(1000);
 await page.mouse.click(box.x+350,box.y+397);await page.waitForTimeout(5000);
 await page.locator('#player').screenshot({path:path.join(out,'after.png')});
}
fs.writeFileSync(path.join(out,'console.txt'),logs.join('\n'));
const result=require('child_process').spawnSync(path.join(__dirname,'../.venv/Scripts/python.exe'),['-c',`from PIL import Image\nfrom pathlib import Path\np=Path(r'${out}')\na=Image.open(p/'before.png').convert('RGB');b=Image.open(p/'after.png').convert('RGB')\nbright=lambda im:sum(max(px)>40 for px in im.getdata())\nprint('visible pixels before/after:',bright(a),bright(b))\nassert bright(a)>100000, 'fixture did not render'\nassert bright(b)>bright(a)*0.7, 'load left screen black'`],{encoding:'utf8'});
console.log(result.stdout);if(result.status)throw Error(result.stderr);
}finally{await browser.close();if(app)app.kill();server.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
