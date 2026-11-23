import asyncio, edge_tts
S = {
 "v1":"L'agriculteur doit décider chaque jour quand irriguer, comment protéger ses cultures et comment produire mieux avec moins d'eau.",
 "v2":"SmartAgri92 transforme les données agricoles en décisions concrètes. Du kit de capteurs jusqu'à l'intelligence artificielle.",
 "v3":"Quatre profils utilisent la plateforme : l'agriculteur, le gestionnaire de coopérative, l'agronome et l'administrateur.",
 "v4":"Pour l'agriculteur, SmartAgri identifie les parcelles prioritaires et recommande les actions à réaliser aujourd'hui.",
 "v5":"L'agronome dispose d'une vision complète de la santé des cultures et des risques.",
 "v6":"Derrière l'interface, des modèles réellement entraînés : humidité du sol, pluie, base de connaissances agronomiques, et des agents de surveillance et d'irrigation.",
 "v7":"L'assistant répond à la question de l'agriculteur, et cite ses sources.",
 "v8":"SmartAgri92 transforme les données agricoles en décisions fiables, explicables et actionnables.",
 "v9":"SmartAgri92. Agriculture intelligente pour le Sénégal.",
}
async def main():
    for k,t in S.items():
        await edge_tts.Communicate(t,"fr-FR-DeniseNeural",rate="+6%").save(f"film/audio/{k}.mp3")
asyncio.run(main())
