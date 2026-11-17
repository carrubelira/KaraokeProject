# Banco · rev-music-ctc · jamendo · con letra

- Fecha: 2026-11-16T13:50:11+01:00
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

Mel-Band RoFormer (Kim, 8 s) + Whisper + lyrics aligner (w2v-BERT 2.0 music lyrics CTC for every language)

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt', 'segment_size': 801}
- **transcriber**: `karaoke_engine.transcribe:WhisperTranscriber` v5
- **segmenter**: `karaoke_engine.transcribe:LineSegmenter` v2
- **aligner**: `karaoke_engine.align.aligner:LyricsAligner` v14 {'model': 'music-w2vbert-ctc'}

## Resumen

| Grupo | Canciones | Fallos | WER | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| de | 20 | 0 | — | — | 0.039 | 0.060 | 99.6 % | 99.9 % | 0.143 | 0.045 | 95.7 % | — | 0 | 74 | 0.0 % | 26.3 % |
| en | 20 | 0 | — | — | 0.056 | 0.126 | 98.4 % | 98.8 % | 0.132 | 0.077 | 92.4 % | — | 0 | 74 | 0.1 % | 24.1 % |
| es | 20 | 0 | — | — | 0.027 | 0.037 | 99.8 % | 99.9 % | 0.160 | 0.013 | 96.5 % | — | 0 | 74 | 0.0 % | 26.0 % |
| fr | 19 | 0 | — | — | 0.026 | 0.096 | 98.7 % | 98.8 % | 0.128 | -0.047 | 87.0 % | — | 0 | 74 | 0.0 % | 28.4 % |
| total | 79 | 0 | — | — | 0.035 | 0.080 | 99.1 % | 99.4 % | 0.142 | 0.024 | 92.8 % | — | 0 | 74 | 0.0 % | 26.2 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 6.9 | 2867 | 2388 | 0.204 |
| aligner | 10.7 | 2134 | 4264 | 0.031 |

## Por canción

| Canción | Idioma | Duración | WER | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10._Disparan_-_criatura | es | 160 | — | 0.025 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 34.0 % | — | 37.0 (caché) |  |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | — | 0.058 | 100.0 % | 100.0 % | 97.8 % | manual | 0.0 % | 19.9 % | — | 45.9 (caché) |  |
| Avercage_-_Embers | en | 243 | — | 0.156 | 87.3 % | 93.1 % | 100.0 % | manual | 0.0 % | 66.7 % | — | 58.1 |  |
| Baila_-_Alfonso_Lugo | es | 210 | — | 0.024 | 100.0 % | 100.0 % | 98.2 % | manual | 0.0 % | 35.9 % | — | 49.3 (caché) |  |
| Besando_Sapos_-_Dream_Tabu | es | 251 | — | 0.023 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 25.0 % | — | 59.5 |  |
| Bitte_beweg_dich_nicht_-_Bukto | de | 273 | — | 0.054 | 100.0 % | 100.0 % | 98.9 % | manual | 0.0 % | 39.4 % | — | 65.3 |  |
| Burn_Out_Man_-_Abendblau | de | 260 | — | 0.060 | 100.0 % | 100.0 % | 86.7 % | manual | 0.0 % | 16.9 % | — | 61.0 |  |
| CHRISTMAS_AVEC_TOI_-_imfreshyourepretty | fr | 234 | — | 0.035 | 100.0 % | 100.0 % | 64.3 % | manual | 0.0 % | 27.4 % | — | 55.8 |  |
| CLUB_DESTINO__-_Pensando_en_ti_-_CLUB_DESTINO | es | 219 | — | 0.049 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 30.1 % | — | 51.1 |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | — | 0.078 | 98.9 % | 100.0 % | 94.6 % | manual | 0.0 % | 29.0 % | — | 57.8 (caché) |  |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | — | 0.023 | 99.6 % | 100.0 % | 97.6 % | manual | 0.1 % | 41.9 % | — | 44.0 (caché) |  |
| Caralibro_-_Vagos_Permanentes | es | 279 | — | 0.028 | 100.0 % | 100.0 % | 99.5 % | manual | 0.0 % | 59.9 % | — | 65.3 |  |
| Color_Out_-_Falling_Star | en | 222 | — | 0.160 | 98.6 % | 99.5 % | 95.5 % | manual | 0.0 % | 34.7 % | — | 52.5 |  |
| Confession_-_Quesabe | fr | 148 | — | 0.027 | 98.6 % | 98.9 % | 83.3 % | manual | 0.2 % | 16.6 % | — | 34.5 (caché) |  |
| Cortez_-_Feel__Stripped_ | en | 241 | — | 0.077 | 99.1 % | 100.0 % | 98.9 % | manual | 0.0 % | 7.3 % | — | 56.7 (caché) |  |
| Culture_&_Co._-_cool.cavemen | fr | 212 | — | 0.048 | 83.9 % | 83.9 % | 93.9 % | manual | 0.0 % | 58.6 % | — | 50.2 |  |
| DON_VALDES_-_Tu_sais_Man | fr | 209 | — | 0.022 | 97.8 % | 97.8 % | 80.2 % | manual | 0.1 % | 29.2 % | — | 50.0 |  |
| Da_wurdest_du_geboren_-_Alice_Tlustos_ | de | 207 | — | 0.097 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 1.4 % | — | 48.0 |  |
| Der_Baum_-_Dienstag_is_Damensauna_(2) | de | 209 | — | 0.032 | 100.0 % | 100.0 % | 97.7 % | manual | 0.0 % | 50.5 % | — | 49.1 |  |
| Der_Musiker_-_d-music | de | 271 | — | 0.021 | 99.4 % | 99.4 % | 96.3 % | manual | 0.0 % | 16.7 % | — | 64.3 (caché) |  |
| Die_Revolution_gehört_Dir!_-_partysahnen | de | 167 | — | 0.040 | 99.3 % | 100.0 % | 93.6 % | manual | 0.0 % | 49.7 % | — | 38.8 |  |
| Diosa_de_la_noche_-_Brunela_Crochenci | es | 230 | — | 0.038 | 100.0 % | 100.0 % | 91.0 % | manual | 0.0 % | 8.3 % | — | 53.6 |  |
| Drei_Nüsse_-_patrouille | de | 259 | — | 0.030 | 100.0 % | 100.0 % | 98.5 % | manual | 0.0 % | 18.0 % | — | 61.3 |  |
| En_liberté_-_tom.leyak | fr | 234 | — | 0.028 | 100.0 % | 100.0 % | 94.0 % | manual | 0.0 % | 15.8 % | — | 55.0 |  |
| Esencia_-_NandoMalo_ | es | 262 | — | 0.021 | 100.0 % | 100.0 % | 98.2 % | manual | 0.0 % | 22.2 % | — | 61.7 (caché) |  |
| Explosive_Ear_Candy_-_Like_The_Sun | en | 193 | — | 0.049 | 100.0 % | 100.0 % | 99.6 % | manual | 0.0 % | 5.1 % | — | 46.0 |  |
| Fantasma_-_Los_Rombos | es | 166 | — | 0.067 | 93.6 % | 98.7 % | 88.6 % | manual | 0.6 % | 46.2 % | — | 38.5 |  |
| Freifliegen_-_durch.dick.und.duenn | de | 250 | — | 0.066 | 99.2 % | 99.2 % | 97.8 % | manual | 0.0 % | 12.6 % | — | 59.1 |  |
| Fußabdrücke_-_Andreas_Jachmann | de | 241 | — | 0.044 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 18.2 % | — | 57.2 |  |
| Guayeteo_-_JhoyKing | es | 158 | — | 0.024 | 100.0 % | 100.0 % | 84.7 % | manual | 0.0 % | 8.7 % | — | 37.3 |  |
| HILA_-_Give_Me_the_Same | en | 234 | — | 0.069 | 99.3 % | 99.3 % | 93.2 % | manual | 0.0 % | 12.3 % | — | 55.3 |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | — | 0.032 | 100.0 % | 100.0 % | 99.1 % | manual | 0.0 % | 36.8 % | — | 49.6 (caché) |  |
| Ich_kann_dich_nicht_vergessen_-_Wingenbach_Frank | de | 258 | — | 0.054 | 100.0 % | 100.0 % | 95.5 % | manual | 0.0 % | 34.3 % | — | 60.1 |  |
| Intentando_Destacar_-_Sundayers_ | es | 220 | — | 0.021 | 100.0 % | 100.0 % | 81.2 % | manual | 0.0 % | 67.7 % | — | 52.1 |  |
| Intro_[Pulsschlag]_-_Zeugen_der_Leere_(2) | de | 157 | — | 0.039 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 68.3 % | — | 36.8 |  |
| JASON_MILLER_-_CROWD_PLEASER | en | 193 | — | 0.037 | 99.8 % | 99.8 % | 83.1 % | manual | 0.0 % | 24.1 % | — | 46.4 |  |
| Keine_Lust_-_Jonny_M | de | 229 | — | 0.019 | 99.8 % | 99.8 % | 95.8 % | manual | 0.0 % | 4.8 % | — | 54.7 (caché) |  |
| Kinematic_-_Peyote | en | 183 | — | 0.056 | 99.3 % | 99.3 % | 93.9 % | manual | 0.4 % | 21.7 % | — | 42.7 (caché) |  |
| LUNABLIND_-_Vision__Radio_Edit_ | en | 221 | — | 0.065 | 99.3 % | 99.3 % | 99.7 % | manual | 0.0 % | 15.6 % | — | 52.9 |  |
| La_rumba_del_coronavirus_-_Rich_Don_Jeri | es | 187 | — | 0.029 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 0.0 % | — | 44.2 |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | — | 0.020 | 100.0 % | 100.0 % | 94.1 % | manual | 0.0 % | 24.2 % | — | 43.7 (caché) |  |
| Le_royaume_des_glous_glous_-_Raoul_de_QSM | fr | 163 | — | 0.031 | 100.0 % | 100.0 % | 96.5 % | manual | 0.0 % | 27.0 % | — | 38.7 |  |
| Les_files_d'attente_-_Law' | fr | 196 | — | 0.026 | 99.5 % | 99.5 % | 66.5 % | manual | 0.0 % | 22.5 % | — | 46.1 |  |
| Libre_by_CybeR_AttaCK_-_CyberAttacK | fr | 217 | — | 0.025 | 99.2 % | 99.5 % | 98.5 % | manual | 0.0 % | 59.9 % | — | 51.5 |  |
| Lower_Loveday_-_Is_It_Right_ | en | 180 | — | 0.057 | 99.5 % | 99.5 % | 97.6 % | manual | 0.0 % | 22.0 % | — | 42.6 |  |
| Mes_Larmes_-_kobzx2z | fr | 159 | — | 0.025 | 98.3 % | 99.3 % | 75.5 % | manual | 0.0 % | 30.3 % | — | 37.4 |  |
| Moon_I_Mean_-_Wrong_Concept | en | 220 | — | 0.053 | 99.6 % | 99.6 % | 95.2 % | manual | 0.0 % | 23.5 % | — | 51.6 |  |
| Musik_-_Heiko | de | 295 | — | 0.041 | 100.0 % | 100.0 % | 94.1 % | manual | 0.0 % | 13.9 % | — | 69.4 |  |
| Mère_nature_-_Law' | fr | 225 | — | 0.025 | 100.0 % | 100.0 % | 96.5 % | manual | 0.0 % | 6.3 % | — | 53.1 (caché) |  |
| POIGNEE_DE_MAIN_-_Cabbac | fr | 209 | — | 0.027 | 100.0 % | 100.0 % | 90.4 % | manual | 0.0 % | 21.4 % | — | 49.0 |  |
| Palabras_-_Javier_Gomez_Bello | es | 216 | — | 0.043 | 100.0 % | 100.0 % | 99.5 % | manual | 0.0 % | 37.7 % | — | 50.7 |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | — | 0.026 | 100.0 % | 100.0 % | 88.1 % | manual | 0.0 % | 32.2 % | — | 47.6 (caché) |  |
| Pluie_d'entre_deux_saisons_-_Midnight_Prefou | fr | 205 | — | 0.037 | 87.2 % | 88.0 % | 93.3 % | manual | 0.0 % | 14.9 % | — | 47.9 |  |
| Pure_Mids_-_The_Leader | en | 262 | — | 0.092 | 100.0 % | 100.0 % | 71.9 % | manual | 1.1 % | 23.9 % | — | 61.5 |  |
| Quentin_Hannappe_-_Keep_On | en | 190 | — | 0.042 | 100.0 % | 100.0 % | 96.0 % | manual | 0.1 % | 40.3 % | — | 44.8 |  |
| Quiero_y_Puedo_-_Nacidos_de_la_Tierra | es | 236 | — | 0.022 | 100.0 % | 100.0 % | 99.8 % | manual | 0.0 % | 5.4 % | — | 57.3 |  |
| Ridgway_-_Fire_Inside | en | 284 | — | 0.045 | 93.3 % | 93.3 % | 73.4 % | manual | 0.0 % | 40.7 % | — | 66.0 (caché) |  |
| Rxbyn_-_Bad_Side | en | 217 | — | 0.045 | 99.5 % | 99.5 % | 95.2 % | manual | 0.0 % | 17.6 % | — | 51.9 |  |
| SHANEY_23_feat._G1NA_G._x_In_den_Strassen_-_Shaney_23 | de | 211 | — | 0.054 | 98.6 % | 99.8 % | 92.6 % | manual | 0.0 % | 20.9 % | — | 50.2 |  |
| Schnodderdodder_-_Abendblau | de | 197 | — | 0.027 | 99.3 % | 100.0 % | 95.9 % | manual | 0.0 % | 16.4 % | — | 47.1 |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | — | 0.038 | 100.0 % | 100.0 % | 96.0 % | manual | 0.0 % | 41.1 % | — | 54.9 (caché) |  |
| Sin_miedo_-_Living_Camboya | es | 223 | — | 0.025 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 17.0 % | — | 52.9 |  |
| Slingshot_Miracle_-_Whistler | en | 229 | — | 0.094 | 98.1 % | 98.1 % | 98.8 % | manual | 0.0 % | 8.6 % | — | 54.1 |  |
| Songwriterz_-_Back_In_Time | en | 209 | — | 0.066 | 96.8 % | 96.8 % | 92.0 % | manual | 0.0 % | 15.5 % | — | 49.4 |  |
| Séculaire_feat._Nÿme_-_saru | fr | 159 | — | 0.023 | 98.7 % | 98.7 % | 88.7 % | manual | 0.3 % | 21.9 % | — | 37.4 |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | — | 0.028 | 99.8 % | 100.0 % | 98.3 % | manual | 0.0 % | 6.6 % | — | 46.1 (caché) |  |
| The.madpix.project_-_One_Way_Street | en | 171 | — | 0.062 | 98.3 % | 99.4 % | 95.1 % | manual | 0.5 % | 29.3 % | — | 40.0 |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | — | 0.075 | 98.4 % | 99.5 % | 95.1 % | manual | 0.0 % | 35.7 % | — | 53.6 (caché) |  |
| Tom_Orlando_-_The_One__feat._Tina_G_ | en | 240 | — | 0.034 | 97.6 % | 97.8 % | 91.6 % | manual | 0.1 % | 15.6 % | — | 58.2 |  |
| Une_Vie_De_Roi_-_david | fr | 303 | — | 0.023 | 100.0 % | 100.0 % | 96.1 % | manual | 0.0 % | 48.9 % | — | 72.3 |  |
| Vente_-_Fafarulo_Calabaza | es | 336 | — | 0.029 | 99.6 % | 99.6 % | 97.8 % | manual | 0.0 % | 32.4 % | — | 80.6 |  |
| Veränderung_-_doromusis | de | 194 | — | 0.045 | 99.5 % | 99.5 % | 90.5 % | manual | 0.0 % | 22.6 % | — | 45.6 |  |
| Wordsmith_-_The_Statement | en | 171 | — | 0.036 | 100.0 % | 100.0 % | 90.7 % | manual | 0.0 % | 22.7 % | — | 39.9 (caché) |  |
| Yuanan_-_Miedo_-_Yuanan | es | 169 | — | 0.025 | 100.0 % | 100.0 % | 91.0 % | manual | 0.0 % | 11.0 % | — | 40.3 |  |
| de_bonne_humeur_-_Le_Nez_Tordu | fr | 161 | — | 0.024 | 100.0 % | 100.0 % | 97.0 % | manual | 0.0 % | 31.0 % | — | 38.5 |  |
| dich_gehen_zu_sehn._-_Wingenbach_Frank | de | 193 | — | 0.036 | 98.3 % | 100.0 % | 97.8 % | manual | 0.0 % | 30.8 % | — | 45.6 |  |
| l'abandon_-_flo | fr | 210 | — | 0.026 | 100.0 % | 100.0 % | 86.2 % | manual | 0.0 % | 10.3 % | — | 49.6 |  |
| te_amo_-_fabios_la_nueva_expresion_de_la_cancion | es | 195 | — | 0.035 | 100.0 % | 100.0 % | 99.4 % | manual | 0.0 % | 21.3 % | — | 45.5 |  |
| ¡Óyeme_tiburón!_-_Corrientes | es | 180 | — | 0.026 | 100.0 % | 100.0 % | 98.1 % | manual | 0.1 % | 14.3 % | — | 42.5 |  |

## Peores casos

Mayor mediana de error de inicio:
- Color_Out_-_Falling_Star: 0.160 s
- Avercage_-_Embers: 0.156 s
- Da_wurdest_du_geboren_-_Alice_Tlustos_: 0.097 s
- Slingshot_Miracle_-_Whistler: 0.094 s
- Pure_Mids_-_The_Leader: 0.092 s

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
