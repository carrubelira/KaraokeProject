# Banco · rev-asr-voice · quick · sin letra

- Fecha: 2026-11-17T00:06:23+01:00
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

Mel-Band RoFormer (Kim, 8 s) + Whisper (each language's default) reading each stretch of singing on its own + line segmenter + lyrics aligner

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt', 'segment_size': 801}
- **transcriber**: `karaoke_engine.transcribe:WhisperTranscriber` v5 {'by_voice': True}
- **segmenter**: `karaoke_engine.transcribe:LineSegmenter` v2
- **aligner**: `karaoke_engine.align.aligner:LyricsAligner` v14 {'second': '', 'rest_penalty': 0.0}

## Resumen

| Grupo | Canciones | Fallos | WER | WER tolerante | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| de | 5 | 0 | 16.5 % | — | 10.0 % | 0.024 | 0.038 | 98.9 % | 99.3 % | 0.055 | 0.022 | 87.7 % | — | 0 | 68 | 0.0 % | 17.1 % |
| en | 5 | 0 | 33.5 % | — | 22.8 % | 0.058 | 0.786 | 95.1 % | 95.3 % | 0.053 | 0.593 | 69.1 % | — | 0 | 70 | 0.2 % | 30.1 % |
| es | 5 | 0 | 9.5 % | — | 4.6 % | 0.024 | 0.058 | 99.2 % | 99.3 % | 0.080 | 0.023 | 94.0 % | — | 0 | 69 | 0.0 % | 23.3 % |
| fr | 5 | 0 | 22.2 % | — | 15.1 % | 0.029 | 0.048 | 99.6 % | 99.7 % | 0.082 | -0.023 | 82.0 % | — | 0 | 66 | 0.0 % | 23.5 % |
| total | 20 | 0 | 20.8 % | — | 13.3 % | 0.031 | 0.216 | 98.3 % | 98.5 % | 0.066 | 0.142 | 82.7 % | — | 0 | 68 | 0.1 % | 23.5 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 7.2 | 2867 | 2304 | 0.203 |
| transcriber | 0.1 | 1335 | 2120 | 0.034 |
| segmenter | — | 0 | 81 | 0.000 |
| aligner | 0.1 | 1559 | 3722 | 0.017 |

## Por canción

| Canción | Idioma | Duración | WER | WER tolerante | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Kinematic_-_Peyote | en | 183 | 18.9 % | — | 0.054 | 96.7 % | 97.5 % | 81.6 % | manual | 0.9 % | 30.4 % | en | 49.8 |  |
| Wordsmith_-_The_Statement | en | 171 | 44.0 % | — | 0.057 | 90.8 % | 90.8 % | 54.0 % | manual | 0.0 % | 30.0 % | en | 59.0 |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | 37.1 % | — | 0.053 | 98.0 % | 98.6 % | 72.4 % | manual | 0.0 % | 51.6 % | en | 57.8 |  |
| Ridgway_-_Fire_Inside | en | 284 | 44.9 % | — | 0.053 | 92.0 % | 92.0 % | 61.5 % | manual | 0.0 % | 27.8 % | en | 72.4 |  |
| Cortez_-_Feel__Stripped_ | en | 241 | 11.2 % | — | 0.068 | 99.1 % | 99.1 % | 93.0 % | manual | 0.0 % | 10.8 % | en | 63.1 |  |
| 10._Disparan_-_criatura | es | 160 | 7.7 % | — | 0.024 | 100.0 % | 100.0 % | 93.8 % | manual | 0.0 % | 24.2 % | es | 39.9 |  |
| Baila_-_Alfonso_Lugo | es | 210 | 13.4 % | — | 0.019 | 100.0 % | 100.0 % | 92.9 % | manual | 0.0 % | 26.9 % | es | 53.5 |  |
| Esencia_-_NandoMalo_ | es | 262 | 10.5 % | — | 0.023 | 99.4 % | 99.4 % | 95.2 % | manual | 0.0 % | 16.0 % | es | 70.1 |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | 7.9 % | — | 0.028 | 98.1 % | 98.4 % | 93.7 % | manual | 0.0 % | 16.1 % | es | 50.3 |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | 6.6 % | — | 0.027 | 100.0 % | 100.0 % | 94.3 % | manual | 0.0 % | 33.3 % | es | 50.4 |  |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | 8.5 % | — | 0.045 | 100.0 % | 100.0 % | 91.3 % | manual | 0.0 % | 31.6 % | de | 58.5 |  |
| Der_Musiker_-_d-music | de | 271 | 20.2 % | — | 0.020 | 100.0 % | 100.0 % | 83.9 % | manual | 0.0 % | 10.7 % | de | 75.0 |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | 29.0 % | — | 0.046 | 98.7 % | 98.7 % | 81.5 % | manual | 0.1 % | 23.5 % | de | 58.9 |  |
| Keine_Lust_-_Jonny_M | de | 229 | 16.8 % | — | 0.016 | 97.3 % | 98.3 % | 89.6 % | manual | 0.0 % | 8.4 % | de | 68.6 |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | 17.9 % | — | 0.031 | 100.0 % | 100.0 % | 84.8 % | manual | 0.1 % | 11.3 % | de | 55.4 |  |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | 6.1 % | — | 0.025 | 100.0 % | 100.0 % | 94.3 % | manual | 0.0 % | 6.1 % | fr | 47.1 |  |
| Confession_-_Quesabe | fr | 148 | 54.9 % | — | 0.026 | 97.6 % | 98.2 % | 50.6 % | manual | 0.0 % | 37.2 % | fr | 41.4 |  |
| Mère_nature_-_Law' | fr | 225 | 14.6 % | — | 0.036 | 100.0 % | 100.0 % | 89.4 % | manual | 0.0 % | 19.2 % | fr | 55.9 |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | 19.3 % | — | 0.037 | 100.0 % | 100.0 % | 91.0 % | manual | 0.0 % | 38.7 % | fr | 49.8 |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | 5.6 % | — | 0.022 | 100.0 % | 100.0 % | 94.5 % | manual | 0.0 % | 16.3 % | fr | 45.5 |  |

## Peores casos

Mayor mediana de error de inicio:
- Cortez_-_Feel__Stripped_: 0.068 s
- Wordsmith_-_The_Statement: 0.057 s
- Kinematic_-_Peyote: 0.054 s
- The_Rinn_-_Voices__2017_Version_: 0.053 s
- Ridgway_-_Fire_Inside: 0.053 s

Mayor WER:
- Confession_-_Quesabe: 54.9 %
- Ridgway_-_Fire_Inside: 44.9 %
- Wordsmith_-_The_Statement: 44.0 %
- The_Rinn_-_Voices__2017_Version_: 37.1 %
- Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique: 29.0 %

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
