# Banco · c4-default · quick · con letra

- Fecha: 2026-11-17T11:21:55+01:00
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
| de | 5 | 0 | — | — | — | 0.024 | 0.034 | 99.9 % | 100.0 % | 0.058 | 0.019 | 96.6 % | — | 0 | 71 | 0.0 % | 13.3 % |
| en | 5 | 0 | — | — | — | 0.054 | 0.116 | 98.7 % | 99.0 % | 0.051 | 0.003 | 90.4 % | — | 0 | 72 | 0.0 % | 31.7 % |
| es | 5 | 0 | — | — | — | 0.024 | 0.034 | 99.9 % | 99.9 % | 0.087 | 0.000 | 98.5 % | — | 0 | 75 | 0.0 % | 21.8 % |
| fr | 5 | 0 | — | — | — | 0.029 | 0.038 | 99.8 % | 99.8 % | 0.084 | -0.015 | 92.3 % | — | 0 | 76 | 0.0 % | 18.8 % |
| total | 20 | 0 | — | — | — | 0.031 | 0.056 | 99.6 % | 99.7 % | 0.069 | 0.002 | 94.3 % | — | 0 | 75 | 0.0 % | 21.4 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 7.2 | 2867 | 2304 | 0.203 |
| aligner | 0.1 | 3314 | 3749 | 0.078 |

## Por canción

| Canción | Idioma | Duración | WER | WER tolerante | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Kinematic_-_Peyote | en | 183 | — | — | 0.050 | 100.0 % | 100.0 % | 93.9 % | manual | 0.2 % | 30.8 % | — | 49.4 |  |
| Wordsmith_-_The_Statement | en | 171 | — | — | 0.051 | 100.0 % | 100.0 % | 90.2 % | manual | 0.0 % | 34.3 % | — | 45.9 |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | — | — | 0.057 | 98.9 % | 100.0 % | 93.6 % | manual | 0.0 % | 45.6 % | — | 59.5 |  |
| Ridgway_-_Fire_Inside | en | 284 | — | — | 0.047 | 93.2 % | 93.6 % | 77.0 % | manual | 0.0 % | 35.3 % | — | 73.7 |  |
| Cortez_-_Feel__Stripped_ | en | 241 | — | — | 0.067 | 100.0 % | 100.0 % | 98.9 % | manual | 0.0 % | 12.4 % | — | 69.6 |  |
| 10._Disparan_-_criatura | es | 160 | — | — | 0.024 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 22.7 % | — | 47.3 |  |
| Baila_-_Alfonso_Lugo | es | 210 | — | — | 0.019 | 100.0 % | 100.0 % | 98.2 % | manual | 0.0 % | 24.6 % | — | 57.5 |  |
| Esencia_-_NandoMalo_ | es | 262 | — | — | 0.023 | 100.0 % | 100.0 % | 98.2 % | manual | 0.0 % | 18.0 % | — | 73.9 |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | — | — | 0.029 | 99.6 % | 99.8 % | 98.3 % | manual | 0.0 % | 16.2 % | — | 56.3 |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | — | — | 0.030 | 100.0 % | 100.0 % | 99.1 % | manual | 0.0 % | 27.4 % | — | 60.0 |  |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | — | — | 0.044 | 100.0 % | 100.0 % | 97.8 % | manual | 0.0 % | 21.0 % | — | 61.0 |  |
| Der_Musiker_-_d-music | de | 271 | — | — | 0.021 | 99.7 % | 100.0 % | 97.2 % | manual | 0.0 % | 11.1 % | — | 71.4 |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | — | — | 0.054 | 98.9 % | 100.0 % | 94.6 % | manual | 0.0 % | 14.0 % | — | 62.8 |  |
| Keine_Lust_-_Jonny_M | de | 229 | — | — | 0.016 | 100.0 % | 100.0 % | 95.8 % | manual | 0.0 % | 4.4 % | — | 61.8 |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | — | — | 0.030 | 100.0 % | 100.0 % | 96.0 % | manual | 0.0 % | 15.9 % | — | 60.9 |  |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | — | — | 0.024 | 100.0 % | 100.0 % | 97.6 % | manual | 0.0 % | 7.7 % | — | 54.8 |  |
| Confession_-_Quesabe | fr | 148 | — | — | 0.029 | 99.3 % | 99.3 % | 87.2 % | manual | 0.2 % | 28.5 % | — | 43.0 |  |
| Mère_nature_-_Law' | fr | 225 | — | — | 0.037 | 100.0 % | 100.0 % | 96.5 % | manual | 0.0 % | 13.9 % | — | 64.1 |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | — | — | 0.034 | 100.0 % | 100.0 % | 88.1 % | manual | 0.0 % | 34.6 % | — | 57.6 |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | — | — | 0.022 | 100.0 % | 100.0 % | 94.1 % | manual | 0.0 % | 9.1 % | — | 52.9 |  |

## Peores casos

Mayor mediana de error de inicio:
- Cortez_-_Feel__Stripped_: 0.067 s
- The_Rinn_-_Voices__2017_Version_: 0.057 s
- Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique: 0.054 s
- Wordsmith_-_The_Statement: 0.051 s
- Kinematic_-_Peyote: 0.050 s

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
