const { chromium } = require('C:/Users/ngdia/Documents/projet_agri/plateforme/web/node_modules/playwright');
const out = 'C:/Users/ngdia/Documents/projet_agri/livrables/video/shots/';
const plan = [
  ['farmer','agriculteur@demo.sn','demo',['tableau','irrigation','meteo','assistant']],
  ['agro','agronome@demo.sn','demo',['tableau','recommandations','maladies','previsions']],
];
(async () => {
  let b; try { b = await chromium.launch({channel:'chrome'}); } catch(e){ b = await chromium.launch(); }
  for (const [tag,u,pw,pages] of plan) {
    const ctx = await b.newContext({viewport:{width:1920,height:1080}});
    const p = await ctx.newPage();
    await p.goto('http://localhost:3000/fr/login',{waitUntil:'networkidle'}); await p.waitForTimeout(2500);
    await p.fill('input[name=username]',u); await p.fill('input[name=password]',pw);
    await p.click('button[type=submit]'); await p.waitForLoadState('networkidle'); await p.waitForTimeout(3000);
    console.log(tag,'login ->',p.url());
    for (const pg of pages) {
      await p.goto('http://localhost:3000/fr/'+pg,{waitUntil:'networkidle'}); await p.waitForTimeout(7000);
      if (pg==='assistant') {
        await p.locator('textarea').first().fill("Comment préparer le sol pour l'oignon ?");
        await p.getByRole('button',{name:'Envoyer'}).click(); await p.waitForTimeout(15000);
      }
      await p.screenshot({path:out+tag+'_'+pg+'.png'}); console.log('shot',tag,pg,p.url());
    }
    await ctx.close();
  }
  await b.close();
})().catch(e=>{console.error('FAIL',e.message);process.exit(1)});
