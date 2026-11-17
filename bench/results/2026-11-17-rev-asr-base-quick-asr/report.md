# Banco · rev-asr-base · quick · sin letra

- Fecha: 2026-11-17T00:01:57+01:00
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

Mel-Band RoFormer (Kim, 8 s) + Whisper (each language's default) reading the whole song with Silero VAD, as before + line segmenter + lyrics aligner

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt', 'segment_size': 801}
- **transcriber**: `karaoke_engine.transcribe:WhisperTranscriber` v5
- **segmenter**: `karaoke_engine.transcribe:LineSegmenter` v2
- **aligner**: `karaoke_engine.align.aligner:LyricsAligner` v14 {'second': '', 'rest_penalty': 0.0}

## Resumen

| Grupo | Canciones | Fallos | WER | WER tolerante | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| de | 5 | 0 | 21.3 % | — | 15.7 % | 0.027 | 0.074 | 96.8 % | 97.8 % | 0.056 | 0.059 | 82.4 % | — | 0 | 65 | 0.0 % | 14.4 % |
| en | 5 | 0 | 29.5 % | — | 24.7 % | 0.059 | 1.690 | 95.2 % | 95.4 % | 0.048 | 1.682 | 68.5 % | — | 0 | 63 | 0.0 % | 25.3 % |
| es | 5 | 0 | 15.2 % | — | 10.9 % | 0.024 | 0.068 | 98.9 % | 99.0 % | 0.080 | 0.020 | 88.1 % | — | 0 | 65 | 0.0 % | 24.4 % |
| fr | 5 | 0 | 19.6 % | — | 13.0 % | 0.030 | 0.041 | 99.8 % | 99.8 % | 0.081 | -0.008 | 81.9 % | — | 0 | 66 | 0.0 % | 23.4 % |
| total | 20 | 0 | 21.7 % | — | 16.2 % | 0.032 | 0.444 | 97.7 % | 98.0 % | 0.066 | 0.414 | 79.8 % | — | 0 | 65 | 0.0 % | 21.9 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 7.2 | 2867 | 2304 | 0.203 |
| transcriber | 0.1 | 1335 | 2117 | 0.022 |
| segmenter | — | 0 | 94 | 0.000 |
| aligner | 0.1 | 1559 | 3724 | 0.016 |

## Por canción

| Canción | Idioma | Duración | WER | WER tolerante | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Kinematic_-_Peyote | en | 183 | 26.4 % | — | 0.056 | 96.6 % | 97.5 % | 80.3 % | manual | 0.0 % | 30.7 % | en | 44.3 |  |
| Wordsmith_-_The_Statement | en | 171 | 29.5 % | — | 0.056 | 94.5 % | 94.5 % | 68.3 % | manual | 0.0 % | 28.5 % | en | 62.0 |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | 61.4 % | — | 0.071 | 80.0 % | 81.2 % | 39.4 % | manual | 0.0 % | 27.0 % | en | 52.4 |  |
| Ridgway_-_Fire_Inside | en | 284 | 33.0 % | — | 0.050 | 93.8 % | 93.8 % | 53.0 % | manual | 0.1 % | 29.4 % | en | 66.0 |  |
| Cortez_-_Feel__Stripped_ | en | 241 | 9.8 % | — | 0.067 | 100.0 % | 100.0 % | 93.8 % | manual | 0.0 % | 10.8 % | en | 59.4 |  |
| 10._Disparan_-_criatura | es | 160 | 43.3 % | — | 0.024 | 97.7 % | 97.7 % | 67.5 % | manual | 0.0 % | 31.6 % | es | 43.9 |  |
| Baila_-_Alfonso_Lugo | es | 210 | 9.9 % | — | 0.019 | 100.0 % | 100.0 % | 91.1 % | manual | 0.0 % | 27.9 % | es | 50.6 |  |
| Esencia_-_NandoMalo_ | es | 262 | 12.6 % | — | 0.022 | 100.0 % | 100.0 % | 92.2 % | manual | 0.0 % | 12.4 % | es | 63.2 |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | 8.7 % | — | 0.028 | 98.1 % | 98.4 % | 92.8 % | manual | 0.0 % | 15.7 % | es | 49.2 |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | 16.0 % | — | 0.030 | 97.8 % | 97.8 % | 84.0 % | manual | 0.0 % | 34.4 % | es | 49.6 |  |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | 9.0 % | — | 0.045 | 100.0 % | 100.0 % | 92.6 % | manual | 0.0 % | 32.1 % | de | 53.8 |  |
| Der_Musiker_-_d-music | de | 271 | 18.9 % | — | 0.020 | 99.7 % | 99.7 % | 83.9 % | manual | 0.0 % | 8.6 % | de | 64.6 |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | 14.0 % | — | 0.049 | 97.4 % | 98.7 % | 83.7 % | manual | 0.0 % | 12.1 % | de | 56.2 |  |
| Keine_Lust_-_Jonny_M | de | 229 | 34.5 % | — | 0.018 | 90.7 % | 93.5 % | 73.1 % | manual | 0.0 % | 7.4 % | de | 63.6 |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | 15.2 % | — | 0.032 | 100.0 % | 100.0 % | 86.1 % | manual | 0.1 % | 11.7 % | de | 54.7 |  |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | 10.6 % | — | 0.025 | 99.5 % | 99.5 % | 89.0 % | manual | 0.0 % | 6.9 % | fr | 47.1 |  |
| Confession_-_Quesabe | fr | 148 | 40.0 % | — | 0.030 | 100.0 % | 100.0 % | 59.8 % | manual | 0.0 % | 35.7 % | fr | 35.7 |  |
| Mère_nature_-_Law' | fr | 225 | 15.4 % | — | 0.037 | 100.0 % | 100.0 % | 87.8 % | manual | 0.0 % | 19.8 % | fr | 54.8 |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | 15.7 % | — | 0.037 | 100.0 % | 100.0 % | 84.7 % | manual | 0.0 % | 41.0 % | fr | 49.6 |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | 9.9 % | — | 0.022 | 99.6 % | 99.6 % | 95.3 % | manual | 0.0 % | 13.4 % | fr | 45.5 |  |

## Peores casos

Mayor mediana de error de inicio:
- The_Rinn_-_Voices__2017_Version_: 0.071 s
- Cortez_-_Feel__Stripped_: 0.067 s
- Wordsmith_-_The_Statement: 0.056 s
- Kinematic_-_Peyote: 0.056 s
- Ridgway_-_Fire_Inside: 0.050 s

Mayor WER:
- The_Rinn_-_Voices__2017_Version_: 61.4 %
- 10._Disparan_-_criatura: 43.3 %
- Confession_-_Quesabe: 40.0 %
- Keine_Lust_-_Jonny_M: 34.5 %
- Ridgway_-_Fire_Inside: 33.0 %

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
