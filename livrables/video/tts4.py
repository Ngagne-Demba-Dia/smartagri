import asyncio, edge_tts
S = {
 "v2":"SmartAgri92 transforme les données agricoles en décisions concrètes.",
 "v3":"Quatre profils : agriculteur, coopérative, agronome et administrateur.",
 "w1":"Côté agriculteur : la météo et le besoin en eau des prochaines heures.",
 "w4":"L'irrigation chiffre le besoin : trois virgule six millimètres, soit dix-sept mètres cubes.",
 "w5":"Côté agronome : une matrice de diagnostic par parcelle, avec NDVI, humidité et pH.",
 "v6":"Derrière l'interface, des modèles entraînés : sol, pluie, base agronomique, et des agents IA.",
 "w8":"Dois-je irriguer demain ? L'assistant répond avec ses sources, et comprend aussi le wolof.",
}
async def main():
    for k,t in S.items():
        await edge_tts.Communicate(t,"fr-FR-DeniseNeural",rate="+6%").save(f"film/audio/{k}.mp3")
asyncio.run(main())
