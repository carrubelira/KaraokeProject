# Banco · rev-asr-voice12 · quick · sin letra

- Fecha: 2026-11-17T01:21:54+01:00
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

Mel-Band RoFormer (Kim, 8 s) + Whisper (each language's default) reading stretches of singing of at most 12 s + line segmenter + lyrics aligner

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt', 'segment_size': 801}
- **transcriber**: `karaoke_engine.transcribe:WhisperTranscriber` v5 {'by_voice': True, 'stretch_seconds': 12.0}
- **segmenter**: `karaoke_engine.transcribe:LineSegmenter` v2
- **aligner**: `karaoke_engine.align.aligner:LyricsAligner` v14 {'second': '', 'rest_penalty': 0.0}

## Resumen

| Grupo | Canciones | Fallos | WER | WER tolerante | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| de | 5 | 0 | 15.7 % | — | 9.0 % | 0.024 | 0.040 | 98.4 % | 99.2 % | 0.056 | 0.025 | 86.9 % | — | 0 | 73 | 0.0 % | 19.3 % |
| en | 5 | 0 | 27.7 % | — | 19.4 % | 0.057 | 0.196 | 97.2 % | 97.6 % | 0.050 | 0.036 | 73.5 % | — | 0 | 73 | 0.1 % | 30.2 % |
| es | 5 | 0 | 13.9 % | — | 9.4 % | 0.024 | 0.067 | 98.6 % | 98.9 % | 0.082 | 0.031 | 90.5 % | — | 0 | 73 | 0.0 % | 25.7 % |
| fr | 5 | 0 | 16.1 % | — | 8.5 % | 0.029 | 0.041 | 99.6 % | 99.7 % | 0.079 | -0.016 | 86.9 % | — | 0 | 72 | 0.0 % | 23.6 % |
| total | 20 | 0 | 18.6 % | — | 11.6 % | 0.031 | 0.084 | 98.4 % | 98.9 % | 0.065 | 0.019 | 84.1 % | — | 0 | 73 | 0.0 % | 24.7 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 7.2 | 2867 | 2304 | 0.203 |
| transcriber | 0.1 | 1335 | 2117 | 0.053 |
| segmenter | — | 0 | 80 | 0.000 |
| aligner | 0.1 | 1559 | 3763 | 0.017 |

## Por canción

| Canción | Idioma | Duración | WER | WER tolerante | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Kinematic_-_Peyote | en | 183 | 27.7 % | — | 0.053 | 96.7 % | 97.5 % | 83.0 % | manual | 0.5 % | 28.9 % | en | 53.8 |  |
| Wordsmith_-_The_Statement | en | 171 | 35.4 % | — | 0.054 | 95.4 % | 95.9 % | 63.7 % | manual | 0.0 % | 26.3 % | en | 47.1 |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | 47.0 % | — | 0.058 | 97.9 % | 99.3 % | 70.4 % | manual | 0.0 % | 53.1 % | en | 66.5 |  |
| Ridgway_-_Fire_Inside | en | 284 | 16.2 % | — | 0.047 | 95.8 % | 95.8 % | 70.7 % | manual | 0.0 % | 30.6 % | en | 77.1 |  |
| Cortez_-_Feel__Stripped_ | en | 241 | 13.8 % | — | 0.069 | 100.0 % | 100.0 % | 89.6 % | manual | 0.0 % | 12.1 % | en | 64.8 |  |
| 10._Disparan_-_criatura | es | 160 | 10.8 % | — | 0.023 | 100.0 % | 100.0 % | 91.2 % | manual | 0.0 % | 25.4 % | es | 43.4 |  |
| Baila_-_Alfonso_Lugo | es | 210 | 21.1 % | — | 0.019 | 99.6 % | 99.6 % | 83.3 % | manual | 0.0 % | 33.1 % | es | 57.6 |  |
| Esencia_-_NandoMalo_ | es | 262 | 16.5 % | — | 0.024 | 98.1 % | 98.1 % | 93.7 % | manual | 0.0 % | 17.1 % | es | 74.1 |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | 9.5 % | — | 0.029 | 97.6 % | 98.3 % | 92.4 % | manual | 0.0 % | 16.5 % | es | 53.6 |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | 12.3 % | — | 0.027 | 100.0 % | 100.0 % | 89.6 % | manual | 0.0 % | 36.4 % | es | 53.5 |  |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | 11.2 % | — | 0.046 | 99.4 % | 100.0 % | 89.1 % | manual | 0.0 % | 33.4 % | de | 60.7 |  |
| Der_Musiker_-_d-music | de | 271 | 21.0 % | — | 0.020 | 100.0 % | 100.0 % | 83.6 % | manual | 0.0 % | 13.0 % | de | 80.3 |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | 40.9 % | — | 0.049 | 97.2 % | 98.6 % | 77.2 % | manual | 0.1 % | 26.2 % | de | 66.1 |  |
| Keine_Lust_-_Jonny_M | de | 229 | 10.5 % | — | 0.016 | 96.4 % | 97.9 % | 88.8 % | manual | 0.0 % | 8.9 % | de | 68.3 |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | 15.9 % | — | 0.031 | 100.0 % | 100.0 % | 88.7 % | manual | 0.1 % | 15.0 % | de | 58.7 |  |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | 7.3 % | — | 0.025 | 100.0 % | 100.0 % | 93.1 % | manual | 0.0 % | 6.6 % | fr | 50.5 |  |
| Confession_-_Quesabe | fr | 148 | 29.9 % | — | 0.027 | 98.8 % | 99.6 % | 72.6 % | manual | 0.0 % | 38.4 % | fr | 45.2 |  |
| Mère_nature_-_Law' | fr | 225 | 13.0 % | — | 0.036 | 100.0 % | 100.0 % | 89.4 % | manual | 0.0 % | 19.0 % | fr | 61.2 |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | 19.3 % | — | 0.038 | 99.2 % | 99.2 % | 89.9 % | manual | 0.0 % | 38.7 % | fr | 54.3 |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | 5.6 % | — | 0.022 | 100.0 % | 100.0 % | 94.1 % | manual | 0.0 % | 15.6 % | fr | 48.5 |  |

## Peores casos

Mayor mediana de error de inicio:
- Cortez_-_Feel__Stripped_: 0.069 s
- The_Rinn_-_Voices__2017_Version_: 0.058 s
- Wordsmith_-_The_Statement: 0.054 s
- Kinematic_-_Peyote: 0.053 s
- Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique: 0.049 s

Mayor WER:
- The_Rinn_-_Voices__2017_Version_: 47.0 %
- Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique: 40.9 %
- Wordsmith_-_The_Statement: 35.4 %
- Confession_-_Quesabe: 29.9 %
- Kinematic_-_Peyote: 27.7 %

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
