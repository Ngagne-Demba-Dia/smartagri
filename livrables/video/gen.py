import subprocess, re
def dur(k): return float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",f"audio/{k}.mp3"]).decode())
PAD=0.18
# kind, voice, payload
sc=[("t","v1","problem"),("t","v2","chain"),("t","v3","roles"),
("s","w1","farmer_tableau|ESPACE AGRICULTEUR · TABLEAU DE BORD|211|1"),
("s","w2","farmer_parcelles|AGRICULTEUR · PARCELLES|295|1"),
("s","w3","farmer_recommandations|AGRICULTEUR · RECOMMANDATIONS IA|739|1"),
("s","w4","farmer_irrigation|AGRICULTEUR · IRRIGATION|877|1"),
("s","v4","farmer_meteo|AGRICULTEUR · MÉTÉO ET PRIORITÉS|0|0"),
("s","w5","agro_tableau|ESPACE AGRONOME · MATRICE AGRONOMIQUE|0|0"),
("s","w6","agro_maladies|AGRONOME · DIAGNOSTIC IA|878|1"),
("s","w7","agro_previsions|AGRONOME · PRÉVISIONS SOL 72 H|0|0"),
("s","v5","agro_recommandations|AGRONOME · RECOMMANDATIONS ET RISQUES|0|0"),
("t","v6","ai"),
("s","w8","farmer_assistant3|ASSISTANT IA · « DOIS-JE IRRIGUER DEMAIN ? »|831|1"),
("t","v8","impact"),("t","v9","end")]
T={"v1":"L’agriculteur doit décider chaque jour quand irriguer, comment protéger ses cultures et comment produire mieux avec moins d’eau.",
"v2":"SmartAgri92 transforme les données agricoles en décisions concrètes.",
"v3":"Quatre profils : agriculteur, coopérative, agronome et administrateur.",
"w1":"Côté agriculteur : la météo et le besoin en eau des prochaines heures.",
"w2":"Les parcelles, avec l’état de chaque culture.",
"w3":"Les recommandations de l’IA disent quoi faire aujourd’hui.",
"w4":"L’irrigation chiffre le besoin : 3,6 millimètres, soit 17 mètres cubes.",
"v4":"SmartAgri identifie les parcelles prioritaires et recommande les actions à réaliser aujourd’hui.",
"w5":"Côté agronome : une matrice de diagnostic par parcelle, avec NDVI, humidité et pH.",
"w6":"Le diagnostic IA détecte les maladies à partir des feuilles.",
"w7":"Et des prévisions du sol à soixante-douze heures.",
"v5":"L’agronome dispose d’une vision complète de la santé des cultures et des risques.",
"v6":"Derrière l’interface, des modèles entraînés : sol, pluie, base agronomique, et des agents IA.",
"w8":"Dois-je irriguer demain ? L’assistant répond avec ses sources, et comprend aussi le wolof.",
"v8":"SmartAgri92 transforme les données agricoles en décisions fiables, explicables et actionnables.",
"v9":"SmartAgri92. Agriculture intelligente pour le Sénégal."}
HTMLT={
"problem":'<div class="mid pp">Chaque jour, une décision</div><div class="big pp"><span class="amb">Irriguer ?</span> Protéger ? Produire&nbsp;mieux&nbsp;?</div><div class="sub pp">Changement climatique · eau rare · maladies · peu de données de terrain</div>',
"chain":'<div class="logo pp" style="font-size:96px;margin-bottom:60px">Smart<b>Agri</b>92</div><div class="row"><div class="node pp">Kit IoT<small>sol · météo · pompe</small></div><div class="arrow pp">→</div><div class="node pp">Données<small>plateforme sécurisée</small></div><div class="arrow pp">→</div><div class="node pp">IA<small>prévisions · assistant</small></div><div class="arrow pp">→</div><div class="node pp" style="background:rgba(244,185,66,.16);border-color:var(--amber)">Décision<small>claire et concrète</small></div></div>',
"roles":'<div class="mid pp" style="margin-bottom:60px">Quatre profils, une seule plateforme</div><div class="row"><div class="chip demo pp">Agriculteur</div><div class="chip pp">Gestionnaire de coopérative</div><div class="chip demo pp">Agronome</div><div class="chip pp">Administrateur</div></div><div class="sub pp">Démonstration : agriculteur et agronome</div>',
"ai":'<div class="mid pp" style="margin-bottom:50px">L’IA SmartAgri</div><div class="row" style="flex-wrap:wrap;max-width:1700px"><div class="node pp" style="width:310px">SoilNowcast<small>humidité du sol · R² 0,84</small></div><div class="node pp" style="width:310px">Rain Intelligence<small>pluie · AUC 0,96</small></div><div class="node pp" style="width:310px">SmartAgri Knowledge<small>535 fiches agronomiques</small></div><div class="node pp" style="width:310px">Agents IA<small>surveillance · irrigation</small></div></div><div class="sub amb pp">30 millions de lignes de données</div>',
"impact":'<div class="mid pp" style="margin-bottom:50px">Un impact pour tout l’écosystème</div><div class="row"><div class="chip pp">Exploitations</div><div class="chip pp">Coopératives</div><div class="chip pp">Agronomes</div><div class="chip pp">Kits IoT</div></div><div class="sub pp">Des décisions fiables, explicables, actionnables</div>',
"end":'<div class="logo pp">Smart<b>Agri</b>92</div><div class="mid pp" style="margin-top:30px"><span class="acc">Agriculture Intelligente</span> pour le Sénégal</div>'}
t=0.0; scenes=[]
for k,(kind,v,p) in enumerate(sc):
    d=dur(v); L=d+PAD+(0.3 if k==0 else 0)+(0.6 if v=="v9" else 0)
    scenes.append((k,kind,v,p,t,round(L,2),round(t+0.25,2),round(d,2))); t+=L
D=round(t,1)
print("TOTAL",D)
S="";SUB="";AUD="";JS=""
for k,kind,v,p,s,L,vs,d in scenes:
    if kind=="t":
        S+=f'      <div id="sc{k}" class="scene center clip" data-start="{s}" data-duration="{L}" data-track-index="1">{HTMLT[p]}</div>\n'
        JS+=f'      pops("#sc{k}", {s}, {L});\n'
    else:
        im,tag,sy,click=p.split("|")
        S+=f'      <div id="sc{k}" class="scene clip" data-start="{s}" data-duration="{L}" data-track-index="1"><div class="tag">{tag}</div><div class="screen"><img id="im{k}" src="shots/{im}.png" /></div></div>\n'
        JS+=f'      screen("#sc{k}", "#im{k}", {s}, {L});\n'
        if click=="1":
            cx,cy=round(140+110*0.854),round(90+int(sy)*0.854)
            JS+=f'      clickAt({s}, {cx}, {cy}, {k});\n'
            AUD+=f'      <audio src="audio/click.mp3" data-start="{round(s+1.5,2)}" data-duration="0.1" data-track-index="{60+k}" data-volume="0.8"></audio>\n'
    SUB+=f'      <div class="sub-line" id="t{k}"><span>{T[v]}</span></div>\n'
    JS+=f'      cap("#t{k}", {vs}, {d});\n'
    AUD+=f'      <audio src="audio/{v}.mp3" data-start="{vs}" data-duration="{round(d+0.05,2)}" data-track-index="{21+k}" data-volume="1"></audio>\n'
    if k>0: AUD+=f'      <audio src="audio/whoosh.mp3" data-start="{round(s-0.35,2)}" data-duration="0.9" data-track-index="{80+k}" data-volume="0.45"></audio>\n'
RP="".join(f'      <div class="ripple" id="rp{k}"></div>\n' for k,kind,v,p,*_ in scenes if kind=="s" and p.endswith("|1"))
head=open("index.html",encoding="utf-8").read().split("<body>")[0]
body=f'''<body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{D}" data-width="1920" data-height="1080">
{S}      <svg id="cursor" viewBox="0 0 24 24"><path d="M3 2l7 19 3-8 8-3z" fill="#fff" stroke="#111" stroke-width="1.5" stroke-linejoin="round"/></svg>
{RP}{SUB}      <audio id="mus" src="audio/music_long.mp3" data-start="0" data-duration="{D}" data-track-index="20" data-volume="0.4" data-fade-in="2" data-fade-out="4"></audio>
{AUD}    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
      const IN = 0.45, OUT = 0.4;
      function fade(id, s, d) {{
        tl.fromTo(id, {{ opacity: 0 }}, {{ opacity: 1, duration: IN, ease: "power2.out" }}, s);
        tl.to(id, {{ opacity: 0, duration: OUT, ease: "power2.in" }}, s + d - OUT);
      }}
      function cap(id, s, d) {{
        tl.fromTo(id, {{ opacity: 0, y: 14 }}, {{ opacity: 1, y: 0, duration: 0.4, ease: "power2.out" }}, s);
        tl.to(id, {{ opacity: 0, duration: 0.3 }}, s + d - 0.1);
      }}
      function pops(sc, s, d) {{
        fade(sc, s, d);
        const n = document.querySelectorAll(sc + " .pp").length;
        document.querySelectorAll(sc + " .pp").forEach((el, i) =>
          tl.fromTo(el, {{ opacity: 0.0, y: 36, scale: 0.94 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.55, ease: "back.out(1.3)" }}, s + 0.3 + i * Math.min(0.9, (d - 2) / n)));
      }}
      function screen(sc, im, s, d) {{
        fade(sc, s, d);
        tl.fromTo(im, {{ scale: 1.0, transformOrigin: "50% 50%" }}, {{ scale: 1.07, duration: d, ease: "none" }}, s);
      }}
      function clickAt(s, x, y, k) {{
        tl.set("#cursor", {{ x: 1300, y: 250, opacity: 0 }}, s);
        tl.to("#cursor", {{ opacity: 1, duration: 0.3 }}, s + 0.5);
        tl.to("#cursor", {{ x: x, y: y, duration: 0.9, ease: "power2.inOut" }}, s + 0.6);
        tl.set("#rp" + k, {{ x: x, y: y, scale: 0.3, opacity: 0 }}, 0);\n        tl.fromTo("#rp" + k, {{ x: x, y: y, scale: 0.3, opacity: 0.9 }}, {{ scale: 1.6, opacity: 0, duration: 0.6, immediateRender: false }}, s + 1.5);
        tl.to("#cursor", {{ opacity: 0, duration: 0.4 }}, s + 2.3);
      }}
{JS}      tl.to("#root", {{ opacity: 0, duration: 0.8 }}, {D-0.9});
      window.__timelines["main"] = tl;
      tl.seek(0);
    </script>
  </body>
</html>
'''
open("index.html","w",encoding="utf-8").write(head+body)


