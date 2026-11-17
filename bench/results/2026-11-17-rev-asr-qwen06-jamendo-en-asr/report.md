# Banco · rev-asr-qwen06 · jamendo-en · sin letra

- Fecha: 2026-11-17T05:57:22+01:00
- Commit: a85e232-dirty
- Banco 3.0.0, normalización v1
- Referencias: en manual

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

Mel-Band RoFormer (Kim, 8 s) + Qwen3-ASR 0.6B reading each stretch of singing on its own, language given + line segmenter + lyrics aligner

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt', 'segment_size': 801}
- **transcriber**: `karaoke_bench.baseline.qwen:QwenTranscriber` v1 {'model': '0.6b'}
- **segmenter**: `karaoke_engine.transcribe:LineSegmenter` v2
- **aligner**: `karaoke_engine.align.aligner:LyricsAligner` v14 {'second': '', 'rest_penalty': 0.0}

## Resumen

| Grupo | Canciones | Fallos | WER | WER tolerante | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| en | 20 | 0 | 22.9 % | — | 15.6 % | 0.057 | 0.120 | 97.8 % | 98.1 % | 0.056 | 0.063 | 81.9 % | — | 0 | 89 | 0.0 % | 32.4 % |
| total | 20 | 0 | 22.9 % | — | 15.6 % | 0.057 | 0.120 | 97.8 % | 98.1 % | 0.056 | 0.063 | 81.9 % | — | 0 | 89 | 0.0 % | 32.4 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 7.2 | 2867 | 2388 | 0.205 |
| transcriber | 11.2 | 2287 | 2636 | 0.075 |
| segmenter | — | 0 | 81 | 0.000 |
| aligner | 0.1 | 1559 | 3778 | 0.016 |

## Por canción

| Canción | Idioma | Duración | WER | WER tolerante | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Avercage_-_Embers | en | 243 | 55.4 % | — | 0.139 | 88.2 % | 89.4 % | 45.0 % | manual | 0.0 % | 86.4 % | en | 75.7 |  |
| Color_Out_-_Falling_Star | en | 222 | 24.5 % | — | 0.149 | 94.8 % | 95.8 % | 85.3 % | manual | 0.0 % | 36.8 % | en | 62.3 |  |
| Cortez_-_Feel__Stripped_ | en | 241 | 7.6 % | — | 0.068 | 100.0 % | 100.0 % | 92.4 % | manual | 0.0 % | 10.1 % | en | 72.6 (caché) |  |
| Explosive_Ear_Candy_-_Like_The_Sun | en | 193 | 39.9 % | — | 0.050 | 100.0 % | 100.0 % | 96.6 % | manual | 0.0 % | 13.0 % | en | 90.8 |  |
| HILA_-_Give_Me_the_Same | en | 234 | 9.4 % | — | 0.059 | 99.0 % | 99.3 % | 89.4 % | manual | 0.0 % | 24.7 % | en | 68.8 |  |
| JASON_MILLER_-_CROWD_PLEASER | en | 193 | 16.4 % | — | 0.051 | 100.0 % | 100.0 % | 85.8 % | manual | 0.0 % | 9.4 % | en | 76.0 |  |
| Kinematic_-_Peyote | en | 183 | 25.8 % | — | 0.053 | 96.8 % | 97.6 % | 84.4 % | manual | 0.5 % | 29.1 % | en | 51.2 (caché) |  |
| LUNABLIND_-_Vision__Radio_Edit_ | en | 221 | 8.2 % | — | 0.064 | 100.0 % | 100.0 % | 92.7 % | manual | 0.0 % | 13.2 % | en | 67.8 |  |
| Lower_Loveday_-_Is_It_Right_ | en | 180 | 6.5 % | — | 0.057 | 100.0 % | 100.0 % | 92.9 % | manual | 0.0 % | 17.5 % | en | 53.1 |  |
| Moon_I_Mean_-_Wrong_Concept | en | 220 | 31.2 % | — | 0.053 | 96.2 % | 96.8 % | 68.0 % | manual | 0.0 % | 57.5 % | en | 64.6 |  |
| Pure_Mids_-_The_Leader | en | 262 | 47.0 % | — | 0.080 | 91.6 % | 91.6 % | 72.8 % | manual | 0.0 % | 72.3 % | en | 125.2 |  |
| Quentin_Hannappe_-_Keep_On | en | 190 | 17.9 % | — | 0.045 | 100.0 % | 100.0 % | 87.4 % | manual | 0.0 % | 20.1 % | en | 53.4 |  |
| Ridgway_-_Fire_Inside | en | 284 | 27.7 % | — | 0.046 | 97.2 % | 97.2 % | 71.1 % | manual | 0.0 % | 32.4 % | en | 77.0 (caché) |  |
| Rxbyn_-_Bad_Side | en | 217 | 19.7 % | — | 0.057 | 98.7 % | 98.7 % | 85.7 % | manual | 0.0 % | 24.6 % | en | 74.0 |  |
| Slingshot_Miracle_-_Whistler | en | 229 | 14.7 % | — | 0.063 | 99.3 % | 100.0 % | 88.3 % | manual | 0.0 % | 27.7 % | en | 62.2 |  |
| Songwriterz_-_Back_In_Time | en | 209 | 14.6 % | — | 0.064 | 91.2 % | 91.7 % | 76.1 % | manual | 0.0 % | 27.6 % | en | 62.7 |  |
| The.madpix.project_-_One_Way_Street | en | 171 | 28.8 % | — | 0.057 | 100.0 % | 100.0 % | 82.0 % | manual | 0.0 % | 27.4 % | en | 50.4 |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | 36.1 % | — | 0.066 | 95.1 % | 95.8 % | 70.4 % | manual | 0.0 % | 50.2 % | en | 65.8 (caché) |  |
| Tom_Orlando_-_The_One__feat._Tina_G_ | en | 240 | 33.4 % | — | 0.043 | 92.5 % | 93.9 % | 72.7 % | manual | 0.1 % | 39.4 % | en | 87.0 |  |
| Wordsmith_-_The_Statement | en | 171 | 14.1 % | — | 0.055 | 100.0 % | 100.0 % | 83.6 % | manual | 0.0 % | 27.7 % | en | 71.8 (caché) |  |

## Peores casos

Mayor mediana de error de inicio:
- Color_Out_-_Falling_Star: 0.149 s
- Avercage_-_Embers: 0.139 s
- Pure_Mids_-_The_Leader: 0.080 s
- Cortez_-_Feel__Stripped_: 0.068 s
- The_Rinn_-_Voices__2017_Version_: 0.066 s

Mayor WER:
- Avercage_-_Embers: 55.4 %
- Pure_Mids_-_The_Leader: 47.0 %
- Explosive_Ear_Candy_-_Like_The_Sun: 39.9 %
- The_Rinn_-_Voices__2017_Version_: 36.1 %
- Tom_Orlando_-_The_One__feat._Tina_G_: 33.4 %

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
