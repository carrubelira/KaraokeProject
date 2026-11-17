# Banco · rev-final-b · jamendo · con letra

- Fecha: 2026-11-17T05:21:38+01:00
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

Mel-Band RoFormer (Kim, 8 s) + Whisper + lyrics aligner (each language's CTC model averaged with the music model, which weighs 0.3; resting between words of a line costs 0.05 per silent frame)

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt', 'segment_size': 801}
- **transcriber**: `karaoke_engine.transcribe:WhisperTranscriber` v5
- **segmenter**: `karaoke_engine.transcribe:LineSegmenter` v2
- **aligner**: `karaoke_engine.align.aligner:LyricsAligner` v14 {'second': 'music-w2vbert-ctc', 'second_weight': 0.3, 'rest_penalty': 0.05}

## Resumen

| Grupo | Canciones | Fallos | WER | WER tolerante | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| de | 20 | 0 | — | — | — | 0.029 | 0.046 | 99.6 % | 100.0 % | 0.076 | 0.026 | 95.9 % | — | 0 | 69 | 0.0 % | 15.3 % |
| en | 20 | 0 | — | — | — | 0.057 | 0.105 | 98.6 % | 98.9 % | 0.065 | 0.064 | 92.2 % | — | 0 | 69 | 0.1 % | 34.7 % |
| es | 20 | 0 | — | — | — | 0.028 | 0.037 | 99.8 % | 99.9 % | 0.098 | 0.004 | 96.5 % | — | 0 | 69 | 0.0 % | 15.3 % |
| fr | 19 | 0 | — | — | — | 0.030 | 0.056 | 99.1 % | 99.3 % | 0.086 | -0.018 | 87.2 % | — | 0 | 70 | 0.0 % | 25.9 % |
| total | 79 | 0 | — | — | — | 0.034 | 0.062 | 99.3 % | 99.5 % | 0.082 | 0.020 | 92.9 % | — | 0 | 69 | 0.0 % | 22.8 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 7.2 | 2867 | 2388 | 0.204 |
| aligner | 0.1 | 2133 | 4062 | 0.054 |

## Por canción

| Canción | Idioma | Duración | WER | WER tolerante | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10._Disparan_-_criatura | es | 160 | — | — | 0.024 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 22.7 % | — | 42.1 (caché) |  |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | — | — | 0.044 | 100.0 % | 100.0 % | 97.8 % | manual | 0.0 % | 21.0 % | — | 59.7 (caché) |  |
| Avercage_-_Embers | en | 243 | — | — | 0.142 | 89.3 % | 93.6 % | 98.9 % | manual | 0.0 % | 91.1 % | — | 63.6 |  |
| Baila_-_Alfonso_Lugo | es | 210 | — | — | 0.019 | 100.0 % | 100.0 % | 98.2 % | manual | 0.0 % | 24.6 % | — | 54.0 (caché) |  |
| Besando_Sapos_-_Dream_Tabu | es | 251 | — | — | 0.031 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 19.3 % | — | 65.7 |  |
| Bitte_beweg_dich_nicht_-_Bukto | de | 273 | — | — | 0.036 | 100.0 % | 100.0 % | 98.9 % | manual | 0.0 % | 21.8 % | — | 81.5 |  |
| Burn_Out_Man_-_Abendblau | de | 260 | — | — | 0.039 | 100.0 % | 100.0 % | 86.7 % | manual | 0.0 % | 6.7 % | — | 66.9 |  |
| CHRISTMAS_AVEC_TOI_-_imfreshyourepretty | fr | 234 | — | — | 0.035 | 99.6 % | 99.6 % | 64.3 % | manual | 0.0 % | 43.4 % | — | 61.9 |  |
| CLUB_DESTINO__-_Pensando_en_ti_-_CLUB_DESTINO | es | 219 | — | — | 0.037 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 10.7 % | — | 56.3 |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | — | — | 0.054 | 98.9 % | 100.0 % | 94.6 % | manual | 0.0 % | 14.0 % | — | 62.6 (caché) |  |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | — | — | 0.024 | 100.0 % | 100.0 % | 97.6 % | manual | 0.0 % | 7.7 % | — | 49.4 (caché) |  |
| Caralibro_-_Vagos_Permanentes | es | 279 | — | — | 0.029 | 100.0 % | 100.0 % | 99.5 % | manual | 0.0 % | 24.1 % | — | 70.8 |  |
| Color_Out_-_Falling_Star | en | 222 | — | — | 0.152 | 97.7 % | 98.6 % | 95.5 % | manual | 0.0 % | 39.8 % | — | 57.0 |  |
| Confession_-_Quesabe | fr | 148 | — | — | 0.029 | 99.3 % | 99.3 % | 87.2 % | manual | 0.2 % | 28.5 % | — | 38.6 (caché) |  |
| Cortez_-_Feel__Stripped_ | en | 241 | — | — | 0.067 | 100.0 % | 100.0 % | 98.9 % | manual | 0.0 % | 12.4 % | — | 61.9 (caché) |  |
| Culture_&_Co._-_cool.cavemen | fr | 212 | — | — | 0.032 | 98.4 % | 99.2 % | 93.9 % | manual | 0.0 % | 62.3 % | — | 55.4 |  |
| DON_VALDES_-_Tu_sais_Man | fr | 209 | — | — | 0.027 | 97.3 % | 97.5 % | 79.8 % | manual | 0.0 % | 42.0 % | — | 54.6 |  |
| Da_wurdest_du_geboren_-_Alice_Tlustos_ | de | 207 | — | — | 0.051 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 5.4 % | — | 52.5 |  |
| Der_Baum_-_Dienstag_is_Damensauna_(2) | de | 209 | — | — | 0.027 | 100.0 % | 100.0 % | 97.7 % | manual | 0.0 % | 11.3 % | — | 54.0 |  |
| Der_Musiker_-_d-music | de | 271 | — | — | 0.021 | 99.7 % | 100.0 % | 97.2 % | manual | 0.0 % | 11.1 % | — | 70.1 (caché) |  |
| Die_Revolution_gehört_Dir!_-_partysahnen | de | 167 | — | — | 0.026 | 100.0 % | 100.0 % | 98.7 % | manual | 0.0 % | 46.0 % | — | 42.9 |  |
| Diosa_de_la_noche_-_Brunela_Crochenci | es | 230 | — | — | 0.030 | 100.0 % | 100.0 % | 91.0 % | manual | 0.0 % | 18.0 % | — | 58.5 |  |
| Drei_Nüsse_-_patrouille | de | 259 | — | — | 0.026 | 100.0 % | 100.0 % | 98.5 % | manual | 0.0 % | 4.6 % | — | 66.5 |  |
| En_liberté_-_tom.leyak | fr | 234 | — | — | 0.032 | 99.6 % | 100.0 % | 94.0 % | manual | 0.0 % | 17.4 % | — | 59.7 |  |
| Esencia_-_NandoMalo_ | es | 262 | — | — | 0.023 | 100.0 % | 100.0 % | 98.2 % | manual | 0.0 % | 18.0 % | — | 66.9 (caché) |  |
| Explosive_Ear_Candy_-_Like_The_Sun | en | 193 | — | — | 0.049 | 100.0 % | 100.0 % | 99.6 % | manual | 0.0 % | 29.5 % | — | 50.1 |  |
| Fantasma_-_Los_Rombos | es | 166 | — | — | 0.050 | 93.6 % | 97.4 % | 88.6 % | manual | 0.6 % | 25.8 % | — | 42.8 |  |
| Freifliegen_-_durch.dick.und.duenn | de | 250 | — | — | 0.032 | 100.0 % | 100.0 % | 97.8 % | manual | 0.0 % | 8.9 % | — | 64.0 |  |
| Fußabdrücke_-_Andreas_Jachmann | de | 241 | — | — | 0.023 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 1.3 % | — | 62.2 |  |
| Guayeteo_-_JhoyKing | es | 158 | — | — | 0.027 | 99.7 % | 100.0 % | 84.7 % | manual | 0.0 % | 21.7 % | — | 41.4 |  |
| HILA_-_Give_Me_the_Same | en | 234 | — | — | 0.061 | 99.3 % | 99.3 % | 93.2 % | manual | 0.0 % | 26.5 % | — | 60.0 |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | — | — | 0.030 | 100.0 % | 100.0 % | 99.1 % | manual | 0.0 % | 27.4 % | — | 54.5 (caché) |  |
| Ich_kann_dich_nicht_vergessen_-_Wingenbach_Frank | de | 258 | — | — | 0.030 | 100.0 % | 100.0 % | 95.5 % | manual | 0.0 % | 10.6 % | — | 65.4 |  |
| Intentando_Destacar_-_Sundayers_ | es | 220 | — | — | 0.023 | 100.0 % | 100.0 % | 81.2 % | manual | 0.0 % | 19.2 % | — | 56.9 |  |
| Intro_[Pulsschlag]_-_Zeugen_der_Leere_(2) | de | 157 | — | — | 0.039 | 95.1 % | 98.8 % | 100.0 % | manual | 0.0 % | 53.7 % | — | 40.9 |  |
| JASON_MILLER_-_CROWD_PLEASER | en | 193 | — | — | 0.048 | 99.8 % | 99.8 % | 83.1 % | manual | 0.1 % | 10.4 % | — | 50.8 |  |
| Keine_Lust_-_Jonny_M | de | 229 | — | — | 0.016 | 100.0 % | 100.0 % | 95.8 % | manual | 0.0 % | 4.4 % | — | 59.7 (caché) |  |
| Kinematic_-_Peyote | en | 183 | — | — | 0.050 | 100.0 % | 100.0 % | 93.9 % | manual | 0.2 % | 30.8 % | — | 48.0 (caché) |  |
| LUNABLIND_-_Vision__Radio_Edit_ | en | 221 | — | — | 0.064 | 99.3 % | 99.3 % | 99.7 % | manual | 0.0 % | 11.5 % | — | 57.3 |  |
| La_rumba_del_coronavirus_-_Rich_Don_Jeri | es | 187 | — | — | 0.028 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 4.9 % | — | 48.6 |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | — | — | 0.022 | 100.0 % | 100.0 % | 94.1 % | manual | 0.0 % | 9.1 % | — | 48.0 (caché) |  |
| Le_royaume_des_glous_glous_-_Raoul_de_QSM | fr | 163 | — | — | 0.035 | 100.0 % | 100.0 % | 96.5 % | manual | 0.0 % | 22.0 % | — | 42.7 |  |
| Les_files_d'attente_-_Law' | fr | 196 | — | — | 0.030 | 99.5 % | 99.5 % | 66.5 % | manual | 0.0 % | 29.6 % | — | 50.5 |  |
| Libre_by_CybeR_AttaCK_-_CyberAttacK | fr | 217 | — | — | 0.029 | 99.2 % | 100.0 % | 98.5 % | manual | 0.0 % | 35.2 % | — | 56.4 |  |
| Lower_Loveday_-_Is_It_Right_ | en | 180 | — | — | 0.057 | 99.5 % | 99.5 % | 96.7 % | manual | 0.0 % | 17.0 % | — | 46.8 |  |
| Mes_Larmes_-_kobzx2z | fr | 159 | — | — | 0.024 | 98.3 % | 99.3 % | 75.5 % | manual | 0.0 % | 41.8 % | — | 41.5 |  |
| Moon_I_Mean_-_Wrong_Concept | en | 220 | — | — | 0.052 | 99.6 % | 99.6 % | 95.2 % | manual | 0.0 % | 54.5 % | — | 56.3 |  |
| Musik_-_Heiko | de | 295 | — | — | 0.027 | 100.0 % | 100.0 % | 94.1 % | manual | 0.0 % | 3.8 % | — | 74.8 |  |
| Mère_nature_-_Law' | fr | 225 | — | — | 0.037 | 100.0 % | 100.0 % | 96.5 % | manual | 0.0 % | 13.9 % | — | 57.9 (caché) |  |
| POIGNEE_DE_MAIN_-_Cabbac | fr | 209 | — | — | 0.033 | 99.2 % | 99.2 % | 90.4 % | manual | 0.0 % | 16.6 % | — | 53.5 |  |
| Palabras_-_Javier_Gomez_Bello | es | 216 | — | — | 0.031 | 100.0 % | 100.0 % | 99.5 % | manual | 0.0 % | 4.2 % | — | 55.6 |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | — | — | 0.034 | 100.0 % | 100.0 % | 88.1 % | manual | 0.0 % | 34.6 % | — | 52.1 (caché) |  |
| Pluie_d'entre_deux_saisons_-_Midnight_Prefou | fr | 205 | — | — | 0.045 | 91.2 % | 91.2 % | 93.3 % | manual | 0.0 % | 31.3 % | — | 52.5 |  |
| Pure_Mids_-_The_Leader | en | 262 | — | — | 0.077 | 100.0 % | 100.0 % | 71.9 % | manual | 0.6 % | 78.8 % | — | 66.7 |  |
| Quentin_Hannappe_-_Keep_On | en | 190 | — | — | 0.044 | 100.0 % | 100.0 % | 96.0 % | manual | 0.0 % | 23.6 % | — | 49.4 |  |
| Quiero_y_Puedo_-_Nacidos_de_la_Tierra | es | 236 | — | — | 0.027 | 100.0 % | 100.0 % | 99.8 % | manual | 0.0 % | 8.9 % | — | 62.3 |  |
| Ridgway_-_Fire_Inside | en | 284 | — | — | 0.047 | 93.2 % | 93.6 % | 77.0 % | manual | 0.0 % | 35.3 % | — | 71.4 (caché) |  |
| Rxbyn_-_Bad_Side | en | 217 | — | — | 0.053 | 99.3 % | 99.3 % | 95.2 % | manual | 0.0 % | 22.3 % | — | 56.4 |  |
| SHANEY_23_feat._G1NA_G._x_In_den_Strassen_-_Shaney_23 | de | 211 | — | — | 0.042 | 98.1 % | 100.0 % | 92.6 % | manual | 0.0 % | 23.6 % | — | 55.0 |  |
| Schnodderdodder_-_Abendblau | de | 197 | — | — | 0.022 | 99.3 % | 100.0 % | 95.9 % | manual | 0.0 % | 14.0 % | — | 51.4 |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | — | — | 0.030 | 100.0 % | 100.0 % | 96.0 % | manual | 0.0 % | 15.9 % | — | 59.7 (caché) |  |
| Sin_miedo_-_Living_Camboya | es | 223 | — | — | 0.026 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 8.2 % | — | 57.3 |  |
| Slingshot_Miracle_-_Whistler | en | 229 | — | — | 0.067 | 99.4 % | 100.0 % | 98.8 % | manual | 0.0 % | 25.2 % | — | 59.0 |  |
| Songwriterz_-_Back_In_Time | en | 209 | — | — | 0.056 | 96.3 % | 96.8 % | 92.0 % | manual | 0.0 % | 35.3 % | — | 54.0 |  |
| Séculaire_feat._Nÿme_-_saru | fr | 159 | — | — | 0.024 | 98.7 % | 98.7 % | 88.4 % | manual | 0.1 % | 23.2 % | — | 41.5 |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | — | — | 0.029 | 99.6 % | 99.8 % | 98.3 % | manual | 0.0 % | 16.2 % | — | 50.6 (caché) |  |
| The.madpix.project_-_One_Way_Street | en | 171 | — | — | 0.059 | 99.4 % | 99.4 % | 95.1 % | manual | 0.0 % | 25.3 % | — | 44.2 |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | — | — | 0.057 | 98.9 % | 100.0 % | 93.6 % | manual | 0.0 % | 45.6 % | — | 58.5 (caché) |  |
| Tom_Orlando_-_The_One__feat._Tina_G_ | en | 240 | — | — | 0.043 | 97.9 % | 97.9 % | 88.2 % | manual | 0.1 % | 44.6 % | — | 63.5 |  |
| Une_Vie_De_Roi_-_david | fr | 303 | — | — | 0.030 | 100.0 % | 100.0 % | 96.1 % | manual | 0.0 % | 4.9 % | — | 78.1 |  |
| Vente_-_Fafarulo_Calabaza | es | 336 | — | — | 0.033 | 99.6 % | 99.6 % | 97.8 % | manual | 0.0 % | 9.2 % | — | 86.2 |  |
| Veränderung_-_doromusis | de | 194 | — | — | 0.032 | 99.0 % | 99.5 % | 90.5 % | manual | 0.0 % | 17.1 % | — | 50.1 |  |
| Wordsmith_-_The_Statement | en | 171 | — | — | 0.051 | 100.0 % | 100.0 % | 90.2 % | manual | 0.0 % | 34.3 % | — | 44.2 (caché) |  |
| Yuanan_-_Miedo_-_Yuanan | es | 169 | — | — | 0.027 | 100.0 % | 100.0 % | 91.0 % | manual | 0.0 % | 11.4 % | — | 44.2 |  |
| de_bonne_humeur_-_Le_Nez_Tordu | fr | 161 | — | — | 0.030 | 99.6 % | 100.0 % | 97.0 % | manual | 0.0 % | 14.9 % | — | 42.6 |  |
| dich_gehen_zu_sehn._-_Wingenbach_Frank | de | 193 | — | — | 0.030 | 98.9 % | 100.0 % | 97.8 % | manual | 0.0 % | 11.5 % | — | 50.0 |  |
| l'abandon_-_flo | fr | 210 | — | — | 0.030 | 100.0 % | 100.0 % | 86.2 % | manual | 0.0 % | 14.3 % | — | 54.2 |  |
| te_amo_-_fabios_la_nueva_expresion_de_la_cancion | es | 195 | — | — | 0.032 | 100.0 % | 100.0 % | 99.4 % | manual | 0.0 % | 5.3 % | — | 49.8 |  |
| ¡Óyeme_tiburón!_-_Corrientes | es | 180 | — | — | 0.028 | 100.0 % | 100.0 % | 98.1 % | manual | 0.0 % | 6.2 % | — | 46.7 |  |

## Peores casos

Mayor mediana de error de inicio:
- Color_Out_-_Falling_Star: 0.152 s
- Avercage_-_Embers: 0.142 s
- Pure_Mids_-_The_Leader: 0.077 s
- Slingshot_Miracle_-_Whistler: 0.067 s
- Cortez_-_Feel__Stripped_: 0.067 s

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
