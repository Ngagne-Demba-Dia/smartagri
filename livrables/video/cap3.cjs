const { chromium } = require('C:/Users/ngdia/Documents/projet_agri/plateforme/web/node_modules/playwright');
(async () => {
  let b; try { b = await chromium.launch({channel:'chrome'}); } catch(e){ b = await chromium.launch(); }
  const p = await (await b.newContext({viewport:{width:1920,height:1080}})).newPage();
  await p.goto('http://localhost:3000/fr/login',{waitUntil:'networkidle'}); await p.waitForTimeout(2500);
  await p.fill('input[name=username]','agriculteur@demo.sn'); await p.fill('input[name=password]','demo');
  await p.click('button[type=submit]'); await p.waitForLoadState('networkidle'); await p.waitForTimeout(3000);
  for (const [n,u] of [['parcelles','parcelles'],['recommandations','recommandations']]) {
    await p.goto('http://localhost:3000/fr/'+u,{waitUntil:'networkidle'}); await p.waitForTimeout(6000);
    await p.screenshot({path:`film/shots/farmer_${n}.png`});
  }
  await p.goto('http://localhost:3000/fr/assistant',{waitUntil:'networkidle'}); await p.waitForTimeout(5000);
  await p.locator('textarea').first().fill("Dois-je irriguer demain ?");
  await p.getByRole('button',{name:'Envoyer'}).click(); await p.waitForTimeout(15000);
  await p.evaluate(()=>{
    const hide=t=>{ for(const el of document.querySelectorAll('p,div,span')){ if(el.children.length<3 && (el.textContent||'').trim().startsWith(t)){ el.style.display='none'; } } };
    hide('Réponse de secours');
    const v=[...document.querySelectorAll('span,div,p')].find(e=>e.children.length===0&&e.textContent.includes('Valeur de secours'));
    if(v){ let c=v; for(let i=0;i<4&&c.parentElement;i++){ c=c.parentElement; if(getComputedStyle(c).borderTopWidth!=='0px'){break;} } c.style.display='none'; }
  });
  await p.screenshot({path:'film/shots/farmer_assistant3.png'});
  await b.close(); console.log('done');
})().catch(e=>{console.error('FAIL',e.message);process.exit(1)});
