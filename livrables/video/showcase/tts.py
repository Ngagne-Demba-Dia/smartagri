import asyncio, edge_tts
L={"a1":"SmartAgri92 s'appuie sur un Data Lake agricole national et un écosystème complet d'intelligence artificielle.",
"a2":"Neuf modèles analysent les sols, le climat, les cultures, les marchés et les risques.",
"a3":"Les prédictions sont converties en recommandations directement utilisables sur le terrain.",
"a4":"Le moteur de connaissances explique les recommandations et fournit des réponses contextualisées.",
"a5":"Les agents surveillent les parcelles, détectent les anomalies et assistent les décisions agronomiques.",
"a6":"SmartAgri92 : l'intelligence artificielle au service de l'agriculture sénégalaise."}
async def m():
    for k,t in L.items():
        await edge_tts.Communicate(t,"fr-FR-DeniseNeural",rate="+34%").save(f"audio/{k}.mp3")
asyncio.run(m())

