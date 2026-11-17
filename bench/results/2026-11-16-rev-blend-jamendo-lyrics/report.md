# Banco · rev-blend · jamendo · con letra

- Fecha: 2026-11-16T18:40:28+01:00
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

Mel-Band RoFormer (Kim, 8 s) + Whisper + lyrics aligner (each language's CTC model averaged with w2v-BERT 2.0 music lyrics CTC)

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt', 'segment_size': 801}
- **transcriber**: `karaoke_engine.transcribe:WhisperTranscriber` v5
- **segmenter**: `karaoke_engine.transcribe:LineSegmenter` v2
- **aligner**: `karaoke_engine.align.aligner:LyricsAligner` v14 {'second': 'music-w2vbert-ctc'}

## Resumen

| Grupo | Canciones | Fallos | WER | WER tolerante | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| de | 20 | 0 | — | — | — | 0.029 | 0.048 | 99.6 % | 99.9 % | 0.085 | 0.028 | 96.0 % | — | 0 | 66 | 0.0 % | 14.6 % |
| en | 20 | 0 | — | — | — | 0.057 | 0.110 | 98.6 % | 98.9 % | 0.082 | 0.065 | 92.5 % | — | 0 | 69 | 0.1 % | 24.0 % |
| es | 20 | 0 | — | — | — | 0.027 | 0.036 | 99.8 % | 99.9 % | 0.111 | 0.005 | 96.5 % | — | 0 | 69 | 0.0 % | 12.7 % |
| fr | 19 | 0 | — | — | — | 0.029 | 0.067 | 99.0 % | 99.2 % | 0.093 | -0.020 | 87.2 % | — | 0 | 69 | 0.0 % | 21.5 % |
| total | 79 | 0 | — | — | — | 0.034 | 0.066 | 99.2 % | 99.5 % | 0.093 | 0.020 | 93.0 % | — | 0 | 69 | 0.0 % | 18.2 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 7.2 | 2867 | 2388 | 0.204 |
| aligner | 0.1 | 3335 | 5520 | 0.052 |

## Por canción

| Canción | Idioma | Duración | WER | WER tolerante | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10._Disparan_-_criatura | es | 160 | — | — | 0.024 | 99.5 % | 100.0 % | 100.0 % | manual | 0.0 % | 18.0 % | — | 41.6 (caché) |  |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | — | — | 0.048 | 100.0 % | 100.0 % | 97.8 % | manual | 0.0 % | 11.7 % | — | 57.9 (caché) |  |
| Avercage_-_Embers | en | 243 | — | — | 0.156 | 89.4 % | 92.6 % | 100.0 % | manual | 0.0 % | 77.1 % | — | 63.3 |  |
| Baila_-_Alfonso_Lugo | es | 210 | — | — | 0.019 | 100.0 % | 100.0 % | 98.2 % | manual | 0.0 % | 23.6 % | — | 51.3 (caché) |  |
| Besando_Sapos_-_Dream_Tabu | es | 251 | — | — | 0.029 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 17.5 % | — | 65.1 |  |
| Bitte_beweg_dich_nicht_-_Bukto | de | 273 | — | — | 0.038 | 100.0 % | 100.0 % | 98.9 % | manual | 0.0 % | 19.5 % | — | 81.8 (caché) |  |
| Burn_Out_Man_-_Abendblau | de | 260 | — | — | 0.039 | 100.0 % | 100.0 % | 86.7 % | manual | 0.0 % | 7.3 % | — | 63.6 (caché) |  |
| CHRISTMAS_AVEC_TOI_-_imfreshyourepretty | fr | 234 | — | — | 0.034 | 100.0 % | 100.0 % | 64.3 % | manual | 0.0 % | 28.7 % | — | 62.3 |  |
| CLUB_DESTINO__-_Pensando_en_ti_-_CLUB_DESTINO | es | 219 | — | — | 0.038 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 10.2 % | — | 55.6 |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | — | — | 0.055 | 98.9 % | 100.0 % | 94.6 % | manual | 0.0 % | 17.2 % | — | 59.9 (caché) |  |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | — | — | 0.024 | 100.0 % | 100.0 % | 97.6 % | manual | 0.0 % | 8.5 % | — | 48.6 (caché) |  |
| Caralibro_-_Vagos_Permanentes | es | 279 | — | — | 0.029 | 100.0 % | 100.0 % | 99.5 % | manual | 0.0 % | 22.2 % | — | 70.7 |  |
| Color_Out_-_Falling_Star | en | 222 | — | — | 0.162 | 97.7 % | 98.6 % | 95.5 % | manual | 0.0 % | 32.4 % | — | 56.9 |  |
| Confession_-_Quesabe | fr | 148 | — | — | 0.030 | 99.3 % | 99.3 % | 87.2 % | manual | 0.2 % | 20.1 % | — | 35.9 (caché) |  |
| Cortez_-_Feel__Stripped_ | en | 241 | — | — | 0.074 | 100.0 % | 100.0 % | 98.9 % | manual | 0.0 % | 8.5 % | — | 59.2 (caché) |  |
| Culture_&_Co._-_cool.cavemen | fr | 212 | — | — | 0.032 | 98.4 % | 98.4 % | 93.9 % | manual | 0.4 % | 58.6 % | — | 55.7 |  |
| DON_VALDES_-_Tu_sais_Man | fr | 209 | — | — | 0.026 | 97.3 % | 97.8 % | 80.2 % | manual | 0.0 % | 28.9 % | — | 54.4 |  |
| Da_wurdest_du_geboren_-_Alice_Tlustos_ | de | 207 | — | — | 0.053 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 2.7 % | — | 50.1 (caché) |  |
| Der_Baum_-_Dienstag_is_Damensauna_(2) | de | 209 | — | — | 0.026 | 100.0 % | 100.0 % | 97.7 % | manual | 0.0 % | 14.9 % | — | 51.2 (caché) |  |
| Der_Musiker_-_d-music | de | 271 | — | — | 0.020 | 99.1 % | 99.4 % | 98.0 % | manual | 0.0 % | 11.3 % | — | 66.8 (caché) |  |
| Die_Revolution_gehört_Dir!_-_partysahnen | de | 167 | — | — | 0.026 | 100.0 % | 100.0 % | 98.7 % | manual | 0.0 % | 46.6 % | — | 40.5 (caché) |  |
| Diosa_de_la_noche_-_Brunela_Crochenci | es | 230 | — | — | 0.031 | 100.0 % | 100.0 % | 91.0 % | manual | 0.1 % | 11.7 % | — | 58.1 |  |
| Drei_Nüsse_-_patrouille | de | 259 | — | — | 0.026 | 100.0 % | 100.0 % | 98.5 % | manual | 0.0 % | 4.6 % | — | 63.7 (caché) |  |
| En_liberté_-_tom.leyak | fr | 234 | — | — | 0.032 | 100.0 % | 100.0 % | 94.0 % | manual | 0.0 % | 14.0 % | — | 59.4 |  |
| Esencia_-_NandoMalo_ | es | 262 | — | — | 0.024 | 99.7 % | 100.0 % | 98.2 % | manual | 0.0 % | 13.5 % | — | 64.2 (caché) |  |
| Explosive_Ear_Candy_-_Like_The_Sun | en | 193 | — | — | 0.049 | 100.0 % | 100.0 % | 99.6 % | manual | 0.0 % | 16.7 % | — | 49.8 |  |
| Fantasma_-_Los_Rombos | es | 166 | — | — | 0.056 | 92.3 % | 96.2 % | 88.6 % | manual | 0.5 % | 24.7 % | — | 42.5 |  |
| Freifliegen_-_durch.dick.und.duenn | de | 250 | — | — | 0.038 | 100.0 % | 100.0 % | 97.8 % | manual | 0.0 % | 7.4 % | — | 61.6 (caché) |  |
| Fußabdrücke_-_Andreas_Jachmann | de | 241 | — | — | 0.021 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 1.9 % | — | 59.5 (caché) |  |
| Guayeteo_-_JhoyKing | es | 158 | — | — | 0.024 | 100.0 % | 100.0 % | 84.7 % | manual | 0.0 % | 15.3 % | — | 41.1 |  |
| HILA_-_Give_Me_the_Same | en | 234 | — | — | 0.066 | 99.3 % | 99.3 % | 93.2 % | manual | 0.0 % | 17.9 % | — | 59.6 |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | — | — | 0.027 | 100.0 % | 100.0 % | 99.1 % | manual | 0.0 % | 26.4 % | — | 51.8 (caché) |  |
| Ich_kann_dich_nicht_vergessen_-_Wingenbach_Frank | de | 258 | — | — | 0.031 | 100.0 % | 100.0 % | 95.5 % | manual | 0.0 % | 10.6 % | — | 62.8 (caché) |  |
| Intentando_Destacar_-_Sundayers_ | es | 220 | — | — | 0.023 | 100.0 % | 100.0 % | 81.2 % | manual | 0.0 % | 21.9 % | — | 57.5 |  |
| Intro_[Pulsschlag]_-_Zeugen_der_Leere_(2) | de | 157 | — | — | 0.038 | 96.3 % | 98.8 % | 100.0 % | manual | 0.0 % | 58.5 % | — | 38.5 (caché) |  |
| JASON_MILLER_-_CROWD_PLEASER | en | 193 | — | — | 0.045 | 99.8 % | 99.8 % | 83.1 % | manual | 0.1 % | 8.2 % | — | 50.6 |  |
| Keine_Lust_-_Jonny_M | de | 229 | — | — | 0.016 | 100.0 % | 100.0 % | 95.8 % | manual | 0.0 % | 1.5 % | — | 56.9 (caché) |  |
| Kinematic_-_Peyote | en | 183 | — | — | 0.053 | 100.0 % | 100.0 % | 93.9 % | manual | 0.3 % | 20.3 % | — | 49.0 (caché) |  |
| LUNABLIND_-_Vision__Radio_Edit_ | en | 221 | — | — | 0.064 | 99.0 % | 99.0 % | 99.7 % | manual | 0.0 % | 7.1 % | — | 57.1 |  |
| La_rumba_del_coronavirus_-_Rich_Don_Jeri | es | 187 | — | — | 0.028 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 0.4 % | — | 49.4 |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | — | — | 0.020 | 100.0 % | 100.0 % | 94.1 % | manual | 0.0 % | 8.3 % | — | 45.5 (caché) |  |
| Le_royaume_des_glous_glous_-_Raoul_de_QSM | fr | 163 | — | — | 0.034 | 100.0 % | 100.0 % | 96.5 % | manual | 0.0 % | 22.0 % | — | 42.4 |  |
| Les_files_d'attente_-_Law' | fr | 196 | — | — | 0.031 | 99.5 % | 99.5 % | 66.5 % | manual | 0.0 % | 20.6 % | — | 50.4 |  |
| Libre_by_CybeR_AttaCK_-_CyberAttacK | fr | 217 | — | — | 0.029 | 99.2 % | 100.0 % | 98.5 % | manual | 0.0 % | 37.9 % | — | 56.1 |  |
| Lower_Loveday_-_Is_It_Right_ | en | 180 | — | — | 0.060 | 99.0 % | 99.5 % | 97.2 % | manual | 0.0 % | 8.5 % | — | 46.9 |  |
| Mes_Larmes_-_kobzx2z | fr | 159 | — | — | 0.025 | 98.3 % | 99.3 % | 75.5 % | manual | 0.0 % | 34.8 % | — | 41.1 |  |
| Moon_I_Mean_-_Wrong_Concept | en | 220 | — | — | 0.052 | 99.6 % | 99.6 % | 95.2 % | manual | 0.0 % | 29.7 % | — | 56.1 |  |
| Musik_-_Heiko | de | 295 | — | — | 0.027 | 100.0 % | 100.0 % | 94.1 % | manual | 0.0 % | 2.5 % | — | 72.6 (caché) |  |
| Mère_nature_-_Law' | fr | 225 | — | — | 0.036 | 100.0 % | 100.0 % | 96.5 % | manual | 0.0 % | 6.7 % | — | 55.2 (caché) |  |
| POIGNEE_DE_MAIN_-_Cabbac | fr | 209 | — | — | 0.031 | 99.2 % | 99.2 % | 90.4 % | manual | 0.0 % | 15.9 % | — | 53.3 |  |
| Palabras_-_Javier_Gomez_Bello | es | 216 | — | — | 0.028 | 100.0 % | 100.0 % | 99.5 % | manual | 0.0 % | 3.8 % | — | 56.3 |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | — | — | 0.031 | 100.0 % | 100.0 % | 88.1 % | manual | 0.0 % | 32.3 % | — | 49.5 (caché) |  |
| Pluie_d'entre_deux_saisons_-_Midnight_Prefou | fr | 205 | — | — | 0.048 | 84.8 % | 85.6 % | 93.3 % | manual | 0.2 % | 20.9 % | — | 52.1 |  |
| Pure_Mids_-_The_Leader | en | 262 | — | — | 0.079 | 100.0 % | 100.0 % | 71.9 % | manual | 0.9 % | 51.3 % | — | 66.2 |  |
| Quentin_Hannappe_-_Keep_On | en | 190 | — | — | 0.045 | 100.0 % | 100.0 % | 96.0 % | manual | 0.0 % | 25.6 % | — | 49.2 |  |
| Quiero_y_Puedo_-_Nacidos_de_la_Tierra | es | 236 | — | — | 0.027 | 100.0 % | 100.0 % | 99.8 % | manual | 0.0 % | 3.3 % | — | 62.4 |  |
| Ridgway_-_Fire_Inside | en | 284 | — | — | 0.046 | 93.2 % | 93.6 % | 77.0 % | manual | 0.0 % | 28.6 % | — | 68.8 (caché) |  |
| Rxbyn_-_Bad_Side | en | 217 | — | — | 0.051 | 99.5 % | 99.5 % | 95.2 % | manual | 0.0 % | 15.3 % | — | 56.7 |  |
| SHANEY_23_feat._G1NA_G._x_In_den_Strassen_-_Shaney_23 | de | 211 | — | — | 0.045 | 98.1 % | 100.0 % | 92.6 % | manual | 0.0 % | 17.3 % | — | 52.3 (caché) |  |
| Schnodderdodder_-_Abendblau | de | 197 | — | — | 0.022 | 99.3 % | 100.0 % | 95.9 % | manual | 0.0 % | 11.6 % | — | 49.0 (caché) |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | — | — | 0.029 | 100.0 % | 100.0 % | 96.0 % | manual | 0.0 % | 16.6 % | — | 57.3 (caché) |  |
| Sin_miedo_-_Living_Camboya | es | 223 | — | — | 0.026 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 7.6 % | — | 57.4 |  |
| Slingshot_Miracle_-_Whistler | en | 229 | — | — | 0.072 | 99.4 % | 100.0 % | 98.8 % | manual | 0.0 % | 14.1 % | — | 60.9 |  |
| Songwriterz_-_Back_In_Time | en | 209 | — | — | 0.056 | 97.3 % | 97.3 % | 92.0 % | manual | 0.0 % | 22.4 % | — | 54.9 |  |
| Séculaire_feat._Nÿme_-_saru | fr | 159 | — | — | 0.024 | 98.7 % | 98.7 % | 88.4 % | manual | 0.1 % | 20.8 % | — | 41.1 |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | — | — | 0.029 | 99.8 % | 100.0 % | 98.3 % | manual | 0.0 % | 8.3 % | — | 47.8 (caché) |  |
| The.madpix.project_-_One_Way_Street | en | 171 | — | — | 0.060 | 99.4 % | 99.4 % | 95.1 % | manual | 0.0 % | 16.7 % | — | 43.9 |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | — | — | 0.069 | 98.9 % | 100.0 % | 93.6 % | manual | 0.0 % | 34.7 % | — | 55.9 (caché) |  |
| Tom_Orlando_-_The_One__feat._Tina_G_ | en | 240 | — | — | 0.038 | 97.8 % | 98.0 % | 91.4 % | manual | 0.1 % | 21.3 % | — | 62.9 |  |
| Une_Vie_De_Roi_-_david | fr | 303 | — | — | 0.030 | 100.0 % | 100.0 % | 96.1 % | manual | 0.0 % | 4.9 % | — | 78.5 |  |
| Vente_-_Fafarulo_Calabaza | es | 336 | — | — | 0.032 | 99.6 % | 99.6 % | 97.8 % | manual | 0.0 % | 5.7 % | — | 87.2 |  |
| Veränderung_-_doromusis | de | 194 | — | — | 0.033 | 99.0 % | 99.5 % | 90.5 % | manual | 0.0 % | 15.6 % | — | 56.4 |  |
| Wordsmith_-_The_Statement | en | 171 | — | — | 0.047 | 100.0 % | 100.0 % | 90.5 % | manual | 0.0 % | 24.1 % | — | 41.7 (caché) |  |
| Yuanan_-_Miedo_-_Yuanan | es | 169 | — | — | 0.026 | 100.0 % | 100.0 % | 91.0 % | manual | 0.0 % | 9.0 % | — | 44.8 |  |
| de_bonne_humeur_-_Le_Nez_Tordu | fr | 161 | — | — | 0.029 | 100.0 % | 100.0 % | 97.0 % | manual | 0.0 % | 14.9 % | — | 42.9 |  |
| dich_gehen_zu_sehn._-_Wingenbach_Frank | de | 193 | — | — | 0.030 | 99.4 % | 100.0 % | 97.8 % | manual | 0.0 % | 12.6 % | — | 50.4 |  |
| l'abandon_-_flo | fr | 210 | — | — | 0.028 | 100.0 % | 100.0 % | 86.2 % | manual | 0.0 % | 10.0 % | — | 54.8 |  |
| te_amo_-_fabios_la_nueva_expresion_de_la_cancion | es | 195 | — | — | 0.032 | 100.0 % | 100.0 % | 99.4 % | manual | 0.0 % | 6.5 % | — | 49.8 |  |
| ¡Óyeme_tiburón!_-_Corrientes | es | 180 | — | — | 0.028 | 100.0 % | 100.0 % | 98.1 % | manual | 0.0 % | 3.3 % | — | 46.9 |  |

## Peores casos

Mayor mediana de error de inicio:
- Color_Out_-_Falling_Star: 0.162 s
- Avercage_-_Embers: 0.156 s
- Pure_Mids_-_The_Leader: 0.079 s
- Cortez_-_Feel__Stripped_: 0.074 s
- Slingshot_Miracle_-_Whistler: 0.072 s

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
