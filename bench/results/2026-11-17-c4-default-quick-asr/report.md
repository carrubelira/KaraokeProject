# Banco · c4-default · quick · sin letra

- Fecha: 2026-11-17T15:49:23+01:00
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
| de | 5 | 0 | 15.7 % | — | 9.0 % | 0.024 | 0.038 | 98.8 % | 99.4 % | 0.058 | 0.020 | 86.9 % | — | 0 | 83 | 0.0 % | 13.4 % |
| en | 5 | 0 | 27.7 % | — | 19.4 % | 0.056 | 0.193 | 97.3 % | 97.7 % | 0.057 | 0.038 | 74.7 % | — | 0 | 83 | 0.1 % | 33.0 % |
| es | 5 | 0 | 13.9 % | — | 9.4 % | 0.025 | 0.049 | 98.8 % | 99.0 % | 0.087 | 0.011 | 91.4 % | — | 0 | 83 | 0.0 % | 22.2 % |
| fr | 5 | 0 | 16.1 % | — | 8.5 % | 0.029 | 0.042 | 99.4 % | 99.4 % | 0.084 | -0.015 | 86.9 % | — | 0 | 82 | 0.0 % | 16.5 % |
| total | 20 | 0 | 18.6 % | — | 11.6 % | 0.031 | 0.079 | 98.6 % | 98.9 % | 0.071 | 0.014 | 84.6 % | — | 0 | 83 | 0.0 % | 21.3 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 7.2 | 2867 | 2304 | 0.203 |
| transcriber | 0.1 | 1335 | 2121 | 0.054 |
| segmenter | — | 0 | 80 | 0.000 |
| aligner | 0.1 | 2133 | 3957 | 0.058 |

## Por canción

| Canción | Idioma | Duración | WER | WER tolerante | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Kinematic_-_Peyote | en | 183 | 27.7 % | — | 0.052 | 100.0 % | 100.0 % | 83.0 % | manual | 0.4 % | 31.5 % | en | 59.6 |  |
| Wordsmith_-_The_Statement | en | 171 | 35.4 % | — | 0.053 | 96.5 % | 96.5 % | 64.0 % | manual | 0.0 % | 27.3 % | en | 55.3 |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | 47.0 % | — | 0.060 | 96.5 % | 99.3 % | 70.4 % | manual | 0.0 % | 54.1 % | en | 75.9 |  |
| Ridgway_-_Fire_Inside | en | 284 | 16.2 % | — | 0.051 | 95.3 % | 95.7 % | 76.3 % | manual | 0.0 % | 40.2 % | en | 88.3 |  |
| Cortez_-_Feel__Stripped_ | en | 241 | 13.8 % | — | 0.068 | 99.1 % | 99.1 % | 89.6 % | manual | 0.0 % | 12.1 % | en | 74.2 |  |
| 10._Disparan_-_criatura | es | 160 | 10.8 % | — | 0.023 | 100.0 % | 100.0 % | 91.2 % | manual | 0.0 % | 23.7 % | es | 49.3 |  |
| Baila_-_Alfonso_Lugo | es | 210 | 21.1 % | — | 0.019 | 99.1 % | 99.1 % | 83.3 % | manual | 0.0 % | 27.5 % | es | 66.4 |  |
| Esencia_-_NandoMalo_ | es | 262 | 16.5 % | — | 0.024 | 98.1 % | 98.4 % | 93.7 % | manual | 0.0 % | 16.5 % | es | 85.5 |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | 9.5 % | — | 0.029 | 98.4 % | 98.6 % | 95.2 % | manual | 0.0 % | 15.0 % | es | 62.3 |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | 12.3 % | — | 0.036 | 100.0 % | 100.0 % | 89.6 % | manual | 0.0 % | 28.0 % | es | 61.9 |  |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | 11.2 % | — | 0.045 | 99.4 % | 99.4 % | 89.1 % | manual | 0.0 % | 21.7 % | de | 67.1 |  |
| Der_Musiker_-_d-music | de | 271 | 21.0 % | — | 0.020 | 100.0 % | 100.0 % | 83.6 % | manual | 0.0 % | 10.7 % | de | 92.6 |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | 40.9 % | — | 0.054 | 98.6 % | 100.0 % | 77.2 % | manual | 0.0 % | 15.2 % | de | 75.6 |  |
| Keine_Lust_-_Jonny_M | de | 229 | 10.5 % | — | 0.016 | 97.2 % | 98.7 % | 88.8 % | manual | 0.0 % | 5.2 % | de | 78.4 |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | 15.9 % | — | 0.029 | 100.0 % | 100.0 % | 88.7 % | manual | 0.1 % | 14.4 % | de | 67.6 |  |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | 7.3 % | — | 0.023 | 100.0 % | 100.0 % | 93.1 % | manual | 0.0 % | 6.6 % | fr | 57.7 |  |
| Confession_-_Quesabe | fr | 148 | 29.9 % | — | 0.027 | 98.4 % | 98.4 % | 72.6 % | manual | 0.0 % | 22.6 % | fr | 53.8 |  |
| Mère_nature_-_Law' | fr | 225 | 13.0 % | — | 0.036 | 100.0 % | 100.0 % | 89.4 % | manual | 0.0 % | 10.9 % | fr | 70.2 |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | 19.3 % | — | 0.036 | 98.8 % | 98.8 % | 89.9 % | manual | 0.0 % | 32.0 % | fr | 63.0 |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | 5.6 % | — | 0.022 | 100.0 % | 100.0 % | 94.1 % | manual | 0.0 % | 10.5 % | fr | 56.4 |  |

## Peores casos

Mayor mediana de error de inicio:
- Cortez_-_Feel__Stripped_: 0.068 s
- The_Rinn_-_Voices__2017_Version_: 0.060 s
- Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique: 0.054 s
- Wordsmith_-_The_Statement: 0.053 s
- Kinematic_-_Peyote: 0.052 s

Mayor WER:
- The_Rinn_-_Voices__2017_Version_: 47.0 %
- Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique: 40.9 %
- Wordsmith_-_The_Statement: 35.4 %
- Confession_-_Quesabe: 29.9 %
- Kinematic_-_Peyote: 27.7 %

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
