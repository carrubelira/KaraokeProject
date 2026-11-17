# Banco · rev-blend-w07 · quick · con letra

- Fecha: 2026-11-17T00:47:11+01:00
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

Mel-Band RoFormer (Kim, 8 s) + Whisper + lyrics aligner (each language's CTC model averaged with the music model, which weighs 0.7)

- **separator**: `karaoke_engine.separation:RoformerSeparator` v2 {'model': 'vocals_mel_band_roformer.ckpt', 'segment_size': 801}
- **transcriber**: `karaoke_engine.transcribe:WhisperTranscriber` v5
- **segmenter**: `karaoke_engine.transcribe:LineSegmenter` v2
- **aligner**: `karaoke_engine.align.aligner:LyricsAligner` v14 {'second': 'music-w2vbert-ctc', 'second_weight': 0.7}

## Resumen

| Grupo | Canciones | Fallos | WER | WER tolerante | CER | Inicio mediana | Inicio media | ≤ 0,3 s | ≤ 0,5 s | Fin mediana | Sesgo | Cobertura | Línea mediana | Cambios de idioma | 4 min (s) | Fuera de voz | Confianza < 0,3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| de | 5 | 0 | — | — | — | 0.028 | 0.044 | 99.7 % | 99.8 % | 0.094 | 0.025 | 96.6 % | — | 0 | 69 | 0.0 % | 16.0 % |
| en | 5 | 0 | — | — | — | 0.050 | 0.155 | 98.5 % | 98.9 % | 0.101 | 0.037 | 90.5 % | — | 0 | 69 | 0.1 % | 26.2 % |
| es | 5 | 0 | — | — | — | 0.024 | 0.032 | 99.9 % | 100.0 % | 0.125 | 0.003 | 98.5 % | — | 0 | 69 | 0.0 % | 23.0 % |
| fr | 5 | 0 | — | — | — | 0.025 | 0.033 | 99.9 % | 99.9 % | 0.111 | -0.008 | 92.3 % | — | 0 | 70 | 0.0 % | 19.4 % |
| total | 20 | 0 | — | — | — | 0.030 | 0.068 | 99.5 % | 99.6 % | 0.108 | 0.015 | 94.4 % | — | 0 | 69 | 0.0 % | 21.2 % |

## Etapas

| Paso | Carga (s) | VRAM pico (MiB) | RAM pico (MiB) | Mediana tiempo/duración |
|---|---|---|---|---|
| separator | 7.2 | 2867 | 2304 | 0.203 |
| aligner | 0.1 | 2133 | 3749 | 0.054 |

## Por canción

| Canción | Idioma | Duración | WER | WER tolerante | Inicio mediana | ≤ 0,3 s | ≤ 0,5 s | Cobertura | Referencia | Fuera de voz | Confianza < 0,3 | Idioma devuelto | Tiempo (s) | Error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Kinematic_-_Peyote | en | 183 | — | — | 0.052 | 99.3 % | 99.3 % | 93.9 % | manual | 0.4 % | 21.7 % | — | 48.1 |  |
| Wordsmith_-_The_Statement | en | 171 | — | — | 0.037 | 100.0 % | 100.0 % | 90.5 % | manual | 0.0 % | 24.5 % | — | 44.5 |  |
| The_Rinn_-_Voices__2017_Version_ | en | 231 | — | — | 0.070 | 98.9 % | 100.0 % | 93.6 % | manual | 0.0 % | 34.2 % | — | 58.7 |  |
| Ridgway_-_Fire_Inside | en | 284 | — | — | 0.046 | 93.6 % | 93.6 % | 77.0 % | manual | 0.0 % | 39.2 % | — | 71.7 |  |
| Cortez_-_Feel__Stripped_ | en | 241 | — | — | 0.075 | 99.1 % | 100.0 % | 98.9 % | manual | 0.0 % | 11.3 % | — | 62.2 |  |
| 10._Disparan_-_criatura | es | 160 | — | — | 0.025 | 99.5 % | 100.0 % | 100.0 % | manual | 0.0 % | 25.3 % | — | 42.2 |  |
| Baila_-_Alfonso_Lugo | es | 210 | — | — | 0.021 | 100.0 % | 100.0 % | 98.2 % | manual | 0.0 % | 32.7 % | — | 54.1 |  |
| Esencia_-_NandoMalo_ | es | 262 | — | — | 0.022 | 100.0 % | 100.0 % | 98.2 % | manual | 0.0 % | 16.8 % | — | 67.0 |  |
| Te_Recuerdo_-_Wilson_Way | es | 194 | — | — | 0.027 | 99.8 % | 100.0 % | 98.3 % | manual | 0.0 % | 8.3 % | — | 50.5 |  |
| Háblame_-_(Talk_to_me)_-_Brunela_Crochenci | es | 214 | — | — | 0.033 | 100.0 % | 100.0 % | 99.1 % | manual | 0.0 % | 32.1 % | — | 54.5 |  |
| 1_Freak_-_Automatisch_Gekommen | de | 188 | — | — | 0.057 | 100.0 % | 100.0 % | 97.8 % | manual | 0.0 % | 15.8 % | — | 60.4 |  |
| Der_Musiker_-_d-music | de | 271 | — | — | 0.020 | 99.4 % | 99.4 % | 97.2 % | manual | 0.0 % | 14.8 % | — | 69.6 |  |
| Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique | de | 248 | — | — | 0.074 | 98.9 % | 100.0 % | 94.6 % | manual | 0.0 % | 17.2 % | — | 62.5 |  |
| Keine_Lust_-_Jonny_M | de | 229 | — | — | 0.019 | 99.8 % | 99.8 % | 95.8 % | manual | 0.0 % | 1.7 % | — | 59.6 |  |
| Sehnsucht-Unplugged_-_REH-TORTE | de | 233 | — | — | 0.032 | 100.0 % | 100.0 % | 96.0 % | manual | 0.0 % | 30.5 % | — | 59.6 |  |
| Capotes_à_un_Franc_-_elmanu | fr | 188 | — | — | 0.025 | 100.0 % | 100.0 % | 97.6 % | manual | 0.0 % | 19.0 % | — | 49.6 |  |
| Confession_-_Quesabe | fr | 148 | — | — | 0.029 | 99.7 % | 99.7 % | 87.2 % | manual | 0.2 % | 19.7 % | — | 38.6 |  |
| Mère_nature_-_Law' | fr | 225 | — | — | 0.026 | 100.0 % | 100.0 % | 96.5 % | manual | 0.0 % | 8.3 % | — | 57.9 |  |
| Pas_que_tes_pas_-_AZUL | fr | 202 | — | — | 0.028 | 100.0 % | 100.0 % | 88.1 % | manual | 0.0 % | 36.0 % | — | 52.0 |  |
| Le_musée_d'air_contemporain_-_KPTN | fr | 184 | — | — | 0.019 | 100.0 % | 100.0 % | 94.1 % | manual | 0.0 % | 13.9 % | — | 48.3 |  |

## Peores casos

Mayor mediana de error de inicio:
- Cortez_-_Feel__Stripped_: 0.075 s
- Cafe_Jenseitz_Bebelstraße_-_kangaroo.musique: 0.074 s
- The_Rinn_-_Voices__2017_Version_: 0.070 s
- 1_Freak_-_Automatisch_Gekommen: 0.057 s
- Kinematic_-_Peyote: 0.052 s

## Notas

- Sincronía: error absoluto de inicio y fin de las palabras emparejadas con la referencia (sin tildes); sesgo = media con signo (positivo = tarde).
- Sin referencia: «Fuera de voz» es la parte del tiempo de las palabras en la que la voz (separada) calla; «Confianza < 0,3», la parte de las palabras con confianza baja.
