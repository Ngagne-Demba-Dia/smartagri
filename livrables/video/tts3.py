import asyncio, edge_tts
S = {
 "w1":"Côté agriculteur : le tableau de bord réunit la météo et le besoin en eau des prochaines vingt-quatre heures.",
 "w2":"Les parcelles, avec l'état de chaque culture.",
 "w3":"Les recommandations de l'IA disent quoi faire aujourd'hui.",
 "w4":"L'irrigation chiffre le besoin : trois virgule six millimètres, soit dix-sept mètres cubes d'eau.",
 "w5":"Côté agronome : une matrice de diagnostic par parcelle, avec la végétation NDVI, l'humidité et le pH.",
 "w6":"Le diagnostic IA détecte les maladies à partir des feuilles.",
 "w7":"Et des prévisions du sol à soixante-douze heures.",
 "w8":"Dois-je irriguer demain ? L'assistant répond en citant ses sources, et il comprend aussi le wolof.",
}
async def main():
    for k,t in S.items():
        await edge_tts.Communicate(t,"fr-FR-DeniseNeural",rate="+6%").save(f"film/audio/{k}.mp3")
asyncio.run(main())
