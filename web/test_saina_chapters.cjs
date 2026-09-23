// Isolated entry-point smoke tests; does not alter the build or the user's save.
const {chromium}=require(process.env.PLAYWRIGHT_PATH||'C:/Users/hepta/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path');
(async()=>{
const browser=await chromium.launch({headless:true,executablePath:process.env.BROWSER_PATH||'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
const dir=path.join(__dirname,'saina-onsen/reports/chapters');fs.mkdirSync(dir,{recursive:true});
try{
 for(let chapter=1;chapter<=5;chapter++){
  const context=await browser.newContext({viewport:{width:1000,height:800}}),page=await context.newPage();
  const req=[],errors=[];
  page.on('request',r=>req.push(r.url()));page.on('console',m=>{if(m.type()==='error')errors.push(m.text())});
  await page.route('**/script/first.adv',r=>r.fulfill({body:fs.readFileSync(path.join(__dirname,'saina-onsen/build/script/first.adv'),'utf8').replace('[Var DebugFlug=0]',`[Var DebugFlug=${chapter}]`),contentType:'text/plain;charset=utf-8'}));
  // Enter each chapter's actual start label, bypassing author debug menus.
  await page.route(`**/script/s0${chapter}.adv`,r=>r.fulfill({body:'[Var DebugFlug=0]\n[Goto label="start"]\n'+fs.readFileSync(path.join(__dirname,`saina-onsen/build/script/s0${chapter}.adv`),'utf8'),contentType:'text/plain;charset=utf-8'}));
  await page.goto('http://127.0.0.1:8766/saina-onsen/build/');await page.waitForTimeout(12000);
  const box=await page.locator('#player').boundingBox();
  // Chapter 4/5 debug menus: first item starts their original opening sequence.
  for(let step=0;step<4;step++){
   await page.waitForTimeout(2500);
   await page.locator('#player').screenshot({path:path.join(dir,`${chapter}-${step}.png`)});
   await page.mouse.click(box.x+650,box.y+540);
  }
  const ok=req.some(u=>u.endsWith(`/s0${chapter}.adv`));if(!ok)throw Error(`Chapter ${chapter} not loaded`);
  fs.writeFileSync(path.join(dir,`${chapter}.json`),JSON.stringify({chapter,loaded:ok,errors},null,2));
  console.log(JSON.stringify({chapter,loaded:ok,errors:errors.length}));await context.close();
 }
}finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
