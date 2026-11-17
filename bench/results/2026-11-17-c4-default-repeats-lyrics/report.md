# Banco · c4-default · repeats · con letra

- Fecha: 2026-11-17T11:16:22+01:00
- Commit: a85e232-dirty
- Banco 3.0.0, normalización v1
- Referencias: de manual, en manual, es manual, fr manual

## Entorno

| Clave | Valor |
|---|---|
| ctranslate2 | 4.8.5 |
| demucs | 4.0.1 |
| driver | 617.42 |
| faster-whisper | 1.2.1 |
| gpu | NVIDIA GeForce RTX 3050 Laptop GPU |
| gpu_memory_mb | 4096 |
| jiwer | 4.0.0 |
| numpy | 2.5.4 |
| platform | Linux-6.6.114.1-microsoft-standard-WSL2-x86_64-with-glibc2.43 |
| python | 3.12.16 |
| torch | 2.14.1+cu130 |
| transformers | 5.22.1 |

## Pipeline

Mel-Band RoFormer (Kim, 8 s) + Whisper by stretches of singing (HiTZ large-v3 for Galician, large-v3-turbo otherwise) + lyrics aligner (each language's CTC model with the music model as a second listener)

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt', 'segment_size': 801}
- **transcriber**: `karaoke_engine.transcribe:WhisperTranscriber` v6
- **segmenter**: `karaoke_engine.transcribe:LineSegmenter` v2
- **aligner**: `karaoke_engine.align.aligner:LyricsAligner` v16

## Resumen

| Grupo | Canciones | Fallos | WER | WER tolerante | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| repeats-marked | 44 | 0 | — | — | — | 0.034 | 0.080 | 98.6 % | 98.8 % | 0.081 | 0.025 | 90.9 % | — | 0 | 76 | 0.0 % | 22.8 % |
| repeats-unmarked | 44 | 0 | — | — | — | 0.034 | 0.159 | 97.6 % | 97.8 % | 0.082 | 0.034 | 89.5 % | — | 0 | 70 | 0.0 % | 21.8 % |
| total | 88 | 0 | — | — | — | 0.034 | 0.119 | 98.1 % | 98.3 % | 0.082 | 0.030 | 90.2 % | — | 0 | 71 | 0.0 % | 22.3 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 7.2 | 2867 | 2388 | 0.205 |
| aligner | 0.1 | 2133 | 4158 | 0.061 |

## Por canción

| Canción | Idioma | Duración | WER | WER tolerante | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| marked-10._Disparan_-_criatura | es | 160 | — | — | 0.024 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 22.7 % | — | 44.1 |  |
| marked-1_Freak_-_Automatisch_Gekommen | de | 188 | — | — | 0.044 | 100.0 % | 100.0 % | 96.7 % | manual | 0.0 % | 21.3 % | — | 59.8 |  |
| marked-Besando_Sapos_-_Dream_Tabu | es | 251 | — | — | 0.031 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 19.3 % | — | 65.3 |  |
| marked-Bitte_beweg_dich_nicht_-_Bukto | de | 273 | — | — | 0.036 | 100.0 % | 100.0 % | 98.9 % | manual | 0.0 % | 21.8 % | — | 85.4 |  |
| marked-Burn_Out_Man_-_Abendblau | de | 260 | — | — | 0.039 | 100.0 % | 100.0 % | 86.7 % | manual | 0.0 % | 6.4 % | — | 71.3 |  |
| marked-CHRISTMAS_AVEC_TOI_-_imfreshyourepretty | fr | 234 | — | — | 0.035 | 99.6 % | 99.6 % | 64.3 % | manual | 0.0 % | 41.0 % | — | 74.5 |  |
| marked-CLUB_DESTINO__-_Pensando_en_ti_-_CLUB_DESTINO | es | 219 | — | — | 0.037 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 10.7 % | — | 60.2 |  |
| marked-Confession_-_Quesabe | fr | 148 | — | — | 0.029 | 99.3 % | 99.3 % | 87.2 % | manual | 0.2 % | 28.5 % | — | 43.5 |  |
| marked-Cortez_-_Feel__Stripped_ | en | 241 | — | — | 0.067 | 100.0 % | 100.0 % | 98.9 % | manual | 0.0 % | 12.4 % | — | 70.3 |  |
| marked-Culture_&_Co._-_cool.cavemen | fr | 212 | — | — | 0.032 | 98.4 % | 99.2 % | 93.9 % | manual | 0.0 % | 62.3 % | — | 55.1 |  |
| marked-DON_VALDES_-_Tu_sais_Man | fr | 209 | — | — | 0.027 | 97.3 % | 97.5 % | 79.8 % | manual | 0.0 % | 42.0 % | — | 55.7 |  |
| marked-Der_Baum_-_Dienstag_is_Damensauna_(2) | de | 209 | — | — | 0.027 | 99.5 % | 99.5 % | 95.5 % | manual | 0.0 % | 10.6 % | — | 58.1 |  |
| marked-Die_Revolution_gehört_Dir!_-_partysahnen | de | 167 | — | — | 0.030 | 93.8 % | 93.8 % | 93.6 % | manual | 0.0 % | 42.4 % | — | 45.8 |  |
| marked-Drei_Nüsse_-_patrouille | de | 259 | — | — | 0.026 | 100.0 % | 100.0 % | 98.5 % | manual | 0.0 % | 4.6 % | — | 76.1 |  |
| marked-Esencia_-_NandoMalo_ | es | 262 | — | — | 0.023 | 100.0 % | 100.0 % | 98.2 % | manual | 0.0 % | 18.0 % | — | 87.6 |  |
| marked-Explosive_Ear_Candy_-_Like_The_Sun | en | 193 | — | — | 0.049 | 100.0 % | 100.0 % | 99.6 % | manual | 0.4 % | 25.0 % | — | 57.5 |  |
| marked-Fantasma_-_Los_Rombos | es | 166 | — | — | 0.050 | 93.6 % | 97.4 % | 88.6 % | manual | 0.4 % | 25.8 % | — | 46.0 |  |
| marked-Fußabdrücke_-_Andreas_Jachmann | de | 241 | — | — | 0.023 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 1.3 % | — | 66.2 |  |
| marked-Guayeteo_-_JhoyKing | es | 158 | — | — | 0.027 | 99.7 % | 100.0 % | 84.7 % | manual | 0.0 % | 21.7 % | — | 46.6 |  |
| marked-Intentando_Destacar_-_Sundayers_ | es | 220 | — | — | 0.023 | 100.0 % | 100.0 % | 80.8 % | manual | 0.0 % | 18.8 % | — | 59.4 |  |
| marked-Keine_Lust_-_Jonny_M | de | 229 | — | — | 0.016 | 100.0 % | 100.0 % | 95.8 % | manual | 0.0 % | 4.4 % | — | 73.6 |  |
| marked-LUNABLIND_-_Vision__Radio_Edit_ | en | 221 | — | — | 0.064 | 99.3 % | 99.3 % | 99.7 % | manual | 0.0 % | 11.5 % | — | 69.1 |  |
| marked-La_rumba_del_coronavirus_-_Rich_Don_Jeri | es | 187 | — | — | 0.028 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 4.9 % | — | 58.3 |  |
| marked-Les_files_d'attente_-_Law' | fr | 196 | — | — | 0.030 | 99.5 % | 99.5 % | 66.5 % | manual | 0.0 % | 28.8 % | — | 53.4 |  |
| marked-Libre_by_CybeR_AttaCK_-_CyberAttacK | fr | 217 | — | — | 0.029 | 99.0 % | 99.7 % | 96.5 % | manual | 0.0 % | 34.9 % | — | 67.3 |  |
| marked-Lower_Loveday_-_Is_It_Right_ | en | 180 | — | — | 0.057 | 99.5 % | 99.5 % | 96.7 % | manual | 0.0 % | 17.0 % | — | 50.9 |  |
| marked-Mes_Larmes_-_kobzx2z | fr | 159 | — | — | 0.023 | 98.0 % | 98.4 % | 63.7 % | manual | 0.0 % | 39.0 % | — | 53.4 |  |
| marked-Moon_I_Mean_-_Wrong_Concept | en | 220 | — | — | 0.052 | 99.6 % | 99.6 % | 95.2 % | manual | 0.0 % | 54.5 % | — | 61.3 |  |
| marked-Mère_nature_-_Law' | fr | 225 | — | — | 0.037 | 100.0 % | 100.0 % | 96.5 % | manual | 0.0 % | 13.9 % | — | 61.0 |  |
| marked-Palabras_-_Javier_Gomez_Bello | es | 216 | — | — | 0.031 | 100.0 % | 100.0 % | 99.5 % | manual | 0.0 % | 4.2 % | — | 62.8 |  |
| marked-Pluie_d'entre_deux_saisons_-_Midnight_Prefou | fr | 205 | — | — | 0.044 | 95.9 % | 95.9 % | 91.0 % | manual | 0.0 % | 28.5 % | — | 58.9 |  |
| marked-Pure_Mids_-_The_Leader | en | 262 | — | — | 0.077 | 100.0 % | 100.0 % | 71.9 % | manual | 0.6 % | 78.4 % | — | 68.5 |  |
| marked-Quentin_Hannappe_-_Keep_On | en | 190 | — | — | 0.044 | 100.0 % | 100.0 % | 96.0 % | manual | 0.0 % | 23.6 % | — | 55.1 |  |
| marked-Ridgway_-_Fire_Inside | en | 284 | — | — | 0.047 | 91.7 % | 92.1 % | 75.0 % | manual | 0.0 % | 34.0 % | — | 83.6 |  |
| marked-Rxbyn_-_Bad_Side | en | 217 | — | — | 0.053 | 99.3 % | 99.3 % | 95.2 % | manual | 0.0 % | 22.3 % | — | 60.0 |  |
| marked-Schnodderdodder_-_Abendblau | de | 197 | — | — | 0.022 | 99.3 % | 100.0 % | 95.9 % | manual | 0.0 % | 14.0 % | — | 58.0 |  |
| marked-Slingshot_Miracle_-_Whistler | en | 229 | — | — | 0.067 | 99.4 % | 100.0 % | 98.8 % | manual | 0.0 % | 25.2 % | — | 59.4 |  |
| marked-Séculaire_feat._Nÿme_-_saru | fr | 159 | — | — | 0.024 | 97.4 % | 97.4 % | 88.1 % | manual | 0.1 % | 23.0 % | — | 44.2 |  |
| marked-Vente_-_Fafarulo_Calabaza | es | 336 | — | — | 0.033 | 99.6 % | 99.6 % | 97.8 % | manual | 0.0 % | 9.2 % | — | 92.9 |  |
| marked-Wordsmith_-_The_Statement | en | 171 | — | — | 0.060 | 85.0 % | 85.0 % | 80.6 % | manual | 0.0 % | 29.4 % | — | 70.2 |  |
| marked-Yuanan_-_Miedo_-_Yuanan | es | 169 | — | — | 0.027 | 100.0 % | 100.0 % | 91.0 % | manual | 0.0 % | 11.4 % | — | 48.7 |  |
| marked-de_bonne_humeur_-_Le_Nez_Tordu | fr | 161 | — | — | 0.030 | 99.6 % | 100.0 % | 97.0 % | manual | 0.0 % | 14.9 % | — | 46.2 |  |
| marked-dich_gehen_zu_sehn._-_Wingenbach_Frank | de | 193 | — | — | 0.030 | 98.9 % | 100.0 % | 97.8 % | manual | 0.0 % | 11.5 % | — | 51.7 |  |
| marked-¡Óyeme_tiburón!_-_Corrientes | es | 180 | — | — | 0.028 | 100.0 % | 100.0 % | 98.1 % | manual | 0.0 % | 6.2 % | — | 59.2 |  |
| unmarked-10._Disparan_-_criatura | es | 160 | — | — | 0.024 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 22.7 % | — | 41.3 |  |
| unmarked-1_Freak_-_Automatisch_Gekommen | de | 188 | — | — | 0.044 | 100.0 % | 100.0 % | 96.7 % | manual | 0.0 % | 21.3 % | — | 50.0 |  |
| unmarked-Besando_Sapos_-_Dream_Tabu | es | 251 | — | — | 0.032 | 100.0 % | 100.0 % | 98.2 % | manual | 0.0 % | 18.8 % | — | 64.7 |  |
| unmarked-Bitte_beweg_dich_nicht_-_Bukto | de | 273 | — | — | 0.038 | 99.7 % | 99.7 % | 96.6 % | manual | 0.0 % | 20.3 % | — | 71.3 |  |
| unmarked-Burn_Out_Man_-_Abendblau | de | 260 | — | — | 0.039 | 100.0 % | 100.0 % | 86.7 % | manual | 0.0 % | 6.1 % | — | 67.1 |  |
| unmarked-CHRISTMAS_AVEC_TOI_-_imfreshyourepretty | fr | 234 | — | — | 0.035 | 94.0 % | 94.0 % | 62.0 % | manual | 0.0 % | 38.8 % | — | 61.2 |  |
| unmarked-CLUB_DESTINO__-_Pensando_en_ti_-_CLUB_DESTINO | es | 219 | — | — | 0.037 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 10.7 % | — | 56.1 |  |
| unmarked-Confession_-_Quesabe | fr | 148 | — | — | 0.029 | 99.3 % | 99.3 % | 87.2 % | manual | 0.2 % | 28.2 % | — | 38.8 |  |
| unmarked-Cortez_-_Feel__Stripped_ | en | 241 | — | — | 0.067 | 100.0 % | 100.0 % | 98.9 % | manual | 0.0 % | 12.4 % | — | 62.5 |  |
| unmarked-Culture_&_Co._-_cool.cavemen | fr | 212 | — | — | 0.032 | 98.4 % | 99.2 % | 93.9 % | manual | 0.0 % | 62.3 % | — | 55.0 |  |
| unmarked-DON_VALDES_-_Tu_sais_Man | fr | 209 | — | — | 0.027 | 97.2 % | 97.5 % | 79.2 % | manual | 0.0 % | 42.0 % | — | 55.6 |  |
| unmarked-Der_Baum_-_Dienstag_is_Damensauna_(2) | de | 209 | — | — | 0.027 | 99.5 % | 99.5 % | 95.5 % | manual | 0.0 % | 10.6 % | — | 54.2 |  |
| unmarked-Die_Revolution_gehört_Dir!_-_partysahnen | de | 167 | — | — | 0.028 | 97.2 % | 97.9 % | 92.3 % | manual | 0.0 % | 41.6 % | — | 43.3 |  |
| unmarked-Drei_Nüsse_-_patrouille | de | 259 | — | — | 0.026 | 100.0 % | 100.0 % | 98.5 % | manual | 0.0 % | 4.6 % | — | 67.8 |  |
| unmarked-Esencia_-_NandoMalo_ | es | 262 | — | — | 0.023 | 100.0 % | 100.0 % | 98.2 % | manual | 0.0 % | 18.0 % | — | 67.5 |  |
| unmarked-Explosive_Ear_Candy_-_Like_The_Sun | en | 193 | — | — | 0.049 | 100.0 % | 100.0 % | 99.6 % | manual | 0.3 % | 21.2 % | — | 50.7 |  |
| unmarked-Fantasma_-_Los_Rombos | es | 166 | — | — | 0.047 | 93.3 % | 94.7 % | 85.2 % | manual | 0.4 % | 17.9 % | — | 43.0 |  |
| unmarked-Fußabdrücke_-_Andreas_Jachmann | de | 241 | — | — | 0.023 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 1.3 % | — | 62.6 |  |
| unmarked-Guayeteo_-_JhoyKing | es | 158 | — | — | 0.031 | 89.8 % | 90.2 % | 77.9 % | manual | 0.0 % | 19.9 % | — | 41.8 |  |
| unmarked-Intentando_Destacar_-_Sundayers_ | es | 220 | — | — | 0.023 | 100.0 % | 100.0 % | 80.4 % | manual | 0.0 % | 18.4 % | — | 57.5 |  |
| unmarked-Keine_Lust_-_Jonny_M | de | 229 | — | — | 0.016 | 100.0 % | 100.0 % | 95.8 % | manual | 0.0 % | 4.4 % | — | 61.0 |  |
| unmarked-LUNABLIND_-_Vision__Radio_Edit_ | en | 221 | — | — | 0.064 | 99.3 % | 99.3 % | 97.6 % | manual | 0.0 % | 11.4 % | — | 57.8 |  |
| unmarked-La_rumba_del_coronavirus_-_Rich_Don_Jeri | es | 187 | — | — | 0.029 | 97.6 % | 97.6 % | 92.9 % | manual | 0.0 % | 2.9 % | — | 49.1 |  |
| unmarked-Les_files_d'attente_-_Law' | fr | 196 | — | — | 0.031 | 98.1 % | 98.1 % | 65.2 % | manual | 0.0 % | 26.2 % | — | 51.2 |  |
| unmarked-Libre_by_CybeR_AttaCK_-_CyberAttacK | fr | 217 | — | — | 0.029 | 99.0 % | 99.7 % | 96.5 % | manual | 0.0 % | 34.9 % | — | 57.2 |  |
| unmarked-Lower_Loveday_-_Is_It_Right_ | en | 180 | — | — | 0.057 | 99.5 % | 99.5 % | 96.7 % | manual | 0.0 % | 17.0 % | — | 47.1 |  |
| unmarked-Mes_Larmes_-_kobzx2z | fr | 159 | — | — | 0.025 | 85.7 % | 86.6 % | 59.5 % | manual | 0.0 % | 38.0 % | — | 41.7 |  |
| unmarked-Moon_I_Mean_-_Wrong_Concept | en | 220 | — | — | 0.052 | 99.2 % | 99.2 % | 94.5 % | manual | 0.0 % | 54.9 % | — | 56.8 |  |
| unmarked-Mère_nature_-_Law' | fr | 225 | — | — | 0.037 | 100.0 % | 100.0 % | 96.5 % | manual | 0.0 % | 13.9 % | — | 58.4 |  |
| unmarked-Palabras_-_Javier_Gomez_Bello | es | 216 | — | — | 0.031 | 100.0 % | 100.0 % | 99.5 % | manual | 0.0 % | 4.2 % | — | 56.0 |  |
| unmarked-Pluie_d'entre_deux_saisons_-_Midnight_Prefou | fr | 205 | — | — | 0.044 | 91.9 % | 91.9 % | 82.8 % | manual | 0.2 % | 21.6 % | — | 52.6 |  |
| unmarked-Pure_Mids_-_The_Leader | en | 262 | — | — | 0.077 | 100.0 % | 100.0 % | 71.9 % | manual | 0.5 % | 75.3 % | — | 66.8 |  |
| unmarked-Quentin_Hannappe_-_Keep_On | en | 190 | — | — | 0.046 | 98.8 % | 98.8 % | 91.4 % | manual | 0.0 % | 21.1 % | — | 49.5 |  |
| unmarked-Ridgway_-_Fire_Inside | en | 284 | — | — | 0.049 | 92.6 % | 93.1 % | 71.1 % | manual | 0.0 % | 30.6 % | — | 72.2 |  |
| unmarked-Rxbyn_-_Bad_Side | en | 217 | — | — | 0.053 | 99.5 % | 99.5 % | 93.2 % | manual | 0.0 % | 23.4 % | — | 57.4 |  |
| unmarked-Schnodderdodder_-_Abendblau | de | 197 | — | — | 0.021 | 99.3 % | 100.0 % | 95.5 % | manual | 0.0 % | 14.0 % | — | 52.0 |  |
| unmarked-Slingshot_Miracle_-_Whistler | en | 229 | — | — | 0.072 | 95.6 % | 96.2 % | 97.5 % | manual | 0.0 % | 23.8 % | — | 59.4 |  |
| unmarked-Séculaire_feat._Nÿme_-_saru | fr | 159 | — | — | 0.024 | 97.4 % | 97.4 % | 88.1 % | manual | 0.1 % | 23.0 % | — | 42.0 |  |
| unmarked-Vente_-_Fafarulo_Calabaza | es | 336 | — | — | 0.033 | 99.6 % | 99.6 % | 97.8 % | manual | 0.0 % | 9.2 % | — | 88.0 |  |
| unmarked-Wordsmith_-_The_Statement | en | 171 | — | — | 0.066 | 76.8 % | 77.0 % | 75.7 % | manual | 0.0 % | 27.6 % | — | 44.8 |  |
| unmarked-Yuanan_-_Miedo_-_Yuanan | es | 169 | — | — | 0.027 | 100.0 % | 100.0 % | 91.0 % | manual | 0.0 % | 11.0 % | — | 44.6 |  |
| unmarked-de_bonne_humeur_-_Le_Nez_Tordu | fr | 161 | — | — | 0.030 | 99.6 % | 100.0 % | 97.0 % | manual | 0.0 % | 14.9 % | — | 42.9 |  |
| unmarked-dich_gehen_zu_sehn._-_Wingenbach_Frank | de | 193 | — | — | 0.030 | 98.9 % | 100.0 % | 97.8 % | manual | 0.0 % | 11.5 % | — | 50.5 |  |
| unmarked-¡Óyeme_tiburón!_-_Corrientes | es | 180 | — | — | 0.028 | 100.0 % | 100.0 % | 98.1 % | manual | 0.0 % | 6.2 % | — | 47.0 |  |

## Peores casos

Mayor mediana de error de inicio:
- marked-Pure_Mids_-_The_Leader: 0.077 s
- unmarked-Pure_Mids_-_The_Leader: 0.077 s
- unmarked-Slingshot_Miracle_-_Whistler: 0.072 s
- marked-Slingshot_Miracle_-_Whistler: 0.067 s
- marked-Cortez_-_Feel__Stripped_: 0.067 s

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
