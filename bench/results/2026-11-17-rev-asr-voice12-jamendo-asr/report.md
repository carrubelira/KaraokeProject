# Banco · rev-asr-voice12 · jamendo · sin letra

- Fecha: 2026-11-17T05:38:47+01:00
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

Mel-Band RoFormer (Kim, 8 s) + Whisper (each language's default) reading stretches of singing of at most 12 s + line segmenter + lyrics aligner

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt', 'segment_size': 801}
- **transcriber**: `karaoke_engine.transcribe:WhisperTranscriber` v5 {'by_voice': True, 'stretch_seconds': 12.0}
- **segmenter**: `karaoke_engine.transcribe:LineSegmenter` v2
- **aligner**: `karaoke_engine.align.aligner:LyricsAligner` v14 {'second': '', 'rest_penalty': 0.0}

## Resumen

| Grupo | Canciones | Fallos | WER | WER tolerante | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| de | 20 | 0 | 14.0 % | — | 7.6 % | 0.029 | 0.045 | 99.0 % | 99.5 % | 0.073 | 0.024 | 87.4 % | — | 0 | 73 | 0.0 % | 19.5 % |
| en | 20 | 0 | 27.4 % | — | 17.8 % | 0.059 | 0.248 | 96.3 % | 96.6 % | 0.058 | 0.045 | 79.7 % | — | 0 | 74 | 0.0 % | 33.2 % |
| es | 20 | 0 | 14.5 % | — | 8.4 % | 0.028 | 0.054 | 99.0 % | 99.1 % | 0.091 | 0.011 | 89.9 % | — | 0 | 73 | 0.0 % | 19.6 % |
| fr | 19 | 0 | 28.0 % | — | 15.8 % | 0.030 | 0.112 | 98.1 % | 98.5 % | 0.081 | 0.046 | 74.0 % | — | 0 | 73 | 0.0 % | 28.8 % |
| total | 79 | 0 | 21.3 % | — | 12.5 % | 0.035 | 0.114 | 98.1 % | 98.4 % | 0.076 | 0.031 | 82.6 % | — | 0 | 73 | 0.0 % | 25.2 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 7.2 | 2867 | 2388 | 0.204 |
| transcriber | 0.1 | 1335 | 2424 | 0.053 |
| segmenter | — | 0 | 93 | 0.000 |
| aligner | 0.1 | 1559 | 3763 | 0.017 |

## Por canción

| Canción | Idioma | Duración | WER | WER tolerante | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10._Disparan_-_criatura | es | 160 | 10.8 % | — | 0.023 | 100.0 % | 100.0 % | 91.2 % | manual | 0.0 % | 25.4 % | es | 43.4 (caché) |  |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | 11.2 % | — | 0.046 | 99.4 % | 100.0 % | 89.1 % | manual | 0.0 % | 33.4 % | de | 60.7 (caché) |  |
| Avercage_-_Embers | en | 243 | 66.7 % | — | 0.167 | 78.7 % | 80.0 % | 39.7 % | manual | 0.0 % | 84.5 % | en | 74.2 |  |
| Baila_-_Alfonso_Lugo | es | 210 | 21.1 % | — | 0.019 | 99.6 % | 99.6 % | 83.3 % | manual | 0.0 % | 33.1 % | es | 57.6 (caché) |  |
| Besando_Sapos_-_Dream_Tabu | es | 251 | 12.3 % | — | 0.032 | 100.0 % | 100.0 % | 99.1 % | manual | 0.0 % | 28.6 % | es | 70.7 |  |
| Bitte_beweg_dich_nicht_-_Bukto | de | 273 | 9.3 % | — | 0.038 | 99.7 % | 99.7 % | 91.2 % | manual | 0.0 % | 23.0 % | de | 85.7 |  |
| Burn_Out_Man_-_Abendblau | de | 260 | 8.7 % | — | 0.039 | 99.6 % | 100.0 % | 86.4 % | manual | 0.0 % | 12.1 % | de | 71.8 |  |
| CHRISTMAS_AVEC_TOI_-_imfreshyourepretty | fr | 234 | 51.4 % | — | 0.035 | 94.9 % | 94.9 % | 50.0 % | manual | 0.0 % | 47.9 % | fr | 67.4 |  |
| CLUB_DESTINO__-_Pensando_en_ti_-_CLUB_DESTINO | es | 219 | 11.2 % | — | 0.037 | 100.0 % | 100.0 % | 96.6 % | manual | 0.0 % | 20.5 % | es | 58.2 |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | 40.9 % | — | 0.049 | 97.2 % | 98.6 % | 77.2 % | manual | 0.1 % | 26.2 % | de | 66.1 (caché) |  |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | 7.3 % | — | 0.025 | 100.0 % | 100.0 % | 93.1 % | manual | 0.0 % | 6.6 % | fr | 50.5 (caché) |  |
| Caralibro_-_Vagos_Permanentes | es | 279 | 11.8 % | — | 0.027 | 99.0 % | 99.5 % | 90.5 % | manual | 0.1 % | 23.7 % | es | 70.2 |  |
| Color_Out_-_Falling_Star | en | 222 | 26.7 % | — | 0.149 | 95.2 % | 96.2 % | 83.0 % | manual | 0.0 % | 35.6 % | en | 58.2 |  |
| Confession_-_Quesabe | fr | 148 | 29.9 % | — | 0.027 | 98.8 % | 99.6 % | 72.6 % | manual | 0.0 % | 38.4 % | fr | 45.2 (caché) |  |
| Cortez_-_Feel__Stripped_ | en | 241 | 13.8 % | — | 0.069 | 100.0 % | 100.0 % | 89.6 % | manual | 0.0 % | 12.1 % | en | 64.8 (caché) |  |
| Culture_&_Co._-_cool.cavemen | fr | 212 | 57.6 % | — | 0.024 | 92.1 % | 92.1 % | 47.7 % | manual | 0.0 % | 60.3 % | fr | 57.6 |  |
| DON_VALDES_-_Tu_sais_Man | fr | 209 | 35.8 % | — | 0.034 | 92.9 % | 94.9 % | 69.7 % | manual | 0.0 % | 47.4 % | fr | 63.2 |  |
| Da_wurdest_du_geboren_-_Alice_Tlustos_ | de | 207 | 6.8 % | — | 0.051 | 100.0 % | 100.0 % | 94.6 % | manual | 0.0 % | 12.1 % | de | 55.7 |  |
| Der_Baum_-_Dienstag_is_Damensauna_(2) | de | 209 | 9.9 % | — | 0.027 | 100.0 % | 100.0 % | 90.1 % | manual | 0.0 % | 10.9 % | de | 55.0 |  |
| Der_Musiker_-_d-music | de | 271 | 21.0 % | — | 0.020 | 100.0 % | 100.0 % | 83.6 % | manual | 0.0 % | 13.0 % | de | 80.3 (caché) |  |
| Die_Revolution_gehört_Dir!_-_partysahnen | de | 167 | 16.4 % | — | 0.027 | 93.4 % | 93.4 % | 87.8 % | manual | 0.0 % | 35.0 % | de | 46.6 |  |
| Diosa_de_la_noche_-_Brunela_Crochenci | es | 230 | 20.3 % | — | 0.029 | 100.0 % | 100.0 % | 86.1 % | manual | 0.1 % | 23.1 % | es | 79.6 |  |
| Drei_Nüsse_-_patrouille | de | 259 | 6.0 % | — | 0.026 | 99.8 % | 100.0 % | 94.0 % | manual | 0.0 % | 7.9 % | de | 71.3 |  |
| En_liberté_-_tom.leyak | fr | 234 | 25.8 % | — | 0.032 | 99.5 % | 100.0 % | 81.2 % | manual | 0.0 % | 28.7 % | fr | 64.3 |  |
| Esencia_-_NandoMalo_ | es | 262 | 16.5 % | — | 0.024 | 98.1 % | 98.1 % | 93.7 % | manual | 0.0 % | 17.1 % | es | 74.1 (caché) |  |
| Explosive_Ear_Candy_-_Like_The_Sun | en | 193 | 57.5 % | — | 0.049 | 100.0 % | 100.0 % | 95.5 % | manual | 0.4 % | 20.9 % | en | 71.0 |  |
| Fantasma_-_Los_Rombos | es | 166 | 48.6 % | — | 0.037 | 97.2 % | 98.6 % | 81.8 % | manual | 0.0 % | 20.0 % | es | 49.4 |  |
| Freifliegen_-_durch.dick.und.duenn | de | 250 | 5.2 % | — | 0.032 | 99.2 % | 100.0 % | 96.3 % | manual | 0.0 % | 17.9 % | de | 64.0 |  |
| Fußabdrücke_-_Andreas_Jachmann | de | 241 | 7.8 % | — | 0.023 | 100.0 % | 100.0 % | 93.5 % | manual | 0.1 % | 5.1 % | de | 62.3 |  |
| Guayeteo_-_JhoyKing | es | 158 | 34.2 % | — | 0.026 | 99.6 % | 99.6 % | 72.1 % | manual | 0.0 % | 27.1 % | es | 44.2 |  |
| HILA_-_Give_Me_the_Same | en | 234 | 13.2 % | — | 0.059 | 99.6 % | 99.6 % | 87.3 % | manual | 0.0 % | 24.8 % | en | 64.8 |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | 12.3 % | — | 0.027 | 100.0 % | 100.0 % | 89.6 % | manual | 0.0 % | 36.4 % | es | 53.5 (caché) |  |
| Ich_kann_dich_nicht_vergessen_-_Wingenbach_Frank | de | 258 | 5.1 % | — | 0.031 | 100.0 % | 100.0 % | 94.4 % | manual | 0.0 % | 12.2 % | de | 66.2 |  |
| Intentando_Destacar_-_Sundayers_ | es | 220 | 26.8 % | — | 0.023 | 100.0 % | 100.0 % | 73.2 % | manual | 0.0 % | 15.1 % | es | 57.8 |  |
| Intro_[Pulsschlag]_-_Zeugen_der_Leere_(2) | de | 157 | 59.8 % | — | 0.038 | 96.8 % | 100.0 % | 76.8 % | manual | 0.0 % | 60.0 % | de | 44.8 |  |
| JASON_MILLER_-_CROWD_PLEASER | en | 193 | 17.2 % | — | 0.052 | 98.1 % | 98.1 % | 89.1 % | manual | 0.0 % | 11.3 % | en | 55.4 |  |
| Keine_Lust_-_Jonny_M | de | 229 | 10.5 % | — | 0.016 | 96.4 % | 97.9 % | 88.8 % | manual | 0.0 % | 8.9 % | de | 68.3 (caché) |  |
| Kinematic_-_Peyote | en | 183 | 27.7 % | — | 0.053 | 96.7 % | 97.5 % | 83.0 % | manual | 0.5 % | 28.9 % | en | 53.8 (caché) |  |
| LUNABLIND_-_Vision__Radio_Edit_ | en | 221 | 12.2 % | — | 0.064 | 100.0 % | 100.0 % | 90.6 % | manual | 0.0 % | 13.2 % | en | 60.3 |  |
| La_rumba_del_coronavirus_-_Rich_Don_Jeri | es | 187 | 8.4 % | — | 0.033 | 93.4 % | 93.4 % | 94.2 % | manual | 0.1 % | 15.6 % | es | 64.8 |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | 5.6 % | — | 0.022 | 100.0 % | 100.0 % | 94.1 % | manual | 0.0 % | 15.6 % | fr | 48.5 (caché) |  |
| Le_royaume_des_glous_glous_-_Raoul_de_QSM | fr | 163 | 28.7 % | — | 0.036 | 100.0 % | 100.0 % | 74.8 % | manual | 0.0 % | 22.7 % | fr | 42.1 |  |
| Les_files_d'attente_-_Law' | fr | 196 | 34.3 % | — | 0.030 | 96.9 % | 97.4 % | 60.5 % | manual | 0.0 % | 28.2 % | fr | 54.4 |  |
| Libre_by_CybeR_AttaCK_-_CyberAttacK | fr | 217 | 34.8 % | — | 0.029 | 99.3 % | 99.6 % | 69.8 % | manual | 0.0 % | 34.4 % | fr | 58.3 |  |
| Lower_Loveday_-_Is_It_Right_ | en | 180 | 7.4 % | — | 0.059 | 100.0 % | 100.0 % | 91.5 % | manual | 0.0 % | 17.1 % | en | 48.7 |  |
| Mes_Larmes_-_kobzx2z | fr | 159 | 53.5 % | — | 0.024 | 95.3 % | 96.4 % | 43.6 % | manual | 0.0 % | 47.7 % | fr | 43.0 |  |
| Moon_I_Mean_-_Wrong_Concept | en | 220 | 34.9 % | — | 0.050 | 99.0 % | 99.5 % | 71.0 % | manual | 0.0 % | 61.0 % | en | 58.4 |  |
| Musik_-_Heiko | de | 295 | 7.2 % | — | 0.025 | 100.0 % | 100.0 % | 94.1 % | manual | 0.1 % | 10.1 % | de | 77.9 |  |
| Mère_nature_-_Law' | fr | 225 | 13.0 % | — | 0.036 | 100.0 % | 100.0 % | 89.4 % | manual | 0.0 % | 19.0 % | fr | 61.2 (caché) |  |
| POIGNEE_DE_MAIN_-_Cabbac | fr | 209 | 19.2 % | — | 0.035 | 99.1 % | 99.1 % | 79.5 % | manual | 0.2 % | 18.0 % | fr | 54.6 |  |
| Palabras_-_Javier_Gomez_Bello | es | 216 | 8.0 % | — | 0.031 | 100.0 % | 100.0 % | 93.9 % | manual | 0.0 % | 8.5 % | es | 57.6 |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | 19.3 % | — | 0.038 | 99.2 % | 99.2 % | 89.9 % | manual | 0.0 % | 38.7 % | fr | 54.3 (caché) |  |
| Pluie_d'entre_deux_saisons_-_Midnight_Prefou | fr | 205 | 30.3 % | — | 0.039 | 94.9 % | 94.9 % | 73.9 % | manual | 0.3 % | 28.9 % | fr | 66.9 |  |
| Pure_Mids_-_The_Leader | en | 262 | 38.3 % | — | 0.091 | 89.4 % | 89.4 % | 74.6 % | manual | 0.0 % | 76.2 % | en | 83.9 |  |
| Quentin_Hannappe_-_Keep_On | en | 190 | 17.9 % | — | 0.046 | 100.0 % | 100.0 % | 87.4 % | manual | 0.0 % | 19.7 % | en | 53.2 |  |
| Quiero_y_Puedo_-_Nacidos_de_la_Tierra | es | 236 | 4.0 % | — | 0.027 | 100.0 % | 100.0 % | 96.7 % | manual | 0.0 % | 12.9 % | es | 67.3 |  |
| Ridgway_-_Fire_Inside | en | 284 | 16.2 % | — | 0.047 | 95.8 % | 95.8 % | 70.7 % | manual | 0.0 % | 30.6 % | en | 77.1 (caché) |  |
| Rxbyn_-_Bad_Side | en | 217 | 22.1 % | — | 0.060 | 95.4 % | 95.6 % | 83.2 % | manual | 0.0 % | 24.3 % | en | 59.1 |  |
| SHANEY_23_feat._G1NA_G._x_In_den_Strassen_-_Shaney_23 | de | 211 | 31.9 % | — | 0.042 | 98.0 % | 99.7 % | 68.5 % | manual | 0.0 % | 34.6 % | de | 58.0 |  |
| Schnodderdodder_-_Abendblau | de | 197 | 13.0 % | — | 0.022 | 100.0 % | 100.0 % | 86.6 % | manual | 0.0 % | 16.5 % | de | 57.5 |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | 15.9 % | — | 0.031 | 100.0 % | 100.0 % | 88.7 % | manual | 0.1 % | 15.0 % | de | 58.7 (caché) |  |
| Sin_miedo_-_Living_Camboya | es | 223 | 7.0 % | — | 0.027 | 100.0 % | 100.0 % | 93.6 % | manual | 0.0 % | 13.4 % | es | 59.5 |  |
| Slingshot_Miracle_-_Whistler | en | 229 | 12.9 % | — | 0.063 | 98.6 % | 100.0 % | 90.7 % | manual | 0.0 % | 29.1 % | en | 63.7 |  |
| Songwriterz_-_Back_In_Time | en | 209 | 14.3 % | — | 0.062 | 91.9 % | 92.4 % | 83.2 % | manual | 0.0 % | 31.8 % | en | 58.5 |  |
| Séculaire_feat._Nÿme_-_saru | fr | 159 | 25.4 % | — | 0.023 | 99.2 % | 99.2 % | 77.1 % | manual | 0.1 % | 27.9 % | fr | 52.2 |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | 9.5 % | — | 0.029 | 97.6 % | 98.3 % | 92.4 % | manual | 0.0 % | 16.5 % | es | 53.6 (caché) |  |
| The.madpix.project_-_One_Way_Street | en | 171 | 23.1 % | — | 0.060 | 100.0 % | 100.0 % | 84.7 % | manual | 0.0 % | 27.8 % | en | 52.3 |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | 47.0 % | — | 0.058 | 97.9 % | 99.3 % | 70.4 % | manual | 0.0 % | 53.1 % | en | 66.5 (caché) |  |
| Tom_Orlando_-_The_One__feat._Tina_G_ | en | 240 | 36.9 % | — | 0.047 | 84.9 % | 84.9 % | 71.7 % | manual | 0.0 % | 35.6 % | en | 70.4 |  |
| Une_Vie_De_Roi_-_david | fr | 303 | 6.8 % | — | 0.030 | 100.0 % | 100.0 % | 93.2 % | manual | 0.0 % | 5.5 % | fr | 81.7 |  |
| Vente_-_Fafarulo_Calabaza | es | 336 | 8.6 % | — | 0.034 | 100.0 % | 100.0 % | 91.7 % | manual | 0.0 % | 11.7 % | es | 91.4 |  |
| Veränderung_-_doromusis | de | 194 | 20.4 % | — | 0.029 | 98.2 % | 98.8 % | 81.0 % | manual | 0.1 % | 25.0 % | de | 61.7 |  |
| Wordsmith_-_The_Statement | en | 171 | 35.4 % | — | 0.054 | 95.4 % | 95.9 % | 63.7 % | manual | 0.0 % | 26.3 % | en | 47.1 (caché) |  |
| Yuanan_-_Miedo_-_Yuanan | es | 169 | 27.2 % | — | 0.027 | 95.7 % | 95.7 % | 78.7 % | manual | 0.0 % | 20.6 % | es | 46.4 |  |
| de_bonne_humeur_-_Le_Nez_Tordu | fr | 161 | 20.1 % | — | 0.029 | 100.0 % | 100.0 % | 82.7 % | manual | 0.0 % | 14.4 % | fr | 44.8 |  |
| dich_gehen_zu_sehn._-_Wingenbach_Frank | de | 193 | 9.9 % | — | 0.029 | 98.8 % | 100.0 % | 90.1 % | manual | 0.0 % | 11.1 % | de | 53.4 |  |
| l'abandon_-_flo | fr | 210 | 18.6 % | — | 0.029 | 97.8 % | 98.5 % | 80.6 % | manual | 0.0 % | 17.7 % | fr | 60.3 |  |
| te_amo_-_fabios_la_nueva_expresion_de_la_cancion | es | 195 | 7.1 % | — | 0.033 | 99.4 % | 100.0 % | 97.0 % | manual | 0.1 % | 8.5 % | es | 50.5 |  |
| ¡Óyeme_tiburón!_-_Corrientes | es | 180 | 5.2 % | — | 0.033 | 99.0 % | 99.0 % | 95.2 % | manual | 0.0 % | 14.7 % | es | 49.6 |  |

## Peores casos

Mayor mediana de error de inicio:
- Avercage_-_Embers: 0.167 s
- Color_Out_-_Falling_Star: 0.149 s
- Pure_Mids_-_The_Leader: 0.091 s
- Cortez_-_Feel__Stripped_: 0.069 s
- LUNABLIND_-_Vision__Radio_Edit_: 0.064 s

Mayor WER:
- Avercage_-_Embers: 66.7 %
- Intro_[Pulsschlag]_-_Zeugen_der_Leere_(2): 59.8 %
- Culture_&_Co._-_cool.cavemen: 57.6 %
- Explosive_Ear_Candy_-_Like_The_Sun: 57.5 %
- Mes_Larmes_-_kobzx2z: 53.5 %

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
