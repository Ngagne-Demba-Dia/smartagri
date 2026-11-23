import asyncio, edge_tts
S = {
 "s1":"Dans les Niayes, au Sénégal, un maraîcher irrigue souvent à l'intuition. Trop d'eau, trop d'engrais, et des récoltes qui souffrent.",
 "s2":"SmartAgri92 relie un kit de capteurs posé dans le champ, une intelligence artificielle, et une plateforme web.",
 "s3":"La plateforme s'adapte à quatre profils : agriculteur, coopérative, agronome et administrateur.",
 "s4":"L'agriculteur voit d'un coup d'œil la météo et le besoin en eau de sa parcelle, en millimètres et en mètres cubes.",
 "s5":"Il pose sa question à l'assistant, qui répond à partir de fiches agronomiques, et cite sa source.",
 "s6":"L'agronome suit les recommandations, le risque de maladies et les prévisions, parcelle par parcelle.",
 "s7":"SmartAgri92. Mesurer, prévoir, conseiller. Pour une agriculture plus sobre en eau.",
}
async def main():
    for k,t in S.items():
        await edge_tts.Communicate(t,"fr-FR-DeniseNeural",rate="+4%").save(f"film/audio/{k}.mp3")
asyncio.run(main())
