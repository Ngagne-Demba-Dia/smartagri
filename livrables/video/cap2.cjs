const { chromium } = require('C:/Users/ngdia/Documents/projet_agri/plateforme/web/node_modules/playwright');
(async () => {
  let b; try { b = await chromium.launch({channel:'chrome'}); } catch(e){ b = await chromium.launch(); }
  const p = await (await b.newContext({viewport:{width:1920,height:1080}})).newPage();
  await p.goto('http://localhost:3000/fr/login',{waitUntil:'networkidle'}); await p.waitForTimeout(2500);
  await p.fill('input[name=username]','agriculteur@demo.sn'); await p.fill('input[name=password]','demo');
  await p.click('button[type=submit]'); await p.waitForLoadState('networkidle'); await p.waitForTimeout(3000);
  await p.goto('http://localhost:3000/fr/assistant',{waitUntil:'networkidle'}); await p.waitForTimeout(5000);
  await p.locator('textarea').first().fill("Dois-je irriguer demain ?");
  await p.screenshot({path:'film/shots/farmer_assistant_q.png'});
  await p.getByRole('button',{name:'Envoyer'}).click(); await p.waitForTimeout(15000);
  await p.screenshot({path:'film/shots/farmer_assistant2.png'});
  await b.close(); console.log('done');
})().catch(e=>{console.error('FAIL',e.message);process.exit(1)});
