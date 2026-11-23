import re
S=[0,5.7,10.3,14.6,19.2,24.1,30.0]
V=[0.1,5.8,10.4,14.7,19.3,24.2]
SUB=["SmartAgri92 s'appuie sur un Data Lake agricole national et un écosystème complet d'intelligence artificielle.",
"Neuf modèles analysent les sols, le climat, les cultures, les marchés et les risques.",
"Les prédictions sont converties en recommandations directement utilisables sur le terrain.",
"Le moteur de connaissances explique les recommandations et fournit des réponses contextualisées.",
"Les agents surveillent les parcelles, détectent les anomalies et assistent les décisions agronomiques.",
"SmartAgri92 : l'intelligence artificielle au service de l'agriculture sénégalaise."]
M=[("SoilNowcast","LightGBM · R² 0,84"),("ET0 Forecast","CatBoost · R² 0,9997"),("Yield Forecast","CatBoost · R² 0,95"),
("Rain Intelligence","CatBoost · AUC 0,96"),("Price Forecast","XGBoost · R² 0,90"),("Crop Calendar","Précision 98 %"),
("NDVI Anomaly","Précision 99,8 %"),("Anomaly Intelligence","One-Class SVM"),("Market Intelligence","KMeans · 7 clusters")]
def clip(i,inner,cls=""):
    return f'<div id="sc{i}" class="clip scene {cls}" data-start="{S[i]}" data-duration="{round(S[i+1]-S[i]+0.0,2)}" data-track-index="{i+1}">{inner}</div>'
logo='<div class="logo"><div class="mark">S92</div><div class="lt">SmartAgri<span class="acc">92</span></div></div>'
s0=clip(0,f'<div class="center full">{logo}<div class="stats"><div class="stat" id="st1"><b>30 M</b><span>lignes de données</span></div><div class="stat" id="st2"><b>28</b><span>datasets</span></div><div class="stat" id="st3"><b>Sénégal</b><span>14 régions</span></div></div><div class="tag" id="tag0">Data Lake agricole national · OCTOPUS-PACK-01</div></div>')
cards="".join(f'<div class="card" id="m{k}"><div class="cn">{n}</div><div class="cm">{m}</div></div>' for k,(n,m) in enumerate(M))
s1=clip(1,f'<div class="head">9 modèles IA</div><div class="grid">{cards}</div>')
s2=clip(2,'''<div class="head">Du Data Lake à la décision</div><div class="flow">
<div class="node" id="f0">Données</div><div class="arr" id="a0">→</div><div class="node" id="f1">Modèles</div><div class="arr" id="a1">→</div><div class="node" id="f2">Agents</div><div class="arr" id="a2">→</div><div class="node dec" id="f3">Décision</div></div>
<div class="chips"><div class="chip" id="c0">SoilNowcast</div><div class="chip" id="c1">Rain Intelligence</div><div class="chip" id="c2">Monitoring</div><div class="chip" id="c3">Irrigation</div></div>''')
s3=clip(3,'''<div class="two"><div class="pills"><div class="pill" id="p0">SmartAgri Knowledge</div><div class="pill" id="p1">Assistant IA</div><div class="pill" id="p2">Copilot</div><div class="pill" id="p3">Knowledge Graph</div></div>
<div class="chat"><div class="q" id="q">Dois-je irriguer demain ?</div><div class="ans" id="an1"><b>Explication</b> · bilan hydrique FAO-56, ET0, pluie prévue.</div><div class="ans rec" id="an2"><b>Recommandation</b> · irriguer selon le déficit.</div></div></div>''')
s4=clip(4,'''<div class="head">Agents IA collaboratifs</div><svg class="lines" viewBox="0 0 1920 1080"><line id="l1" x1="600" y1="545" x2="720" y2="545"/><line id="l2" x1="1200" y1="545" x2="1320" y2="545"/></svg>
<div class="agent" id="g1" style="left:120px;top:420px"><b>Monitoring Agent</b><span>Surveille les parcelles · détecte les anomalies</span></div>
<div class="agent orch" id="g0" style="left:720px;top:420px"><b>Orchestrator</b><span>Coordonne et escalade</span></div>
<div class="agent" id="g2" style="left:1320px;top:420px"><b>Irrigation Agent</b><span>Assiste les décisions agronomiques</span></div>''')
s5=clip(5,f'<div class="center full">{logo}<div class="big2" id="t1">Agri-Moderne 5.0</div><div class="tag" id="t2">PAS Challenge 2026</div></div>')
subs="".join(f'<div id="sub{i}" class="clip sub" data-start="{V[i]}" data-duration="{round(S[i+1]-V[i]-0.05,2)}" data-track-index="30">{t}</div>' for i,t in enumerate(SUB))
aud=f'<audio id="mus" src="audio/music.mp3" data-start="0" data-duration="30" data-track-index="40" data-volume="0.3"></audio>'
aud+="".join(f'<audio id="vo{i}" src="audio/a{i+1}.mp3" data-start="{V[i]}" data-duration="5.7" data-track-index="{41+i}" data-volume="1"></audio>' for i in range(6))
aud+="".join(f'<audio id="wh{i}" src="audio/whoosh.mp3" data-start="{max(S[i]-0.1,0)}" data-duration="0.9" data-track-index="{50+i}" data-volume="0.4"></audio>' for i in range(1,6))
css='''*{margin:0;padding:0;box-sizing:border-box}html,body{width:1920px;height:1080px;overflow:hidden;background:#06160f}
#root{position:relative;width:1920px;height:1080px;font-family:"Segoe UI",Arial,sans-serif;color:#f4fbf5;background:radial-gradient(1200px 800px at 70% 20%,#0e3a29,#06160f);overflow:hidden}
.scene{position:absolute;inset:0}.acc{color:#7ddc8a}.center{display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}.full{position:absolute;inset:0}
.logo{display:flex;align-items:center;gap:28px;margin-bottom:60px}.mark{width:130px;height:130px;border-radius:32px;background:#7ddc8a;color:#06160f;font-size:52px;font-weight:800;display:flex;align-items:center;justify-content:center}
.lt{font-size:120px;font-weight:700;letter-spacing:-.03em}
.stats{display:flex;gap:50px}.stat{background:rgba(125,220,138,.1);border:2px solid rgba(125,220,138,.4);border-radius:28px;padding:30px 54px}.stat b{display:block;font-size:84px;color:#7ddc8a}.stat span{font-size:34px;color:#b8dcc3}
.tag{margin-top:50px;font-size:38px;color:#f4b942;font-weight:600;letter-spacing:.04em}.big2{font-size:96px;font-weight:700}
.head{position:absolute;top:70px;left:0;right:0;text-align:center;font-size:64px;font-weight:700}
.grid{position:absolute;top:190px;left:110px;display:grid;grid-template-columns:repeat(3,550px);gap:26px 30px}
.card{height:220px;border-radius:26px;background:rgba(125,220,138,.09);border:2px solid rgba(125,220,138,.4);display:flex;flex-direction:column;justify-content:center;padding:0 36px}
.cn{font-size:42px;font-weight:700}.cm{font-size:30px;color:#9fd0ae;margin-top:10px}
.flow{position:absolute;top:330px;left:0;right:0;display:flex;justify-content:center;align-items:center;gap:30px}
.node{width:340px;height:170px;border-radius:30px;background:rgba(125,220,138,.1);border:3px solid #7ddc8a;font-size:54px;font-weight:700;display:flex;align-items:center;justify-content:center}
.node.dec{background:#7ddc8a;color:#06160f}.arr{font-size:80px;color:#f4b942}
.chips{position:absolute;top:620px;left:0;right:0;display:flex;justify-content:center;gap:34px}
.chip{font-size:40px;font-weight:600;padding:20px 44px;border-radius:60px;background:#f4b942;color:#06160f}
.two{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;gap:90px}
.pills{display:flex;flex-direction:column;gap:30px}.pill{font-size:50px;font-weight:700;padding:26px 54px;border-radius:26px;border:3px solid #7ddc8a;background:rgba(125,220,138,.1);width:620px}
.chat{width:900px;display:flex;flex-direction:column;gap:26px}.q{align-self:flex-end;font-size:46px;font-weight:600;background:#7ddc8a;color:#06160f;padding:24px 40px;border-radius:30px}
.ans{font-size:36px;line-height:1.35;background:rgba(255,255,255,.08);border-radius:28px;padding:30px 38px}.ans b{color:#7ddc8a}.rec{border:3px solid #f4b942}.rec b{color:#f4b942}
.lines line{stroke:#7ddc8a;stroke-width:5;stroke-dasharray:14 12}.lines{position:absolute;inset:0;width:1920px;height:1080px}
.agent{position:absolute;width:480px;height:250px;border-radius:30px;background:rgba(125,220,138,.1);border:3px solid #7ddc8a;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;padding:0 24px;gap:12px}
.agent b{font-size:46px}.agent span{font-size:30px;color:#b8dcc3}.orch{background:#7ddc8a;color:#06160f}.orch span{color:#0d3322}
.sub{position:absolute;left:160px;right:160px;bottom:56px;text-align:center;font-size:40px;font-weight:600;line-height:1.25;background:rgba(0,0,0,.6);border-radius:18px;padding:14px 30px;z-index:50}'''
js='''window.__timelines=window.__timelines||{};const tl=gsap.timeline({paused:true});
const E=(i,t)=>{tl.fromTo(i,{opacity:0,y:40},{opacity:1,y:0,duration:.5,ease:"power3.out",immediateRender:false},t)};
tl.from(".logo",{scale:.85,duration:.8,ease:"back.out(1.6)"},0);
["#st1","#st2","#st3"].forEach((s,k)=>tl.from(s,{opacity:0,y:50,duration:.5,ease:"power3.out"},1.3+k*.5));
tl.from("#tag0",{opacity:0,duration:.5},3.2);
for(let k=0;k<9;k++)tl.from("#m"+k,{opacity:0,scale:.8,duration:.35,ease:"back.out(1.4)"},5.8+k*.42);
["#f0","#a0","#f1","#a1","#f2","#a2","#f3"].forEach((s,k)=>tl.from(s,{opacity:0,x:-40,duration:.4,ease:"power3.out"},10.5+k*.22));
["#c0","#c1","#c2","#c3"].forEach((s,k)=>tl.from(s,{opacity:0,y:40,scale:.9,duration:.4,ease:"back.out(1.5)"},12.2+k*.4));
tl.to(["#f1","#f2"],{scale:1.06,duration:.4,yoyo:true,repeat:1},13.0);
["#p0","#p1","#p2","#p3"].forEach((s,k)=>tl.from(s,{opacity:0,x:-80,duration:.4,ease:"power3.out"},14.8+k*.3));
tl.from("#q",{opacity:0,y:30,duration:.4},15.4);tl.from("#an1",{opacity:0,y:30,duration:.5},16.0);tl.from("#an2",{opacity:0,y:30,duration:.5},17.0);
tl.from("#g0",{opacity:0,scale:.8,duration:.5,ease:"back.out(1.5)"},19.5);
tl.from(["#l1","#l2"],{opacity:0,duration:.4},20.2);
tl.from("#g1",{opacity:0,x:-80,duration:.5},20.5);tl.from("#g2",{opacity:0,x:80,duration:.5},21.3);
tl.to(["#g1","#g2","#g0"],{scale:1.05,duration:.35,yoyo:true,repeat:1,stagger:.5},22.4);
tl.from("#t1",{opacity:0,y:40,duration:.6},25.3);tl.from("#t2",{opacity:0,y:30,duration:.6},26.3);
document.querySelectorAll(".sub").forEach(s=>{});
for(let i=0;i<6;i++)tl.from("#sub"+i,{opacity:0,y:16,duration:.25},[0.1,5.8,10.4,14.7,19.3,24.2][i]);
window.__timelines["main"]=tl;'''
html=f'<!doctype html><html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=1920, height=1080"><title>SmartAgri92 AI Engine Showcase</title><script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script><style>{css}</style></head><body><div id="root" data-composition-id="main" data-start="0" data-duration="30" data-width="1920" data-height="1080">{s0}{s1}{s2}{s3}{s4}{s5}{subs}{aud}</div><script>{js}</script></body></html>'
open("index.html","w",encoding="utf-8").write(html)
