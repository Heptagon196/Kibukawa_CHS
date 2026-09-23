const {chromium}=require(process.env.PLAYWRIGHT_PATH||'C:/Users/hepta/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.BROWSER_PATH||'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
 try{
  const page=await browser.newPage({viewport:{width:1000,height:800}});
  const dir=path.join(__dirname,'saina-onsen/reports/ui');fs.mkdirSync(dir,{recursive:true});
  await page.route('**/script/first.adv',r=>r.fulfill({body:fs.readFileSync(path.join(__dirname,'saina-onsen/build/script/first.adv'),'utf8').replace('[Var DebugFlug=0]','[Var DebugFlug=1]'),contentType:'text/plain;charset=utf-8'}));
  await page.route('**/script/s01.adv',r=>r.fulfill({body:'*start|01「排版验证」\n[Talker char="癸生川"]\n第一行：这是中文对白的显示检查。[r]\n第二行：高亮[bw]关键线索[/bw]及标点。[r]\n第三行：这一行也必须完整显示。[pp]\n[Talker char=""]\n第一行：这是没有姓名的叙述文字。[r]\n第二行：依然保持原作的三行容量。[r]\n第三行：文字不应超出画面底边。[pp]\n[SaveMenu]\n[AutoSave]\n[LoadMenu]\n',contentType:'text/plain;charset=utf-8'}));
  await page.goto('http://127.0.0.1:8766/saina-onsen/build/');await page.waitForTimeout(12000);
  const box=await page.locator('#player').boundingBox();
  for(const name of ['speaker','narration','save']){
   await page.waitForTimeout(4000);await page.locator('#player').screenshot({path:path.join(dir,name+'.png')});
   if(name!=='save')await page.mouse.click(box.x+700,box.y+550);
  }
  // Select slot 1; the original SaveMenu schedules saving at the next AutoSave.
  await page.mouse.click(box.x+350,box.y+485);await page.waitForTimeout(1500);
  await page.locator('#player').screenshot({path:path.join(dir,'save-confirm.png')});
  await page.mouse.click(box.x+140,box.y+552);await page.waitForTimeout(2000);
  await page.locator('#player').screenshot({path:path.join(dir,'load.png')});
  console.log('Captured three-line speaker/narration, save and load menus');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
