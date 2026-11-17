# Banco · rev-rest-02 · quick · con letra

- Fecha: 2026-11-16T18:54:28+01:00
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

Mel-Band RoFormer (Kim, 8 s) + Whisper + lyrics aligner (each language's CTC model; resting between words of a line costs 0.2 per silent frame)

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt', 'segment_size': 801}
- **transcriber**: `karaoke_engine.transcribe:WhisperTranscriber` v5
- **segmenter**: `karaoke_engine.transcribe:LineSegmenter` v2
- **aligner**: `karaoke_engine.align.aligner:LyricsAligner` v14 {'rest_penalty': 0.2}

## Resumen

| Grupo | Canciones | Fallos | WER | WER tolerante | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| de | 5 | 0 | — | — | — | 0.024 | 0.035 | 99.7 % | 99.8 % | 0.056 | 0.020 | 96.8 % | — | 0 | 61 | 0.0 % | 18.0 % |
| en | 5 | 0 | — | — | — | 0.056 | 0.121 | 98.6 % | 98.7 % | 0.045 | 0.003 | 90.3 % | — | 0 | 60 | 0.0 % | 29.7 % |
| es | 5 | 0 | — | — | — | 0.024 | 0.056 | 99.4 % | 99.5 % | 0.081 | 0.022 | 97.4 % | — | 0 | 60 | 0.0 % | 24.5 % |
| fr | 5 | 0 | — | — | — | 0.029 | 0.041 | 99.8 % | 99.8 % | 0.079 | -0.016 | 92.3 % | — | 0 | 60 | 0.0 % | 24.3 % |
| total | 20 | 0 | — | — | — | 0.032 | 0.064 | 99.4 % | 99.5 % | 0.063 | 0.008 | 94.1 % | — | 0 | 60 | 0.0 % | 24.1 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 7.2 | 2867 | 2304 | 0.203 |
| aligner | 0.1 | 1559 | 3711 | 0.017 |

## Por canción

| Canción | Idioma | Duración | WER | WER tolerante | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Kinematic_-_Peyote | en | 183 | — | — | 0.052 | 99.3 % | 99.3 % | 93.9 % | manual | 0.2 % | 28.7 % | — | 41.6 |  |
| Wordsmith_-_The_Statement | en | 171 | — | — | 0.054 | 100.0 % | 100.0 % | 89.8 % | manual | 0.0 % | 30.8 % | — | 37.7 |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | — | — | 0.052 | 98.9 % | 100.0 % | 93.6 % | manual | 0.0 % | 46.1 % | — | 50.5 |  |
| Ridgway_-_Fire_Inside | en | 284 | — | — | 0.049 | 92.7 % | 92.7 % | 77.0 % | manual | 0.0 % | 30.9 % | — | 61.9 |  |
| Cortez_-_Feel__Stripped_ | en | 241 | — | — | 0.068 | 100.0 % | 100.0 % | 98.9 % | manual | 0.0 % | 12.1 % | — | 53.3 |  |
| 10._Disparan_-_criatura | es | 160 | — | — | 0.024 | 100.0 % | 100.0 % | 100.0 % | manual | 0.0 % | 22.2 % | — | 36.3 |  |
| Baila_-_Alfonso_Lugo | es | 210 | — | — | 0.019 | 100.0 % | 100.0 % | 98.2 % | manual | 0.0 % | 29.8 % | — | 46.1 |  |
| Esencia_-_NandoMalo_ | es | 262 | — | — | 0.023 | 100.0 % | 100.0 % | 98.2 % | manual | 0.0 % | 19.5 % | — | 57.8 |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | — | — | 0.029 | 98.2 % | 98.4 % | 94.8 % | manual | 0.0 % | 16.3 % | — | 43.2 |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | — | — | 0.027 | 100.0 % | 100.0 % | 99.1 % | manual | 0.0 % | 34.9 % | — | 46.5 |  |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | — | — | 0.044 | 100.0 % | 100.0 % | 97.8 % | manual | 0.0 % | 32.5 % | — | 48.7 |  |
| Der_Musiker_-_d-music | de | 271 | — | — | 0.021 | 99.4 % | 99.7 % | 98.0 % | manual | 0.0 % | 13.8 % | — | 59.9 |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | — | — | 0.046 | 97.7 % | 98.9 % | 94.6 % | manual | 0.0 % | 20.4 % | — | 53.6 |  |
| Keine_Lust_-_Jonny_M | de | 229 | — | — | 0.016 | 99.8 % | 99.8 % | 95.8 % | manual | 0.0 % | 8.2 % | — | 51.3 |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | — | — | 0.031 | 100.0 % | 100.0 % | 96.0 % | manual | 0.0 % | 15.2 % | — | 51.4 |  |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | — | — | 0.025 | 100.0 % | 100.0 % | 97.6 % | manual | 0.0 % | 7.7 % | — | 42.5 |  |
| Confession_-_Quesabe | fr | 148 | — | — | 0.029 | 99.3 % | 99.3 % | 87.2 % | manual | 0.0 % | 43.1 % | — | 32.3 |  |
| Mère_nature_-_Law' | fr | 225 | — | — | 0.037 | 100.0 % | 100.0 % | 96.5 % | manual | 0.0 % | 18.3 % | — | 49.9 |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | — | — | 0.036 | 100.0 % | 100.0 % | 88.1 % | manual | 0.0 % | 38.1 % | — | 44.5 |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | — | — | 0.022 | 100.0 % | 100.0 % | 94.1 % | manual | 0.0 % | 14.3 % | — | 40.8 |  |

## Peores casos

Mayor mediana de error de inicio:
- Cortez_-_Feel__Stripped_: 0.068 s
- Wordsmith_-_The_Statement: 0.054 s
- Kinematic_-_Peyote: 0.052 s
- The_Rinn_-_Voices__2017_Version_: 0.052 s
- Ridgway_-_Fire_Inside: 0.049 s

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
