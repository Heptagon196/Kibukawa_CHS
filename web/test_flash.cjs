// Run against the local preview server; an isolated headless browser is always closed.
const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'C:/Users/hepta/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs = require('fs');
const {execFileSync} = require('child_process');
const path = require('path');
(async () => {
 const browser = await chromium.launch({headless:true, executablePath:process.env.BROWSER_PATH || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
 const original=process.argv.includes('--original');
 const reports = path.join(__dirname,'saina-onsen/reports',original?'baseline':'verification'); fs.mkdirSync(reports,{recursive:true});
 const log=[];
 try {
  const page=await browser.newPage({viewport:{width:1000,height:800}});
  if(original) await page.route('**/build/LemoNovel.swf',r=>r.fulfill({path:path.join(__dirname,'saina-onsen/originals/LemoNovel.swf'),contentType:'application/x-shockwave-flash'}));
  const requests=[]; page.on('request',r=>requests.push(r.url()));
  page.on('console',m=>log.push(m.text()));
  await page.goto(process.argv.find(a=>a.startsWith('http')) || 'http://127.0.0.1:8766/saina-onsen/build/');
  await page.waitForTimeout(12000);
  await page.locator('#player').screenshot({path:path.join(reports,'menu.png')});
  fs.writeFileSync(path.join(reports,'console.txt'),log.join('\n'));
  const count=Number(execFileSync(path.join(__dirname,'../.venv/Scripts/python.exe'),['-c',
   "from PIL import Image; import sys; im=Image.open(sys.argv[1]).convert('RGB'); print(sum(min(p)>80 for p in im.crop((210,350,590,410)).get_flattened_data()))",path.join(reports,'menu.png')],{encoding:'utf8'}).trim());
  console.log(JSON.stringify({menuBrightPixels:count,required:200,pass:count>=200}));
  if(count<200) process.exitCode=1;
  if(count>=200) {
   const box=await page.locator('#player').boundingBox();
   await page.mouse.click(box.x+400,box.y+380);
   await page.waitForTimeout(4000);
   await page.locator('#player').screenshot({path:path.join(reports,'after-start.png')});
   for(let i=0;i<8;i++) {await page.mouse.click(box.x+400,box.y+540);await page.waitForTimeout(500);}
   await page.locator('#player').screenshot({path:path.join(reports,'dialogue.png')});
   fs.writeFileSync(path.join(reports,'requests.json'),JSON.stringify(requests,null,2));
   fs.writeFileSync(path.join(reports,'console.txt'),log.join('\n'));
   console.log(JSON.stringify({started:requests.some(u=>u.endsWith('/s01.adv'))}));
   if(!requests.some(u=>u.endsWith('/s01.adv')))process.exitCode=1;
   if(process.argv.includes('--extended')) {
    for(let i=0;i<80;i++) {await page.mouse.click(box.x+400,box.y+540);await page.waitForTimeout(200);}
    await page.locator('#player').screenshot({path:path.join(reports,'extended.png')});
   }
  }
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
