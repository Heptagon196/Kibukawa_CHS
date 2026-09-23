(async()=>{
document.querySelector('[data-game=birthday]').click();
const f=document.querySelector('#game-frame');
for(let i=0;i<100;i++){await new Promise(r=>setTimeout(r,100));if(f.contentWindow.TYRANO?.kag?.stat?.charas?.izn)break;}
const w=f.contentWindow,k=w.TYRANO.kag,d=f.contentDocument;
const source=await w.fetch('data/scenario/first.ks').then(r=>r.text());
async function tag(name,pm){await new Promise((resolve,reject)=>{let t=setTimeout(()=>reject(Error(name+' timeout')),3000);k.ftag.nextOrder=()=>{clearTimeout(t);resolve()};k.ftag.startTag(name,pm)});}
async function macro(name){const body=source.split('[macro name="'+name+'"]')[1].split('[endmacro]')[0];for(const match of body.matchAll(/\[(\w+)([^\]]*)\]/g)){let pm={};for(const m of match[2].matchAll(/(\w+)=(?:"([^"]*)"|([^\s]+))/g))pm[m[1]]=m[2]??m[3];await tag(match[1],pm);}}
await macro('chara_izn');await tag('camera',{zoom:'1.4',x:'-160',y:'-60',time:'1000',wait:'false'});await macro('face_izn_ang');
await new Promise(r=>setTimeout(r,1800));
const parts=[...d.querySelectorAll('.tyrano_chara')].map(e=>({cls:e.className,src:e.querySelector('img')?.getAttribute('src'),imageRect:e.querySelector('img')?.getBoundingClientRect().toJSON(),rect:e.getBoundingClientRect().toJSON(),style:e.getAttribute('style')}));
const base=parts[0].rect; return {parts,ok:parts.every(p=>['x','y','width','height'].every(v=>Math.abs(p.rect[v]-base[v])<1))};
})()
