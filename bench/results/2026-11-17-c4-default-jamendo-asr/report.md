# Banco · c4-default · jamendo · sin letra

- Fecha: 2026-11-17T16:27:51+01:00
- Commit: 3b31efe
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
| de | 20 | 0 | 14.0 % | — | 7.6 % | 0.029 | 0.042 | 99.3 % | 99.7 % | 0.077 | 0.022 | 87.4 % | — | 0 | 83 | 0.0 % | 15.9 % |
| en | 20 | 0 | 27.4 % | — | 17.8 % | 0.058 | 0.166 | 97.7 % | 98.1 % | 0.066 | 0.082 | 80.6 % | — | 0 | 84 | 0.0 % | 34.5 % |
| es | 20 | 0 | 14.5 % | — | 8.4 % | 0.028 | 0.052 | 98.9 % | 99.0 % | 0.099 | 0.006 | 90.4 % | — | 0 | 83 | 0.0 % | 15.6 % |
| fr | 19 | 0 | 28.0 % | — | 15.8 % | 0.029 | 0.102 | 98.5 % | 98.8 % | 0.086 | 0.048 | 74.1 % | — | 0 | 83 | 0.0 % | 24.3 % |
| total | 79 | 0 | 21.3 % | — | 12.5 % | 0.034 | 0.090 | 98.6 % | 98.9 % | 0.083 | 0.039 | 83.0 % | — | 0 | 83 | 0.0 % | 22.5 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 7.2 | 2867 | 2388 | 0.204 |
| transcriber | 0.1 | 1335 | 2446 | 0.054 |
| segmenter | — | 0 | 93 | 0.000 |
| aligner | 0.1 | 2133 | 4170 | 0.058 |

## Por canción

| Canción | Idioma | Duración | WER | WER tolerante | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10._Disparan_-_criatura | es | 160 | 10.8 % | — | 0.023 | 100.0 % | 100.0 % | 91.2 % | manual | 0.0 % | 23.7 % | es | 49.3 (caché) |  |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | 11.2 % | — | 0.045 | 99.4 % | 99.4 % | 89.1 % | manual | 0.0 % | 21.7 % | de | 67.1 (caché) |  |
| Avercage_-_Embers | en | 243 | 66.7 % | — | 0.167 | 82.3 % | 87.3 % | 41.8 % | manual | 0.0 % | 90.4 % | en | 83.2 |  |
| Baila_-_Alfonso_Lugo | es | 210 | 21.1 % | — | 0.019 | 99.1 % | 99.1 % | 83.3 % | manual | 0.0 % | 27.5 % | es | 66.4 (caché) |  |
| Besando_Sapos_-_Dream_Tabu | es | 251 | 12.3 % | — | 0.031 | 100.0 % | 100.0 % | 99.1 % | manual | 0.0 % | 21.2 % | es | 79.6 |  |
| Bitte_beweg_dich_nicht_-_Bukto | de | 273 | 9.3 % | — | 0.037 | 100.0 % | 100.0 % | 91.2 % | manual | 0.0 % | 20.7 % | de | 107.0 |  |
| Burn_Out_Man_-_Abendblau | de | 260 | 8.7 % | — | 0.039 | 99.6 % | 100.0 % | 86.4 % | manual | 0.0 % | 9.3 % | de | 83.1 |  |
| CHRISTMAS_AVEC_TOI_-_imfreshyourepretty | fr | 234 | 51.4 % | — | 0.034 | 94.9 % | 94.9 % | 50.0 % | manual | 0.0 % | 39.4 % | fr | 75.9 |  |
| CLUB_DESTINO__-_Pensando_en_ti_-_CLUB_DESTINO | es | 219 | 11.2 % | — | 0.037 | 100.0 % | 100.0 % | 96.6 % | manual | 0.0 % | 17.2 % | es | 68.0 |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | 40.9 % | — | 0.054 | 98.6 % | 100.0 % | 77.2 % | manual | 0.0 % | 15.2 % | de | 75.6 (caché) |  |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | 7.3 % | — | 0.023 | 100.0 % | 100.0 % | 93.1 % | manual | 0.0 % | 6.6 % | fr | 57.7 (caché) |  |
| Caralibro_-_Vagos_Permanentes | es | 279 | 11.8 % | — | 0.028 | 99.5 % | 99.5 % | 90.5 % | manual | 0.0 % | 24.8 % | es | 80.7 |  |
| Color_Out_-_Falling_Star | en | 222 | 26.7 % | — | 0.150 | 97.3 % | 98.4 % | 83.0 % | manual | 0.0 % | 35.2 % | en | 67.3 |  |
| Confession_-_Quesabe | fr | 148 | 29.9 % | — | 0.027 | 98.4 % | 98.4 % | 72.6 % | manual | 0.0 % | 22.6 % | fr | 53.8 (caché) |  |
| Cortez_-_Feel__Stripped_ | en | 241 | 13.8 % | — | 0.068 | 99.1 % | 99.1 % | 89.6 % | manual | 0.0 % | 12.1 % | en | 74.2 (caché) |  |
| Culture_&_Co._-_cool.cavemen | fr | 212 | 57.6 % | — | 0.030 | 93.7 % | 93.7 % | 47.7 % | manual | 0.0 % | 62.4 % | fr | 66.4 |  |
| DON_VALDES_-_Tu_sais_Man | fr | 209 | 35.8 % | — | 0.028 | 96.3 % | 98.0 % | 70.3 % | manual | 0.0 % | 45.6 % | fr | 72.7 |  |
| Da_wurdest_du_geboren_-_Alice_Tlustos_ | de | 207 | 6.8 % | — | 0.054 | 100.0 % | 100.0 % | 94.6 % | manual | 0.0 % | 7.4 % | de | 64.5 |  |
| Der_Baum_-_Dienstag_is_Damensauna_(2) | de | 209 | 9.9 % | — | 0.027 | 100.0 % | 100.0 % | 90.1 % | manual | 0.0 % | 10.0 % | de | 64.4 |  |
| Der_Musiker_-_d-music | de | 271 | 21.0 % | — | 0.020 | 100.0 % | 100.0 % | 83.6 % | manual | 0.0 % | 10.7 % | de | 92.6 (caché) |  |
| Die_Revolution_gehört_Dir!_-_partysahnen | de | 167 | 16.4 % | — | 0.025 | 97.1 % | 97.8 % | 87.8 % | manual | 0.0 % | 36.4 % | de | 54.7 |  |
| Diosa_de_la_noche_-_Brunela_Crochenci | es | 230 | 20.3 % | — | 0.030 | 100.0 % | 100.0 % | 86.1 % | manual | 0.1 % | 16.4 % | es | 90.2 |  |
| Drei_Nüsse_-_patrouille | de | 259 | 6.0 % | — | 0.026 | 100.0 % | 100.0 % | 94.0 % | manual | 0.0 % | 5.2 % | de | 83.0 |  |
| En_liberté_-_tom.leyak | fr | 234 | 25.8 % | — | 0.032 | 100.0 % | 100.0 % | 81.2 % | manual | 0.0 % | 18.7 % | fr | 73.5 |  |
| Esencia_-_NandoMalo_ | es | 262 | 16.5 % | — | 0.024 | 98.1 % | 98.4 % | 93.7 % | manual | 0.0 % | 16.5 % | es | 85.5 (caché) |  |
| Explosive_Ear_Candy_-_Like_The_Sun | en | 193 | 57.5 % | — | 0.049 | 100.0 % | 100.0 % | 95.5 % | manual | 0.2 % | 19.2 % | en | 81.7 |  |
| Fantasma_-_Los_Rombos | es | 166 | 48.6 % | — | 0.042 | 95.8 % | 97.2 % | 81.8 % | manual | 0.0 % | 24.2 % | es | 57.2 |  |
| Freifliegen_-_durch.dick.und.duenn | de | 250 | 5.2 % | — | 0.033 | 100.0 % | 100.0 % | 96.3 % | manual | 0.0 % | 9.0 % | de | 73.9 |  |
| Fußabdrücke_-_Andreas_Jachmann | de | 241 | 7.8 % | — | 0.023 | 100.0 % | 100.0 % | 93.5 % | manual | 0.0 % | 3.8 % | de | 73.1 |  |
| Guayeteo_-_JhoyKing | es | 158 | 34.2 % | — | 0.025 | 98.0 % | 98.4 % | 73.5 % | manual | 0.0 % | 20.0 % | es | 51.6 |  |
| HILA_-_Give_Me_the_Same | en | 234 | 13.2 % | — | 0.062 | 99.6 % | 99.6 % | 87.3 % | manual | 0.0 % | 25.8 % | en | 74.2 |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | 12.3 % | — | 0.036 | 100.0 % | 100.0 % | 89.6 % | manual | 0.0 % | 28.0 % | es | 61.9 (caché) |  |
| Ich_kann_dich_nicht_vergessen_-_Wingenbach_Frank | de | 258 | 5.1 % | — | 0.029 | 100.0 % | 100.0 % | 94.4 % | manual | 0.0 % | 10.7 % | de | 76.2 |  |
| Intentando_Destacar_-_Sundayers_ | es | 220 | 26.8 % | — | 0.023 | 100.0 % | 100.0 % | 74.6 % | manual | 0.0 % | 16.4 % | es | 66.5 |  |
| Intro_[Pulsschlag]_-_Zeugen_der_Leere_(2) | de | 157 | 59.8 % | — | 0.039 | 100.0 % | 100.0 % | 76.8 % | manual | 0.1 % | 62.0 % | de | 52.0 |  |
| JASON_MILLER_-_CROWD_PLEASER | en | 193 | 17.2 % | — | 0.048 | 100.0 % | 100.0 % | 89.1 % | manual | 0.0 % | 10.7 % | en | 64.3 |  |
| Keine_Lust_-_Jonny_M | de | 229 | 10.5 % | — | 0.016 | 97.2 % | 98.7 % | 88.8 % | manual | 0.0 % | 5.2 % | de | 78.4 (caché) |  |
| Kinematic_-_Peyote | en | 183 | 27.7 % | — | 0.052 | 100.0 % | 100.0 % | 83.0 % | manual | 0.4 % | 31.5 % | en | 59.6 (caché) |  |
| LUNABLIND_-_Vision__Radio_Edit_ | en | 221 | 12.2 % | — | 0.064 | 100.0 % | 100.0 % | 90.6 % | manual | 0.0 % | 10.8 % | en | 69.4 |  |
| La_rumba_del_coronavirus_-_Rich_Don_Jeri | es | 187 | 8.4 % | — | 0.034 | 91.9 % | 91.9 % | 94.2 % | manual | 0.0 % | 7.6 % | es | 73.9 |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | 5.6 % | — | 0.022 | 100.0 % | 100.0 % | 94.1 % | manual | 0.0 % | 10.5 % | fr | 56.4 (caché) |  |
| Le_royaume_des_glous_glous_-_Raoul_de_QSM | fr | 163 | 28.7 % | — | 0.036 | 100.0 % | 100.0 % | 74.8 % | manual | 0.0 % | 19.8 % | fr | 49.5 |  |
| Les_files_d'attente_-_Law' | fr | 196 | 34.3 % | — | 0.029 | 97.9 % | 97.9 % | 60.5 % | manual | 0.0 % | 23.7 % | fr | 62.5 |  |
| Libre_by_CybeR_AttaCK_-_CyberAttacK | fr | 217 | 34.8 % | — | 0.029 | 99.3 % | 99.6 % | 69.8 % | manual | 0.0 % | 35.3 % | fr | 67.8 |  |
| Lower_Loveday_-_Is_It_Right_ | en | 180 | 7.4 % | — | 0.062 | 100.0 % | 100.0 % | 92.0 % | manual | 0.0 % | 16.6 % | en | 56.5 |  |
| Mes_Larmes_-_kobzx2z | fr | 159 | 53.5 % | — | 0.022 | 95.3 % | 96.4 % | 43.6 % | manual | 0.0 % | 42.0 % | fr | 50.0 |  |
| Moon_I_Mean_-_Wrong_Concept | en | 220 | 34.9 % | — | 0.053 | 98.5 % | 99.5 % | 71.7 % | manual | 0.0 % | 61.3 % | en | 67.2 |  |
| Musik_-_Heiko | de | 295 | 7.2 % | — | 0.026 | 100.0 % | 100.0 % | 94.1 % | manual | 0.0 % | 4.2 % | de | 89.0 |  |
| Mère_nature_-_Law' | fr | 225 | 13.0 % | — | 0.036 | 100.0 % | 100.0 % | 89.4 % | manual | 0.0 % | 10.9 % | fr | 70.2 (caché) |  |
| POIGNEE_DE_MAIN_-_Cabbac | fr | 209 | 19.2 % | — | 0.035 | 99.1 % | 99.1 % | 79.5 % | manual | 0.0 % | 13.7 % | fr | 62.9 |  |
| Palabras_-_Javier_Gomez_Bello | es | 216 | 8.0 % | — | 0.031 | 100.0 % | 100.0 % | 93.9 % | manual | 0.0 % | 4.2 % | es | 66.3 |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | 19.3 % | — | 0.036 | 98.8 % | 98.8 % | 89.9 % | manual | 0.0 % | 32.0 % | fr | 63.0 (caché) |  |
| Pluie_d'entre_deux_saisons_-_Midnight_Prefou | fr | 205 | 30.3 % | — | 0.037 | 94.9 % | 94.9 % | 73.9 % | manual | 0.2 % | 21.4 % | fr | 76.5 |  |
| Pure_Mids_-_The_Leader | en | 262 | 38.3 % | — | 0.092 | 91.5 % | 92.7 % | 71.9 % | manual | 0.0 % | 79.8 % | en | 95.7 |  |
| Quentin_Hannappe_-_Keep_On | en | 190 | 17.9 % | — | 0.046 | 100.0 % | 100.0 % | 87.4 % | manual | 0.0 % | 23.1 % | en | 61.4 |  |
| Quiero_y_Puedo_-_Nacidos_de_la_Tierra | es | 236 | 4.0 % | — | 0.027 | 100.0 % | 100.0 % | 96.7 % | manual | 0.0 % | 8.5 % | es | 77.7 |  |
| Ridgway_-_Fire_Inside | en | 284 | 16.2 % | — | 0.051 | 95.3 % | 95.7 % | 76.3 % | manual | 0.0 % | 40.2 % | en | 88.3 (caché) |  |
| Rxbyn_-_Bad_Side | en | 217 | 22.1 % | — | 0.057 | 95.1 % | 95.4 % | 83.2 % | manual | 0.0 % | 22.8 % | en | 68.3 |  |
| SHANEY_23_feat._G1NA_G._x_In_den_Strassen_-_Shaney_23 | de | 211 | 31.9 % | — | 0.042 | 98.7 % | 99.7 % | 68.5 % | manual | 0.0 % | 22.9 % | de | 67.5 |  |
| Schnodderdodder_-_Abendblau | de | 197 | 13.0 % | — | 0.022 | 100.0 % | 100.0 % | 86.6 % | manual | 0.0 % | 16.2 % | de | 66.1 |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | 15.9 % | — | 0.029 | 100.0 % | 100.0 % | 88.7 % | manual | 0.1 % | 14.4 % | de | 67.6 (caché) |  |
| Sin_miedo_-_Living_Camboya | es | 223 | 7.0 % | — | 0.026 | 100.0 % | 100.0 % | 93.6 % | manual | 0.0 % | 6.7 % | es | 68.2 |  |
| Slingshot_Miracle_-_Whistler | en | 229 | 12.9 % | — | 0.063 | 99.3 % | 100.0 % | 90.7 % | manual | 0.0 % | 28.5 % | en | 73.0 |  |
| Songwriterz_-_Back_In_Time | en | 209 | 14.3 % | — | 0.060 | 93.4 % | 93.4 % | 83.2 % | manual | 0.0 % | 32.2 % | en | 67.4 |  |
| Séculaire_feat._Nÿme_-_saru | fr | 159 | 25.4 % | — | 0.022 | 99.6 % | 99.6 % | 77.1 % | manual | 0.1 % | 28.0 % | fr | 60.6 |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | 9.5 % | — | 0.029 | 98.4 % | 98.6 % | 95.2 % | manual | 0.0 % | 15.0 % | es | 62.3 (caché) |  |
| The.madpix.project_-_One_Way_Street | en | 171 | 23.1 % | — | 0.060 | 100.0 % | 100.0 % | 84.7 % | manual | 0.0 % | 28.3 % | en | 59.7 |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | 47.0 % | — | 0.060 | 96.5 % | 99.3 % | 70.4 % | manual | 0.0 % | 54.1 % | en | 75.9 (caché) |  |
| Tom_Orlando_-_The_One__feat._Tina_G_ | en | 240 | 36.9 % | — | 0.044 | 97.4 % | 97.4 % | 77.9 % | manual | 0.0 % | 39.5 % | en | 80.8 |  |
| Une_Vie_De_Roi_-_david | fr | 303 | 6.8 % | — | 0.030 | 100.0 % | 100.0 % | 93.2 % | manual | 0.0 % | 5.8 % | fr | 93.4 |  |
| Vente_-_Fafarulo_Calabaza | es | 336 | 8.6 % | — | 0.033 | 99.8 % | 99.8 % | 92.5 % | manual | 0.0 % | 10.5 % | es | 105.3 |  |
| Veränderung_-_doromusis | de | 194 | 20.4 % | — | 0.030 | 97.7 % | 98.2 % | 81.0 % | manual | 0.0 % | 22.1 % | de | 70.7 |  |
| Wordsmith_-_The_Statement | en | 171 | 35.4 % | — | 0.053 | 96.5 % | 96.5 % | 64.0 % | manual | 0.0 % | 27.3 % | en | 55.3 (caché) |  |
| Yuanan_-_Miedo_-_Yuanan | es | 169 | 27.2 % | — | 0.026 | 95.7 % | 95.7 % | 78.7 % | manual | 0.0 % | 11.8 % | es | 53.9 |  |
| de_bonne_humeur_-_Le_Nez_Tordu | fr | 161 | 20.1 % | — | 0.029 | 100.0 % | 100.0 % | 82.7 % | manual | 0.0 % | 11.1 % | fr | 51.7 |  |
| dich_gehen_zu_sehn._-_Wingenbach_Frank | de | 193 | 9.9 % | — | 0.029 | 98.8 % | 100.0 % | 90.1 % | manual | 0.0 % | 10.0 % | de | 61.5 |  |
| l'abandon_-_flo | fr | 210 | 18.6 % | — | 0.030 | 98.2 % | 98.9 % | 80.6 % | manual | 0.0 % | 12.2 % | fr | 69.8 |  |
| te_amo_-_fabios_la_nueva_expresion_de_la_cancion | es | 195 | 7.1 % | — | 0.033 | 100.0 % | 100.0 % | 97.0 % | manual | 0.0 % | 4.2 % | es | 58.6 |  |
| ¡Óyeme_tiburón!_-_Corrientes | es | 180 | 5.2 % | — | 0.028 | 100.0 % | 100.0 % | 95.2 % | manual | 0.0 % | 7.6 % | es | 57.8 |  |

## Peores casos

Mayor mediana de error de inicio:
- Avercage_-_Embers: 0.167 s
- Color_Out_-_Falling_Star: 0.150 s
- Pure_Mids_-_The_Leader: 0.092 s
- Cortez_-_Feel__Stripped_: 0.068 s
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
