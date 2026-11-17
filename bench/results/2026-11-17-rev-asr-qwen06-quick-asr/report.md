# Banco · rev-asr-qwen06 · quick · sin letra

- Fecha: 2026-11-17T00:14:31+01:00
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

Mel-Band RoFormer (Kim, 8 s) + Qwen3-ASR 0.6B reading each stretch of singing on its own, language given + line segmenter + lyrics aligner

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt', 'segment_size': 801}
- **transcriber**: `karaoke_bench.baseline.qwen:QwenTranscriber` v1 {'model': '0.6b'}
- **segmenter**: `karaoke_engine.transcribe:LineSegmenter` v2
- **aligner**: `karaoke_engine.align.aligner:LyricsAligner` v14 {'second': '', 'rest_penalty': 0.0}

## Resumen

| Grupo | Canciones | Fallos | WER | WER tolerante | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| de | 5 | 0 | 21.7 % | — | 9.8 % | 0.024 | 0.045 | 99.6 % | 99.6 % | 0.056 | 0.006 | 81.4 % | — | 0 | 93 | 0.0 % | 18.1 % |
| en | 5 | 0 | 19.2 % | — | 12.0 % | 0.056 | 0.088 | 98.7 % | 98.8 % | 0.046 | 0.036 | 81.6 % | — | 0 | 87 | 0.1 % | 29.9 % |
| es | 5 | 0 | 21.0 % | — | 9.4 % | 0.024 | 0.063 | 99.1 % | 99.2 % | 0.081 | 0.023 | 83.2 % | — | 0 | 93 | 0.0 % | 23.8 % |
| fr | 5 | 0 | 21.1 % | — | 10.9 % | 0.029 | 0.049 | 99.4 % | 99.4 % | 0.079 | -0.019 | 83.4 % | — | 0 | 94 | 0.0 % | 23.7 % |
| total | 20 | 0 | 20.7 % | — | 10.5 % | 0.032 | 0.062 | 99.2 % | 99.2 % | 0.063 | 0.013 | 82.3 % | — | 0 | 93 | 0.0 % | 23.8 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 7.2 | 2867 | 2304 | 0.203 |
| transcriber | 11.2 | 2231 | 2636 | 0.089 |
| segmenter | — | 0 | 81 | 0.000 |
| aligner | 0.1 | 1559 | 3778 | 0.017 |

## Por canción

| Canción | Idioma | Duración | WER | WER tolerante | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Kinematic_-_Peyote | en | 183 | 25.8 % | — | 0.053 | 96.8 % | 97.6 % | 84.4 % | manual | 0.5 % | 29.1 % | en | 51.2 |  |
| Wordsmith_-_The_Statement | en | 171 | 14.1 % | — | 0.055 | 100.0 % | 100.0 % | 83.6 % | manual | 0.0 % | 27.7 % | en | 71.8 |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | 36.1 % | — | 0.066 | 95.1 % | 95.8 % | 70.4 % | manual | 0.0 % | 50.2 % | en | 65.8 |  |
| Ridgway_-_Fire_Inside | en | 284 | 27.7 % | — | 0.046 | 97.2 % | 97.2 % | 71.1 % | manual | 0.0 % | 32.4 % | en | 77.0 |  |
| Cortez_-_Feel__Stripped_ | en | 241 | 7.6 % | — | 0.068 | 100.0 % | 100.0 % | 92.4 % | manual | 0.0 % | 10.1 % | en | 72.6 |  |
| 10._Disparan_-_criatura | es | 160 | 21.6 % | — | 0.023 | 100.0 % | 100.0 % | 83.0 % | manual | 0.0 % | 27.1 % | es | 48.7 |  |
| Baila_-_Alfonso_Lugo | es | 210 | 28.2 % | — | 0.019 | 100.0 % | 100.0 % | 75.2 % | manual | 0.0 % | 30.7 % | es | 65.6 |  |
| Esencia_-_NandoMalo_ | es | 262 | 17.1 % | — | 0.023 | 99.7 % | 99.7 % | 88.6 % | manual | 0.0 % | 13.5 % | es | 81.3 |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | 16.7 % | — | 0.029 | 97.7 % | 98.0 % | 85.6 % | manual | 0.0 % | 17.2 % | es | 69.1 |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | 33.0 % | — | 0.026 | 100.0 % | 100.0 % | 77.4 % | manual | 0.0 % | 30.3 % | es | 54.5 |  |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | 25.4 % | — | 0.046 | 100.0 % | 100.0 % | 80.1 % | manual | 0.0 % | 33.0 % | de | 71.7 |  |
| Der_Musiker_-_d-music | de | 271 | 23.5 % | — | 0.020 | 100.0 % | 100.0 % | 80.2 % | manual | 0.0 % | 12.2 % | de | 84.0 |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | 31.2 % | — | 0.054 | 98.5 % | 98.5 % | 70.7 % | manual | 0.0 % | 19.8 % | de | 62.4 |  |
| Keine_Lust_-_Jonny_M | de | 229 | 17.5 % | — | 0.016 | 99.1 % | 99.1 % | 84.3 % | manual | 0.0 % | 10.3 % | de | 86.8 |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | 17.2 % | — | 0.032 | 100.0 % | 100.0 % | 83.4 % | manual | 0.0 % | 14.9 % | de | 62.5 |  |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | 13.1 % | — | 0.025 | 100.0 % | 100.0 % | 89.8 % | manual | 0.0 % | 7.6 % | fr | 60.6 |  |
| Confession_-_Quesabe | fr | 148 | 37.9 % | — | 0.028 | 98.3 % | 98.3 % | 71.4 % | manual | 0.1 % | 40.3 % | fr | 54.5 |  |
| Mère_nature_-_Law' | fr | 225 | 17.8 % | — | 0.036 | 100.0 % | 100.0 % | 86.6 % | manual | 0.0 % | 20.5 % | fr | 67.4 |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | 20.7 % | — | 0.036 | 98.7 % | 98.7 % | 83.2 % | manual | 0.0 % | 35.3 % | fr | 64.1 |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | 10.3 % | — | 0.022 | 100.0 % | 100.0 % | 89.8 % | manual | 0.0 % | 14.8 % | fr | 60.4 |  |

## Peores casos

Mayor mediana de error de inicio:
- Cortez_-_Feel__Stripped_: 0.068 s
- The_Rinn_-_Voices__2017_Version_: 0.066 s
- Wordsmith_-_The_Statement: 0.055 s
- Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique: 0.054 s
- Kinematic_-_Peyote: 0.053 s

Mayor WER:
- Confession_-_Quesabe: 37.9 %
- The_Rinn_-_Voices__2017_Version_: 36.1 %
- Háblame_-_(Talk_to_me)_-_Brunela_Crochenci: 33.0 %
- Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique: 31.2 %
- Baila_-_Alfonso_Lugo: 28.2 %

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
